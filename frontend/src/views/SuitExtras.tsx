import { useEffect, useMemo, useState } from 'react';
import { getEvents, runDebug } from '../api';
import { getLiga, type LigaRow } from '../games/hubApi';
import { Replay } from '../replay/Replay';
import { ICON } from '../replay/assets';
import type { DebugResult, EventInfo, MatchData, RatingChange, TournamentResult } from '../types';

export const REACTIONS = ['👏', '😂', '😮', '🔥', '😭', '🤝', '💀', '🎉'];

/* ------------------------------------------------------------------ event */
export function EventSelect({ value, onChange, disabled, id = 'set-event' }: { value: string; onChange: (v: string) => void; disabled?: boolean; id?: string }) {
  const [events, setEvents] = useState<EventInfo[]>([]);
  useEffect(() => {
    getEvents().then(setEvents).catch(() => setEvents([]));
  }, []);
  const cur = events.find((e) => e.id === value);
  return (
    <label className="field" htmlFor={id} style={{ gridColumn: '1 / -1' }}>
      Mode event
      <select id={id} className="input" value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        {(events.length ? events : [{ id: 'normal', nama: 'Normal', ket: '' }]).map((e) => <option key={e.id} value={e.id}>{e.nama}</option>)}
      </select>
      {cur && cur.id !== 'normal' && <small className="hint">{cur.ket}</small>}
    </label>
  );
}

/** Nama event dari id (untuk header room). */
export function EventName({ id }: { id?: string }) {
  const [events, setEvents] = useState<EventInfo[]>([]);
  useEffect(() => {
    getEvents().then(setEvents).catch(() => setEvents([]));
  }, []);
  if (!id || id === 'normal') return null;
  const e = events.find((x) => x.id === id);
  return <span className="status-pill warn" title={e?.ket}>⚡ {e?.nama ?? id}</span>;
}

export function EventBadge({ ev }: { ev?: EventInfo | null }) {
  if (!ev || ev.id === 'normal') return null;
  return <span className="status-pill warn" title={ev.ket}>⚡ {ev.nama}{ev.kejutan ? ' (kejutan)' : ''}</span>;
}

/* ------------------------------------------------------------------ reaksi */
export interface FloatReaction { id: number; name: string; emoji: string; x: number }

export function useReactions(): [FloatReaction[], (name: string, emoji: string) => void] {
  const [items, setItems] = useState<FloatReaction[]>([]);
  const add = (name: string, emoji: string) => {
    const id = Date.now() + Math.random();
    setItems((r) => [...r.slice(-14), { id, name, emoji, x: 8 + Math.random() * 84 }]);
    window.setTimeout(() => setItems((r) => r.filter((x) => x.id !== id)), 3200);
  };
  return [items, add];
}

export function ReactionBar({ onSend }: { onSend: (emoji: string) => void }) {
  return (
    <div className="react-bar-suit" role="group" aria-label="Kirim reaksi">
      {REACTIONS.map((e) => <button key={e} type="button" onClick={() => onSend(e)} aria-label={`Reaksi ${e}`}>{e}</button>)}
    </div>
  );
}

export function ReactionLayer({ items }: { items: FloatReaction[] }) {
  return (
    <div className="react-layer" aria-live="polite">
      {items.map((r) => <div key={r.id} className="react-float" style={{ left: `${r.x}%` }}><span>{r.emoji}</span><small>{r.name}</small></div>)}
    </div>
  );
}

export function RatingList({ ratings, players }: { ratings?: Record<string, RatingChange> | null; players: { id: string; name: string; color: string }[] }) {
  if (!ratings || !Object.keys(ratings).length) return null;
  return (
    <div className="net" aria-label="Perubahan rating liga">
      <span>Rating liga:</span>
      {players.filter((p) => ratings[p.id]).map((p) => {
        const r = ratings[p.id];
        return (
          <span key={p.id} className="chip" style={{ ['--c' as string]: p.color }}>
            {p.name} <b className={r.delta >= 0 ? 'p' : 'm'}>{Math.round(r.baru)} ({r.delta >= 0 ? '+' : ''}{r.delta.toFixed(1)})</b>
          </span>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ debugger */
export function DebugPanel({ match, myIndex, code, ronde }: { match: MatchData; myIndex: number; code: string; ronde: number }) {
  const lastRound = match.rounds.length ? match.rounds[match.rounds.length - 1].r : 1;
  const [r, setR] = useState(ronde);
  const [res, setRes] = useState<DebugResult | null>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [usedCode, setUsedCode] = useState('');

  useEffect(() => setR(Math.min(Math.max(1, ronde), lastRound)), [ronde, lastRound]);
  const alive = (rr: number) => {
    const prev = match.rounds.filter((x) => x.r < rr);
    const hp = prev.length ? prev[prev.length - 1].after : match.players.map(() => match.settings.hp_awal);
    return hp[myIndex] > 0;
  };

  const run = async () => {
    setBusy(true);
    setErr('');
    setRes(null);
    try {
      const before = match.rounds.filter((x) => x.r < r);
      const d = await runDebug({
        code, settings: match.settings, names: match.players.map((p) => p.name), my_index: myIndex, ronde: r,
        rounds: before.slice(-(match.settings.ingatan + 1)),
      });
      setRes(d);
      setUsedCode(code);
      setStep(0);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const trace = res?.trace ?? [];
  const cur = trace[Math.min(step, Math.max(0, trace.length - 1))];
  const lines = useMemo(() => usedCode.split('\n'), [usedCode]);
  const actual = match.rounds.find((x) => x.r === r)?.choices[myIndex] ?? null;

  return (
    <div className="panel debug-panel">
      <h3>Debugger langkah demi langkah</h3>
      <p className="hint">
        Jalankan ulang botmu di satu ronde dengan info yang sama persis seperti saat match, lalu telusuri baris demi baris beserta isi variabelnya.
        Memakai kode di editormu sekarang, jadi kamu bisa memperbaiki lalu langsung mengecek lagi.
      </p>
      <div className="row">
        <label className="field" htmlFor="dbg-r" style={{ width: 120 }}>Ronde
          <input id="dbg-r" type="number" min={1} max={lastRound} value={r} onChange={(e) => setR(Math.min(lastRound, Math.max(1, +e.target.value || 1)))} />
        </label>
        <button type="button" className="btn primary" disabled={busy || !code.trim() || !alive(r)} onClick={run}>{busy ? 'Menjalankan…' : '🐞 Debug ronde ini'}</button>
        {!alive(r) && <span className="hint">Botmu sudah gugur sebelum ronde {r}.</span>}
      </div>
      {err && <div className="err-box">{err}</div>}
      {res && !res.ok && res.error && <div className="err-box"><b>Baris {res.error.baris ?? '?'}</b>: {res.error.pesan}</div>}
      {res?.ok && (
        <>
          <div className="row">
            <span>Hasil: {res.pilihan ? <b className={`w ${res.pilihan}`}><span className="dbg-ic" dangerouslySetInnerHTML={{ __html: ICON[res.pilihan] }} /> {res.pilihan.toUpperCase()}</b> : <b className="bad">error</b>}</span>
            {actual && <span className="hint">· di match aslinya: {actual.toUpperCase()}{res.pilihan && res.pilihan !== actual ? ' (berbeda karena kodemu berubah)' : ''}</span>}
            <span className="hint">· {res.langkah} langkah{res.info?.kabut ? ' · event kabut: pilihan lawan disembunyikan' : ''}</span>
          </div>
          {res.error && <div className="err-box"><b>Baris {res.error.baris ?? '?'}</b>: {res.error.pesan} (di match, bot memakai BATU)</div>}
          {trace.length > 0 && (
            <>
              <div className="row dbg-ctrl">
                <button type="button" className="btn small" onClick={() => setStep(0)} aria-label="Langkah pertama">⏮</button>
                <button type="button" className="btn small" onClick={() => setStep(Math.max(0, step - 1))} aria-label="Langkah sebelumnya">◀</button>
                <button type="button" className="btn small" onClick={() => setStep(Math.min(trace.length - 1, step + 1))} aria-label="Langkah berikutnya">▶</button>
                <button type="button" className="btn small" onClick={() => setStep(trace.length - 1)} aria-label="Langkah terakhir">⏭</button>
                <label className="scrub">
                  <input type="range" min={0} max={trace.length - 1} value={step} onChange={(e) => setStep(+e.target.value)} aria-label="Langkah" />
                  <output>{step + 1}/{trace.length}</output>
                </label>
              </div>
              <div className="dbg-grid">
                <pre className="dbg-code" aria-label="Kode bot">
                  {lines.map((ln, i) => (
                    <div key={i} className={cur?.baris === i + 1 ? 'on' : ''}><span className="ln">{i + 1}</span>{ln || ' '}</div>
                  ))}
                </pre>
                <div className="dbg-vars">
                  <div className="hint">Baris {cur?.baris} · fungsi <code>{cur?.fungsi || '(atas)'}</code> · langkah ke-{cur?.langkah}</div>
                  {cur?.kembali != null && <div className="ok-box">return → <code>{cur.kembali}</code></div>}
                  <table className="tbl">
                    <thead><tr><th>Variabel</th><th>Isi</th></tr></thead>
                    <tbody>
                      {Object.entries(cur?.vars ?? {}).map(([k, v]) => <tr key={k}><td><code>{k}</code></td><td className="dbg-val">{v}</td></tr>)}
                      {!Object.keys(cur?.vars ?? {}).length && <tr><td colSpan={2} className="hint">belum ada variabel</td></tr>}
                    </tbody>
                  </table>
                  {res.cetak && res.cetak.length > 0 && <div><div className="hint">print():</div>{res.cetak.map((c, k) => <code key={k} className="dbg-print">{c}</code>)}</div>}
                  {res.jejak_penuh && <p className="hint">Jejak dibatasi 600 langkah pertama.</p>}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ turnamen */
export function TournamentView({ t, me }: { t: TournamentResult; me: string | null }) {
  const [sel, setSel] = useState<number | null>(null);
  const P = t.players;
  const cell = (i: number, j: number) => t.matches.findIndex((m) => (m.a === i && m.b === j) || (m.a === j && m.b === i));
  const chosen = sel != null ? t.matches[sel] : null;
  const myIdxIn = (m: (typeof t.matches)[number]) => {
    const ids = [P[m.a].id, P[m.b].id];
    const k = ids.indexOf(me ?? '');
    return k >= 0 ? k : undefined;
  };
  return (
    <div className="panel tournament">
      <div className="row">
        <h3>Turnamen {t.id}</h3>
        <EventBadge ev={t.event} />
        <span className="hint">Setiap pasangan main 1 lawan 1 sekali · menang 3, seri 1, kalah 0 · seri poin dipecah selisih HP.</span>
      </div>
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>#</th><th>Bot</th><th>Poin</th><th>M</th><th>S</th><th>K</th><th>Selisih HP</th><th>Rating</th></tr></thead>
          <tbody>
            {t.standings.map((r, k) => {
              const p = P[r.index];
              const rt = t.ratings?.[p.id];
              return (
                <tr key={p.id} className={p.id === me ? 'me' : ''}>
                  <td>{k === 0 ? '🏆' : k + 1}</td>
                  <td><span className="chip" style={{ ['--c' as string]: p.color }}>{p.name}</span></td>
                  <td className="num"><b>{r.poin}</b></td><td className="num">{r.menang}</td><td className="num">{r.seri}</td><td className="num">{r.kalah}</td>
                  <td className="num">{r.selisih_hp > 0 ? '+' : ''}{r.selisih_hp}</td>
                  <td className="num">{rt ? `${Math.round(rt.baru)} (${rt.delta >= 0 ? '+' : ''}${rt.delta.toFixed(1)})` : '–'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <h3>Matriks hasil <span className="hint">(klik kotak untuk menonton replay)</span></h3>
      <div className="table-wrap">
        <table className="tbl matrix">
          <thead><tr><th />{P.map((p) => <th key={p.id} style={{ color: p.color }}>{p.name}</th>)}</tr></thead>
          <tbody>
            {P.map((row, i) => (
              <tr key={row.id}>
                <th style={{ color: row.color }}>{row.name}</th>
                {P.map((col, j) => {
                  if (i === j) return <td key={col.id} className="hint">·</td>;
                  const k = cell(i, j);
                  const m = t.matches[k];
                  const mine = m.a === i ? m.hp[0] : m.hp[1];
                  const res = m.pemenang == null ? 'S' : m.pemenang === i ? 'M' : 'K';
                  return (
                    <td key={col.id}>
                      <button type="button" className={`mx ${res} ${sel === k ? 'on' : ''}`} onClick={() => setSel(sel === k ? null : k)} title={`${row.name} vs ${col.name}`}>
                        {res} <small>{mine}</small>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {chosen && (
        <div className="tour-replay">
          <div className="row"><b>{P[chosen.a].name} vs {P[chosen.b].name}</b><span className="hint">{chosen.ronde} ronde · HP akhir {chosen.hp[0]} – {chosen.hp[1]}</span>
            <span className="spacer" /><button type="button" className="btn small" onClick={() => setSel(null)}>Tutup replay</button></div>
          <Replay key={chosen.match.id} match={chosen.match} myIndex={myIdxIn(chosen)} />
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ liga */
export function SuitLiga() {
  const [rows, setRows] = useState<LigaRow[] | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    getLiga('suit_arena').then((r) => setRows(r.board)).catch((e) => setErr((e as Error).message));
  }, []);
  return (
    <div className="panel" style={{ maxWidth: 760 }}>
      <h2>Liga Suit Bot Arena</h2>
      <p className="hint">
        Rating ELO (mulai 1200) untuk pemain yang masuk akun (menu Kilas Pasar → Akun). Dihitung dari setiap match dan turnamen di room.
        Latihan tidak dihitung.
      </p>
      {err && <div className="err-box">{err}</div>}
      {rows == null && !err && <div className="spinner" />}
      {rows && rows.length === 0 && <p className="hint">Belum ada match yang tercatat. Masuk akun lalu main di room bersama teman.</p>}
      {rows && rows.length > 0 && (
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>#</th><th>Pemain</th><th>Rating</th><th>Match</th><th>Juara</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.username}><td>{r.rank}</td><td>{r.username}</td><td className="num">{Math.round(r.rating)}</td><td className="num">{r.games}</td><td className="num">{r.wins}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
