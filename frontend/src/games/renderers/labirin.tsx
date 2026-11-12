import { useEffect, useState, type ReactNode } from 'react';
import { seatColor } from '../hubApi';
import { NameChip, ScoreBoard, TurnNote, idxOf, type RenderProps } from './common';

const BIT: Record<string, number> = { atas: 1, kanan: 2, bawah: 4, kiri: 8 };
const ARROW: Record<string, string> = { atas: '↑', bawah: '↓', kiri: '←', kanan: '→' };
const KEYMAP: Record<string, string> = {
  ArrowUp: 'atas', ArrowDown: 'bawah', ArrowLeft: 'kiri', ArrowRight: 'kanan', w: 'atas', s: 'bawah', a: 'kiri', d: 'kanan',
};
const S = 24;

type Cell = number | null;

/** Gambar labirin (peta berkabut atau terbuka), tali, tanda, benda, dan pemain. */
export function MazeSvg({ v, names, me, peta, tali, tanda, small }: {
  v: any; names: string[]; me: number | null; peta?: Cell[][]; tali?: Record<string, number[][]>; tanda?: any[]; small?: boolean;
}) {
  const map: Cell[][] = peta ?? v.peta;
  const n = map.length;
  const vis = new Set<string>((v.terlihat ?? []).map((x: number[]) => `${x[0]},${x[1]}`));
  const fogNow = !peta && v.terlihat != null;
  const cells: ReactNode[] = [];
  const walls: ReactNode[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const w = map[r][c];
      const x = c * S;
      const y = r * S;
      if (w == null) {
        cells.push(<rect key={`u${r}-${c}`} x={x} y={y} width={S} height={S} className="lb-unknown" />);
        continue;
      }
      const dim = fogNow && !vis.has(`${r},${c}`);
      cells.push(<rect key={`f${r}-${c}`} x={x} y={y} width={S} height={S} className={`lb-floor ${dim ? 'dim' : ''}`} />);
      if (w & 1) walls.push(<line key={`t${r}-${c}`} x1={x} y1={y} x2={x + S} y2={y} />);
      if (w & 2) walls.push(<line key={`r${r}-${c}`} x1={x + S} y1={y} x2={x + S} y2={y + S} />);
      if (w & 4) walls.push(<line key={`b${r}-${c}`} x1={x} y1={y + S} x2={x + S} y2={y + S} />);
      if (w & 8) walls.push(<line key={`l${r}-${c}`} x1={x} y1={y} x2={x} y2={y + S} />);
    }
  }
  const ctr = (p: number[]) => [p[1] * S + S / 2, p[0] * S + S / 2];
  const ropes = Object.entries(tali ?? v.tali ?? {}).flatMap(([nm, pts]) => {
    const segs: number[][][] = [];
    let cur: number[][] = [];
    (pts as number[][]).forEach((p, k) => {
      const prev = (pts as number[][])[k - 1];
      if (prev && Math.abs(prev[0] - p[0]) + Math.abs(prev[1] - p[1]) !== 1) {
        if (cur.length > 1) segs.push(cur);
        cur = [];
      }
      cur.push(p);
    });
    if (cur.length > 1) segs.push(cur);
    return segs.map((sg, k) => (
      <polyline key={`${nm}-${k}`} className="lb-rope" points={sg.map((p) => ctr(p).join(',')).join(' ')}
        style={{ stroke: seatColor(idxOf(names, nm)) }} />
    ));
  });
  const emoji = (p: number[], t: string, key: string, cls = 'lb-emoji') => {
    const [cx, cy] = ctr(p);
    return <text key={key} x={cx} y={cy} className={cls} dominantBaseline="central" textAnchor="middle">{t}</text>;
  };
  const players = Object.entries(v.pemain ?? {}).filter(([, p]: [string, any]) => p.posisi && !p.selesai);
  return (
    <svg className={`lb-svg ${small ? 'sm' : ''}`} viewBox={`-2 -2 ${n * S + 4} ${n * S + 4}`} role="img" aria-label="Peta labirin">
      <g>{cells}</g>
      {emoji([0, 0], 'S', 'start', 'lb-start')}
      {v.keluar && emoji(v.keluar, '🚪', 'exit')}
      <g>{ropes}</g>
      <g className="lb-walls">{walls}</g>
      {(v.koin ?? []).map((p: number[], k: number) => emoji(p, '🪙', `k${k}`))}
      {(v.jebakan ?? []).map((p: number[], k: number) => emoji(p, '🕳️', `j${k}`))}
      {(v.portal ?? []).flatMap((pr: number[][], k: number) => pr.map((p, j) => emoji(p, '🌀', `p${k}-${j}`, `lb-emoji portal-${k % 4}`)))}
      {(tanda ?? v.tanda ?? []).map((t: any, k: number) => {
        const [cx, cy] = ctr(t.posisi);
        return <text key={`m${k}`} x={cx - S * 0.22} y={cy - S * 0.2} className="lb-mark" dominantBaseline="central" textAnchor="middle"
          style={{ fill: seatColor(idxOf(names, t.oleh)) }}>{t.simbol}</text>;
      })}
      {!peta && players.map(([nm, p]: [string, any], k) => {
        const i = idxOf(names, nm);
        const [cx, cy] = ctr(p.posisi);
        const off = (k % 3 - 1) * 3;
        return (
          <g key={nm}>
            <circle cx={cx + off} cy={cy + off} r={S * 0.3} className={`lb-player ${i === me ? 'me' : ''}`} style={{ fill: seatColor(i) }} />
            {i === me && v.arah_terakhir && <text x={cx + off} y={cy + off} className="lb-dir" dominantBaseline="central" textAnchor="middle">{ARROW[v.arah_terakhir]}</text>}
          </g>
        );
      })}
    </svg>
  );
}

export function RLabirin({ view, names, me, canAct, act, replay, tunggu }: RenderProps) {
  const v = view;
  const [lari, setLari] = useState(false);
  const [palet, setPalet] = useState(false);
  const myName = me != null ? names[me] : null;
  const pos: number[] | null = v.posisi ?? null;
  const here: number | null = pos && v.peta?.[pos[0]]?.[pos[1]] != null ? v.peta[pos[0]][pos[1]] : null;
  const cooling = (tunggu ?? 0) > 0;
  const live = canAct && !cooling;
  const open = (a: string) => here != null && !(here & BIT[a]);
  const move = (a: string, run = lari) => {
    if (!live || !open(a)) return;
    act(run ? `lari_${a}` : a);
  };

  useEffect(() => {
    if (!live) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      const a = KEYMAP[e.key] ?? KEYMAP[e.key.toLowerCase()];
      if (!a) return;
      e.preventDefault();
      move(a, lari || e.shiftKey);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const last = v.riwayat?.[v.riwayat.length - 1];
  const fresh = last && last.ronde === v.ronde - 1 && (v.langkah ?? 0) === 0;
  const finished = myName ? v.pemain?.[myName]?.selesai : false;
  const rows = names.map((n, i) => {
    const p = v.pemain?.[n];
    return {
      name: n, idx: i, value: v.skor?.[n] ?? 0,
      sub: p ? (p.selesai ? `🏁 #${p.urutan} · ${p.langkah} langkah` : `${p.langkah} langkah · sisa ${p.sisa}${p.tali_aktif ? ' · 🧵' : ''}`) : undefined,
      dim: !!p && !p.selesai && p.sisa <= 0,
    };
  }).sort((a, b) => Number(b.value) - Number(a.value));

  return (
    <div className="game-grid lb">
      <div className="panel">
        <div className="row"><b>Labirin {v.ronde}/{v.ronde_total}</b><span className="tag-mini">{v.ukuran}×{v.ukuran}</span><span className="spacer" />
          <span className="hint">{v.pandang === 'terang' ? '☀️ terang' : v.pandang === 'ingat' ? `🌫️ kabut diingat · pandang ${v.jarak_pandang}` : `🌑 kabut tanpa ingatan · pandang ${v.jarak_pandang}`}</span></div>
        {fresh && (
          <details className="lb-prev" open>
            <summary>Labirin {last.ronde} selesai · jalur terpendek {last.jalur_terpendek} langkah · urutan: {last.urutan.join(', ') || 'tidak ada yang keluar'}</summary>
            <MazeSvg v={{ ...last, pemain: {}, koin: [], jebakan: [], portal: [] }} names={names} me={me} peta={last.peta} tali={last.tali} tanda={last.tanda} small />
          </details>
        )}
        <TurnNote canAct={canAct} acted={false} replay={replay} me={me}>Cari pintu keluar 🚪{v.keluar ? '' : ' (lokasinya belum diketahui)'}.</TurnNote>
        {finished && <div className="turn-note done">🏁 Kamu keluar di urutan ke-{v.pemain[myName!].urutan}! Menunggu yang lain…</div>}
        {!replay && me != null && !finished && (v.sisa_langkah ?? 1) <= 0 && <div className="turn-note">Jatah langkahmu habis untuk labirin ini.</div>}
        <div className="lb-wrap"><MazeSvg v={v} names={names} me={me} /></div>
        {me != null && !replay && v.posisi && (
          <p className="hint lb-status">
            Langkah {v.langkah} · sisa <b>{v.sisa_langkah}</b> · koin {v.pemain?.[myName!]?.koin ?? 0}
            {v.suar_aktif > 0 && <> · 🔦 suar {v.suar_aktif} langkah</>}
            {cooling && <b className="bad"> · ⏳ tertahan jebakan {Math.ceil(tunggu ?? 0)} dtk</b>}
          </p>
        )}
        {canAct && (
          <div className="lb-controls">
            <div className="lb-pad">
              <span />
              <button type="button" className="btn big" disabled={!live || !open('atas')} onClick={() => move('atas')} aria-label="Atas">↑</button>
              <span />
              <button type="button" className="btn big" disabled={!live || !open('kiri')} onClick={() => move('kiri')} aria-label="Kiri">←</button>
              <button type="button" className={`btn big ${lari ? 'primary' : ''}`} onClick={() => setLari(!lari)} title="Lari: terus menyusuri lorong sampai persimpangan">🏃</button>
              <button type="button" className="btn big" disabled={!live || !open('kanan')} onClick={() => move('kanan')} aria-label="Kanan">→</button>
              <span />
              <button type="button" className="btn big" disabled={!live || !open('bawah')} onClick={() => move('bawah')} aria-label="Bawah">↓</button>
              <span />
            </div>
            <div className="lb-abil">
              <button type="button" className="btn small" disabled={!live || v.tanda_sisa <= 0} onClick={() => setPalet(!palet)}>📍 Tanda ({v.tanda_sisa})</button>
              <button type="button" className={`btn small ${v.tali_aktif ? 'primary' : ''}`} disabled={!live || (!v.tali_aktif && v.tali_sisa <= 0)}
                onClick={() => act(v.tali_aktif ? 'tali_off' : 'tali_on')}>🧵 Tali {v.tali_aktif ? 'ON' : 'OFF'} ({v.tali_sisa})</button>
              <button type="button" className="btn small" disabled={!live || v.suar_sisa <= 0} onClick={() => act('suar')}>🔦 Suar ({v.suar_sisa})</button>
              <span className="hint">{lari ? '🏃 Lari aktif: satu tekan menyusuri lorong' : 'Tip: Shift+panah = lari'}</span>
            </div>
            {palet && (
              <div className="lb-palette">
                {(v.simbol ?? []).map((sim: string) => (
                  <button key={sim} type="button" className="btn small" disabled={!live} onClick={() => { act({ tanda: sim }); setPalet(false); }}>{sim}</button>
                ))}
              </div>
            )}
          </div>
        )}
        {(v.riwayat ?? []).length > 0 && (
          <ul className="hist">
            {(v.riwayat ?? []).slice().reverse().map((r: any) => (
              <li key={r.ronde}>
                <b>Labirin {r.ronde}</b> <span className="hint">jalur terpendek {r.jalur_terpendek}</span>
                <span className="hist-chips">
                  {names.map((n) => (
                    <span key={n} className={`chip ${r.urutan[0] === n ? 'win' : ''}`} style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>
                      {n} {r.urutan.includes(n) ? `#${r.urutan.indexOf(n) + 1}` : '✗'} · {r.langkah[n]} lgk <b>+{r.poin[n]}</b>
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        )}
        {!replay && me == null && v.pandang !== 'terang' && <p className="hint">Penonton tidak melihat isi labirin berkabut (host bisa membuka semua untuk penonton).</p>}
      </div>
      <div>
        <ScoreBoard rows={rows} me={me} />
        {Object.values(v.pemain ?? {}).some((p: any) => p.selesai) && (
          <div className="panel"><h3>Sudah keluar</h3>
            <p>{Object.entries(v.pemain).filter(([, p]: [string, any]) => p.selesai)
              .sort((a: any, b: any) => a[1].urutan - b[1].urutan)
              .map(([n, p]: [string, any]) => <span key={n}>#{p.urutan} <NameChip name={n} idx={idxOf(names, n)} /> </span>)}</p>
          </div>
        )}
      </div>
    </div>
  );
}
