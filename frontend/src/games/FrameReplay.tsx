import { useEffect, useMemo, useState } from 'react';
import { fetchSudut, type Frame, type GameMeta } from './hubApi';
import { describeEvent, rendererFor } from './renderers';

const SPEEDS = [0.5, 1, 2, 4];

/** Pemutar replay umum: memutar frame tampilan publik satu per satu. */
export function FrameReplay({ frames, meta, names, settings, me = null }: {
  frames: Frame[]; meta: GameMeta; names: string[]; settings: Record<string, any>; me?: number | null;
}) {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const R = rendererFor(meta.id);
  const last = frames.length - 1;
  const base = meta.kategori === 'tick' ? 350 : meta.kategori === 'mandiri' ? 250 : 900;

  useEffect(() => {
    if (!playing) return;
    if (i >= last) {
      setPlaying(false);
      return;
    }
    const t = window.setTimeout(() => setI((x) => Math.min(last, x + 1)), base / speed);
    return () => window.clearTimeout(t);
  }, [playing, i, last, base, speed]);

  const f = frames[Math.min(i, last)];
  const lines = useMemo(() => (f?.events ?? []).map(describeEvent).filter(Boolean) as string[], [f]);
  if (!f) return null;
  return (
    <div className="frame-replay">
      <div className="replay-controls panel">
        <div className="row">
          <button type="button" className="btn small" onClick={() => { setPlaying(false); setI(0); }} aria-label="Ke awal">⏮</button>
          <button type="button" className="btn small" onClick={() => { setPlaying(false); setI(Math.max(0, i - 1)); }} aria-label="Mundur">◀</button>
          <button type="button" className="btn small primary" onClick={() => { if (i >= last) setI(0); setPlaying(!playing); }}>{playing ? '⏸ Jeda' : '▶ Putar'}</button>
          <button type="button" className="btn small" onClick={() => { setPlaying(false); setI(Math.min(last, i + 1)); }} aria-label="Maju">▶</button>
          <button type="button" className="btn small" onClick={() => { setPlaying(false); setI(last); }} aria-label="Ke akhir">⏭</button>
          <div className="seg" role="group" aria-label="Kecepatan">
            {SPEEDS.map((s) => <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)}>{s}×</button>)}
          </div>
          <label className="scrub">
            <input type="range" min={0} max={last} value={i} onChange={(e) => { setPlaying(false); setI(Number(e.target.value)); }} aria-label="Posisi replay" />
            <output>{i}/{last}</output>
          </label>
        </div>
        {lines.length > 0 && <div className="replay-events">{lines.map((l, k) => <span key={k}>{l}</span>)}</div>}
      </div>
      <R view={f.view} meta={meta} names={names} me={me} canAct={false} acted={false} act={() => undefined} replay events={f.events}
        settings={settings} pending={[]} />
    </div>
  );
}

/** Replay dengan pilihan sudut pandang: semua rahasia terbuka, penonton (berkabut), atau seperti yang dilihat satu pemain. */
export function ReplayPanel({ frames, meta, names, settings, replayId, initial = 'semua' }: {
  frames: Frame[]; meta: GameMeta; names: string[]; settings: Record<string, any>; replayId?: string | null; initial?: 'semua' | number;
}) {
  const [kursi, setKursi] = useState<'semua' | number>(initial);
  const [alt, setAlt] = useState<Frame[] | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (kursi === 'semua' || !replayId) {
      setAlt(null);
      return;
    }
    let alive = true;
    setBusy(true);
    setErr('');
    fetchSudut(replayId, kursi)
      .then((r) => alive && setAlt(r.frames))
      .catch((e) => alive && setErr((e as Error).message))
      .finally(() => alive && setBusy(false));
    return () => {
      alive = false;
    };
  }, [kursi, replayId]);
  return (
    <div className="panel">
      <div className="row">
        <h3>Replay</h3>
        <span className="spacer" />
        {replayId && (
          <label className="field inline">Sudut pandang
            <select className="input" value={String(kursi)} onChange={(e) => setKursi(e.target.value === 'semua' ? 'semua' : Number(e.target.value))}>
              <option value="semua">Semua rahasia terbuka</option>
              <option value="-1">Penonton (berkabut)</option>
              {names.map((n, i) => <option key={n} value={i}>Seperti dilihat {n}</option>)}
            </select>
          </label>
        )}
      </div>
      {busy && <p className="hint"><span className="spinner" /> Membuat ulang match dari sudut pandang itu…</p>}
      {err && <p className="bad">{err}</p>}
      {(frames.length > 1 || alt) && (
        <FrameReplay key={String(kursi) + (alt ? 'a' : 'f')} frames={alt ?? frames} meta={meta} names={names} settings={settings}
          me={kursi === 'semua' || kursi < 0 ? null : kursi} />
      )}
    </div>
  );
}
