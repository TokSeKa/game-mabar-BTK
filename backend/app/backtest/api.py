"""REST untuk tab Backtest: daftar strategi, jalankan (di proses terpisah), progres, hasil, riwayat.

Kode strategi hanya dibaca dari folder ``strategi/`` di server/laptop; lewat web orang hanya bisa memilih file
yang sudah ada dan mengubah PENGATURAN/PARAMETER, tidak bisa mengunggah kode.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .data import Eksternal
from .runner import hasil_dir, new_id
from .strategy import list_strategies, read_meta, resolve_path, strategi_dir

log = logging.getLogger("backtest")
ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{4}$")
SYM_RE = re.compile(r"^[A-Za-z0-9.=_\-]{1,30}$")
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class RunReq(BaseModel):
    strategi: str = Field(max_length=120)
    pengaturan: dict[str, Any] = Field(default_factory=dict)
    parameter: dict[str, Any] = Field(default_factory=dict)


@dataclass
class Job:
    id: str
    strategi: str
    status: str = "jalan"          # jalan | selesai | gagal | batal
    progres: float = 0.0
    pesan: str = "memulai"
    error: str | None = None
    mulai: float = field(default_factory=time.time)
    selesai: float | None = None
    proc: asyncio.subprocess.Process | None = None
    task: asyncio.Task | None = None

    def public(self) -> dict[str, Any]:
        return {"id": self.id, "strategi": self.strategi, "status": self.status, "progres": self.progres,
                "pesan": self.pesan, "error": self.error, "durasi": round((self.selesai or time.time()) - self.mulai, 1)}


class Jobs:
    def __init__(self, root: Path | None = None, timeout: float | None = None, parallel: int | None = None):
        self.root = root or hasil_dir()
        self.timeout = timeout or float(os.environ.get("BACKTEST_TIMEOUT", 900))
        self.parallel = parallel or int(os.environ.get("BACKTEST_PARALEL", 1))
        self.jobs: dict[str, Job] = {}

    def running(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.status == "jalan"]

    async def start(self, req: RunReq) -> Job:
        if len(self.running()) >= self.parallel:
            raise HTTPException(429, "Masih ada backtest yang berjalan. Tunggu sampai selesai atau batalkan dulu.")
        try:
            path = resolve_path(req.strategi)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(404, str(e)) from None
        if path.parent.resolve() != strategi_dir().resolve():
            raise HTTPException(400, "Hanya strategi di folder strategi/ yang bisa dijalankan dari web.")
        meta = read_meta(path)
        if meta["error"]:
            raise HTTPException(400, meta["error"])
        rid = new_id()
        while rid in self.jobs or (self.root / rid).exists():
            rid = new_id()
        out = self.root / rid
        out.mkdir(parents=True, exist_ok=True)
        cfg = out / "permintaan.json"
        cfg.write_text(json.dumps({"pengaturan": req.pengaturan, "parameter": req.parameter}), encoding="utf-8")
        job = Job(rid, path.name)
        self.jobs[rid] = job
        job.proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "app.backtest", "jalankan", str(path), "--json-input", str(cfg), "--keluaran", str(out),
            "--id", rid, "--progres-json", cwd=str(BACKEND_DIR), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        job.task = asyncio.create_task(self._watch(job, out))
        return job

    async def _watch(self, job: Job, out: Path) -> None:
        tail: list[str] = []
        try:
            async def read() -> None:
                assert job.proc and job.proc.stdout
                async for raw in job.proc.stdout:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        tail.append(line)
                        del tail[:-20]
                        continue
                    if "progres" in msg:
                        job.progres, job.pesan = float(msg["progres"]), str(msg.get("pesan", ""))
                    elif "error" in msg:
                        job.error = str(msg["error"])
                    elif "selesai" in msg:
                        job.progres = 1.0
                await job.proc.wait()
            await asyncio.wait_for(read(), timeout=self.timeout)
            code = job.proc.returncode
            if job.status == "batal":
                pass
            elif code == 0 and (out / "hasil.json").exists():
                job.status, job.pesan = "selesai", "selesai"
            else:
                job.status = "gagal"
                job.error = job.error or ("\n".join(tail[-8:]) or f"Proses berhenti (kode {code}).")
        except asyncio.TimeoutError:
            self._kill(job)
            job.status, job.error = "gagal", f"Melebihi batas waktu {self.timeout:.0f} detik. Persempit rentang/aset."
        except Exception as e:  # noqa: BLE001
            log.exception("backtest watch")
            job.status, job.error = "gagal", str(e)
        finally:
            job.selesai = time.time()
            if job.status != "selesai" and not (out / "hasil.json").exists():
                shutil.rmtree(out, ignore_errors=True)

    def _kill(self, job: Job) -> None:
        if job.proc and job.proc.returncode is None:
            try:
                job.proc.kill()
            except ProcessLookupError:
                pass

    def cancel(self, rid: str) -> Job:
        job = self.jobs.get(rid)
        if not job:
            raise HTTPException(404, "Backtest tidak ditemukan.")
        if job.status == "jalan":
            job.status, job.error = "batal", "Dibatalkan."
            self._kill(job)
        return job

    def shutdown(self) -> None:
        for j in self.running():
            self._kill(j)

    def results(self, limit: int = 200) -> list[dict[str, Any]]:
        out = []
        if not self.root.is_dir():
            return out
        for d in sorted((p for p in self.root.iterdir() if p.is_dir() and ID_RE.match(p.name)), reverse=True)[:limit]:
            f = d / "hasil.json"
            if not f.exists():
                continue
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            rk = r.get("ringkasan", {})
            out.append({"id": r["id"], "strategi": r["strategi"], "judul": r.get("judul"), "dibuat": r.get("dibuat"),
                        "mode": r.get("mode"), "pasar_nama": r.get("pasar_nama"), "timeframe": r.get("timeframe"),
                        "n_aset": len(r.get("aset", [])), "produk": r.get("pengaturan", {}).get("produk"),
                        "return_pct": rk.get("return_pct"), "buy_hold_pct": rk.get("buy_hold_pct"),
                        "max_dd_pct": rk.get("max_dd_pct"), "sharpe": rk.get("sharpe"), "n_trades": rk.get("n_trades"),
                        "parameter": r.get("parameter")})
        return out


def _dir(jobs: Jobs, rid: str) -> Path:
    if not ID_RE.match(rid):
        raise HTTPException(400, "Id tidak valid.")
    d = jobs.root / rid
    if not (d / "hasil.json").exists():
        raise HTTPException(404, "Hasil tidak ditemukan.")
    return d


def mount(app: FastAPI, jobs: Jobs | None = None) -> Jobs:
    jobs = jobs or Jobs()
    r = APIRouter(prefix="/api/backtest")
    enabled = os.environ.get("BACKTEST_AKTIF", "1") != "0"

    def need() -> None:
        if not enabled:
            raise HTTPException(404, "Backtest dimatikan di server ini (BACKTEST_AKTIF=0).")

    @r.get("/strategi")
    async def strategi() -> dict[str, Any]:
        need()
        folder = strategi_dir()
        return {"folder": str(folder), "strategi": await asyncio.to_thread(list_strategies, folder),
                "pengumpul": await asyncio.to_thread(Eksternal().status)}

    @r.post("/jalankan")
    async def jalankan(req: RunReq) -> dict[str, Any]:
        need()
        return (await jobs.start(req)).public()

    @r.get("/job/{rid}")
    async def job(rid: str) -> dict[str, Any]:
        j = jobs.jobs.get(rid)
        if not j:
            raise HTTPException(404, "Backtest tidak ditemukan.")
        return j.public()

    @r.post("/job/{rid}/batal")
    async def batal(rid: str) -> dict[str, Any]:
        return jobs.cancel(rid).public()

    @r.get("/hasil")
    async def daftar() -> dict[str, Any]:
        need()
        return {"hasil": await asyncio.to_thread(jobs.results), "berjalan": [j.public() for j in jobs.running()]}

    @r.get("/hasil/{rid}")
    async def hasil(rid: str) -> FileResponse:
        return FileResponse(_dir(jobs, rid) / "hasil.json", media_type="application/json")

    @r.get("/hasil/{rid}/aset/{sym}")
    async def aset(rid: str, sym: str) -> FileResponse:
        if not SYM_RE.match(sym):
            raise HTTPException(400, "Simbol tidak valid.")
        f = _dir(jobs, rid) / "aset" / f"{sym}.json"
        if not f.exists():
            raise HTTPException(404, "Data chart aset ini tidak ada.")
        return FileResponse(f, media_type="application/json")

    @r.delete("/hasil/{rid}")
    async def hapus(rid: str) -> dict[str, Any]:
        d = _dir(jobs, rid)
        await asyncio.to_thread(shutil.rmtree, d, True)
        return {"ok": True}

    app.include_router(r)
    app.state.backtest = jobs
    return jobs
