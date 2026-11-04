"""Akun pemain (SQLite): daftar, masuk, token, riwayat hasil, dan papan peringkat harian."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
TOKEN_DAYS = 30


class AuthError(Exception):
    pass


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


class AccountDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self._fails: dict[str, list[float]] = {}
        with self.lock:
            self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE, pw_hash BLOB, salt BLOB, created INTEGER);
            CREATE TABLE IF NOT EXISTS tokens (
                token_hash TEXT PRIMARY KEY, user_id INTEGER, created INTEGER, expires INTEGER);
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY, user_id INTEGER, mode TEXT, created INTEGER, market TEXT, asset TEXT,
                chart_tf TEXT, return_pct REAL, bh_pct REAL, stats TEXT);
            CREATE INDEX IF NOT EXISTS results_user ON results(user_id, created);
            CREATE TABLE IF NOT EXISTS daily_config (date TEXT PRIMARY KEY, config TEXT);
            CREATE TABLE IF NOT EXISTS daily_entries (
                date TEXT, user_id INTEGER, status TEXT, return_pct REAL, stats TEXT, finished INTEGER,
                PRIMARY KEY (date, user_id));
            """)

    # ------------------------------------------------------------ akun
    def _throttle(self, key: str) -> None:
        now = time.time()
        fails = [t for t in self._fails.get(key, []) if now - t < 600]
        self._fails[key] = fails
        if len(fails) >= 10:
            raise AuthError("Terlalu banyak percobaan gagal. Coba lagi dalam 10 menit.")

    def _fail(self, key: str) -> None:
        self._fails.setdefault(key, []).append(time.time())

    def _new_token(self, user_id: int) -> str:
        tok = secrets.token_urlsafe(32)
        now = int(time.time())
        self.db.execute("INSERT INTO tokens VALUES (?,?,?,?)",
                        (hashlib.sha256(tok.encode()).hexdigest(), user_id, now, now + TOKEN_DAYS * 86400))
        return tok

    def register(self, username: str, password: str) -> tuple[dict[str, Any], str]:
        username = (username or "").strip()
        if not USERNAME_RE.match(username):
            raise AuthError("Username 3-20 karakter: huruf, angka, atau garis bawah (_).")
        if len(password or "") < 6:
            raise AuthError("Password minimal 6 karakter.")
        if len(password) > 200:
            raise AuthError("Password terlalu panjang.")
        salt = secrets.token_bytes(16)
        with self.lock:
            try:
                cur = self.db.execute("INSERT INTO users (username, pw_hash, salt, created) VALUES (?,?,?,?)",
                                      (username, _hash(password, salt), salt, int(time.time())))
            except sqlite3.IntegrityError:
                raise AuthError("Username sudah dipakai.") from None
            uid = int(cur.lastrowid)
            return {"id": uid, "username": username}, self._new_token(uid)

    def login(self, username: str, password: str, ip: str = "") -> tuple[dict[str, Any], str]:
        key = f"{ip}|{(username or '').lower()}"
        self._throttle(key)
        with self.lock:
            row = self.db.execute("SELECT * FROM users WHERE username = ?", ((username or "").strip(),)).fetchone()
            if row is None or not hmac.compare_digest(_hash(password or "", row["salt"]), row["pw_hash"]):
                self._fail(key)
                raise AuthError("Username atau password salah.")
            return {"id": row["id"], "username": row["username"]}, self._new_token(row["id"])

    def user_for_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        h = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            row = self.db.execute(
                "SELECT u.id, u.username, t.expires FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token_hash = ?",
                (h,)).fetchone()
        if row is None or row["expires"] < time.time():
            return None
        return {"id": row["id"], "username": row["username"]}

    def logout(self, token: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM tokens WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))

    # ------------------------------------------------------------ hasil
    def add_result(self, user_id: int, mode: str, market: str, asset: str, chart_tf: str,
                   return_pct: float, bh_pct: float, stats: dict[str, Any]) -> None:
        with self.lock:
            self.db.execute(
                "INSERT INTO results (user_id, mode, created, market, asset, chart_tf, return_pct, bh_pct, stats)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, mode, int(time.time()), market, asset, chart_tf, return_pct, bh_pct, json.dumps(stats)))

    def results(self, user_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute("SELECT * FROM results WHERE user_id = ? ORDER BY created DESC LIMIT ?",
                                   (user_id, limit)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["stats"] = json.loads(d["stats"] or "{}")
            out.append(d)
        return out

    def profile(self, user_id: int) -> dict[str, Any]:
        with self.lock:
            r = self.db.execute(
                "SELECT COUNT(*) n, AVG(return_pct) avg_ret, MAX(return_pct) best, "
                "SUM(CASE WHEN return_pct > bh_pct THEN 1 ELSE 0 END) beat FROM results WHERE user_id = ?",
                (user_id,)).fetchone()
            d = self.db.execute("SELECT COUNT(*) n FROM daily_entries WHERE user_id = ? AND status = 'done'",
                                (user_id,)).fetchone()
        return {"sesi": r["n"] or 0, "rata_return": r["avg_ret"], "terbaik": r["best"],
                "kalahkan_buy_hold": r["beat"] or 0, "harian_selesai": d["n"] or 0}

    # ------------------------------------------------------------ harian
    def daily_config(self, date: str) -> dict[str, Any] | None:
        with self.lock:
            r = self.db.execute("SELECT config FROM daily_config WHERE date = ?", (date,)).fetchone()
        return json.loads(r["config"]) if r else None

    def save_daily_config(self, date: str, cfg: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO daily_config VALUES (?,?)", (date, json.dumps(cfg)))
            r = self.db.execute("SELECT config FROM daily_config WHERE date = ?", (date,)).fetchone()
        return json.loads(r["config"])

    def daily_entry(self, date: str, user_id: int) -> dict[str, Any] | None:
        with self.lock:
            r = self.db.execute("SELECT * FROM daily_entries WHERE date = ? AND user_id = ?", (date, user_id)).fetchone()
        return dict(r) if r else None

    def daily_begin(self, date: str, user_id: int) -> None:
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO daily_entries (date, user_id, status) VALUES (?,?, 'started')",
                            (date, user_id))

    def daily_finish(self, date: str, user_id: int, return_pct: float, stats: dict[str, Any]) -> None:
        with self.lock:
            self.db.execute(
                "UPDATE daily_entries SET status='done', return_pct=?, stats=?, finished=? WHERE date=? AND user_id=?",
                (return_pct, json.dumps(stats), int(time.time()), date, user_id))

    def daily_board(self, date: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute(
                "SELECT u.username, e.return_pct, e.stats, e.finished FROM daily_entries e JOIN users u ON u.id = e.user_id "
                "WHERE e.date = ? AND e.status = 'done' ORDER BY e.return_pct DESC, e.finished ASC LIMIT ?",
                (date, limit)).fetchall()
        out = []
        for i, r in enumerate(rows, 1):
            st = json.loads(r["stats"] or "{}")
            out.append({"rank": i, "username": r["username"], "return_pct": r["return_pct"],
                        "n_trades": st.get("n_trades"), "max_dd_pct": st.get("max_dd_pct")})
        return out

    def daily_rank(self, date: str, user_id: int) -> int | None:
        e = self.daily_entry(date, user_id)
        if not e or e["status"] != "done":
            return None
        with self.lock:
            r = self.db.execute("SELECT COUNT(*) n FROM daily_entries WHERE date=? AND status='done' AND return_pct > ?",
                                (date, e["return_pct"])).fetchone()
        return int(r["n"]) + 1
