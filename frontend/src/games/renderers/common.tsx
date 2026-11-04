import { useEffect, useState, type ReactNode } from 'react';
import type { GameMeta } from '../hubApi';
import { fmt, seatColor } from '../hubApi';

export interface RenderProps {
  view: any;
  meta: GameMeta;
  names: string[];
  /** kursi yang sudut pandangnya dipakai (null = penonton / replay umum) */
  me: number | null;
  /** boleh mengirim aksi sekarang (giliranku dan aku manusia di kursi ini) */
  canAct: boolean;
  /** aksi untuk langkah ini sudah terkirim */
  acted: boolean;
  act: (a: unknown) => void;
  replay: boolean;
  events: any[];
  settings: Record<string, any>;
  pending: number[];
}

export interface ScoreRow {
  name: string;
  value: ReactNode;
  sub?: ReactNode;
  idx: number;
  dim?: boolean;
  tag?: ReactNode;
}

export function ScoreBoard({ rows, me, title = 'Skor' }: { rows: ScoreRow[]; me: number | null; title?: string }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <ol className="board">
        {rows.map((r, k) => (
          <li key={r.name} className={`${r.idx === me ? 'me' : ''} ${r.dim ? 'out' : ''}`}>
            <span className="rk">{k + 1}</span>
            <span className="dot" style={{ ['--c' as string]: seatColor(r.idx) }} />
            <span className="nm">
              {r.name} {r.tag && <small>{r.tag}</small>}
            </span>
            <span className="v">
              {r.value}
              {r.sub != null && <small>{r.sub}</small>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Papan skor dari dict nama → angka, urut terbesar. */
export function scoreRows(names: string[], scores: Record<string, number>, digits = 2): ScoreRow[] {
  return names
    .map((n, i) => ({ name: n, idx: i, raw: scores?.[n] ?? 0 }))
    .sort((a, b) => b.raw - a.raw)
    .map((r) => ({ name: r.name, idx: r.idx, value: fmt(r.raw, digits) }));
}

export function TurnNote({ canAct, acted, replay, me, children }: { canAct: boolean; acted: boolean; replay: boolean; me: number | null; children?: ReactNode }) {
  if (replay) return null;
  if (acted) return <div className="turn-note done">Aksi terkirim. Menunggu pemain lain…</div>;
  if (canAct) return <div className="turn-note go">Giliranmu! {children}</div>;
  if (me == null) return <div className="turn-note">Kamu menonton.</div>;
  return null;
}

export function NumberPicker({ value, onChange, min, max, step = 1, label, disabled }: {
  value: number; onChange: (v: number) => void; min: number; max: number; step?: number; label?: string; disabled?: boolean;
}) {
  const clamp = (v: number) => Math.min(max, Math.max(min, Number.isFinite(v) ? v : min));
  return (
    <div className="numpick">
      {label && <span className="np-label">{label}</span>}
      <button type="button" className="btn small" disabled={disabled || value <= min} onClick={() => onChange(clamp(value - step))} aria-label="Kurangi">−</button>
      <input type="range" min={min} max={max} step={step} value={value} disabled={disabled} onChange={(e) => onChange(clamp(Number(e.target.value)))} />
      <input className="np-num" type="number" min={min} max={max} step={step} value={value} disabled={disabled}
        onChange={(e) => onChange(clamp(Number(e.target.value)))} />
      <button type="button" className="btn small" disabled={disabled || value >= max} onClick={() => onChange(clamp(value + step))} aria-label="Tambah">+</button>
    </div>
  );
}

/** State lokal yang kembali ke ``initial`` setiap kali ``resetKey`` berubah (misalnya ronde baru). */
export function useResetState<T>(initial: T, resetKey: unknown): [T, (v: T) => void] {
  const [v, setV] = useState(initial);
  useEffect(() => {
    setV(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);
  return [v, setV];
}

export function NameChip({ name, idx }: { name: string; idx: number }) {
  return <span className="chip" style={{ ['--c' as string]: seatColor(idx) }}>{name}</span>;
}

export function idxOf(names: string[], name: string | null | undefined): number {
  return name == null ? -1 : names.indexOf(name);
}
