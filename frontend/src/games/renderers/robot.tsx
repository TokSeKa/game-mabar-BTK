import { useEffect } from 'react';
import { fmt, seatColor } from '../hubApi';
import { ScoreBoard, TurnNote, type RenderProps } from './common';

const KEYMOVE: Record<string, string> = {
  ArrowUp: 'atas', ArrowDown: 'bawah', ArrowLeft: 'kiri', ArrowRight: 'kanan',
  w: 'atas', s: 'bawah', a: 'kiri', d: 'kanan',
};
const KEYSHOT: Record<string, string> = { i: 'atas', k: 'bawah', j: 'kiri', l: 'kanan' };
const ARROW: Record<string, string> = { atas: '↑', bawah: '↓', kiri: '←', kanan: '→' };
const PU_ICON: Record<string, string> = { senjata: '⚡', perisai: '🛡️', nyawa: '❤️' };

export function RRobot({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const n: number = v.ukuran;
  const myName = me != null ? names[me] : null;
  const mine = myName ? v.robot[myName] : null;
  const ready = mine && mine.siap_tembak === 0 && mine.hidup;

  useEffect(() => {
    if (!canAct) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest('input, textarea, .cm-editor')) return;
      const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
      if (e.shiftKey && KEYMOVE[e.key]) {
        e.preventDefault();
        if (ready) act(`tembak_${KEYMOVE[e.key]}`);
      } else if (KEYSHOT[k]) {
        e.preventDefault();
        if (ready) act(`tembak_${KEYSHOT[k]}`);
      } else if (KEYMOVE[k]) {
        e.preventDefault();
        act(KEYMOVE[k]);
      } else if (k === ' ') {
        e.preventDefault();
        act('diam');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [canAct, ready, act]);

  const cell = 100 / n;
  const shots = (v.kejadian ?? []).filter((e: any) => e.jenis === 'tembak');
  const zona: [number, number] | null = v.zona ?? null;
  const rad: number = v.pandang ?? 0;
  // kabut: petak di luar jarak pandang robotku digelapkan (juga di replay sudut pandang pemain)
  const fogOn = rad > 0 && mine != null;
  const sees = (r: number, c: number) => !fogOn || Math.max(Math.abs(mine.baris - r), Math.abs(mine.kolom - c)) <= rad;
  const skor = v.skor ?? Object.fromEntries(Object.entries(v.robot ?? {}).map(([nm, b]: [string, any]) => [nm, { poin: b.poin, hidup: b.hidup, hancur: b.hancur }]));
  return (
    <div className="game-grid">
      <div className="panel robot-panel">
        <div className="row"><b>Giliran {v.giliran}/{v.giliran_total}</b><span className="spacer" />
          {mine && <span className="hint">Nyawamu {mine.nyawa}{mine.perisai ? ' 🛡️' : ''} · senjata {mine.siap_tembak === 0 ? 'siap' : `${mine.siap_tembak} giliran lagi`}</span>}</div>
        {(rad > 0 || zona) && (
          <p className="hint">
            {rad > 0 ? `🌫️ Kabut perang: jarak pandang ${rad} petak. ` : ''}
            {zona ? `🌀 Zona aman baris/kolom ${zona[0]}–${zona[1]}${v.zona_berikut ? `, menyempit lagi di giliran ${v.zona_berikut}` : ''}; di luar zona −1 nyawa tiap giliran.` : ''}
          </p>
        )}
        <svg className="arena-svg" viewBox="0 0 100 100" role="img" aria-label="Peta arena robot">
          <rect x="0" y="0" width="100" height="100" className="ar-floor" />
          {v.peta.map((row: string, r: number) =>
            row.split('').map((ch, c) => (ch === '#' ? <rect key={`${r}-${c}`} x={c * cell} y={r * cell} width={cell} height={cell} className="ar-wall" /> : null)),
          )}
          {zona && Array.from({ length: n }, (_, r) => Array.from({ length: n }, (_, c) => (
            r < zona[0] || r > zona[1] || c < zona[0] || c > zona[1]
              ? <rect key={`z${r}-${c}`} x={c * cell} y={r * cell} width={cell} height={cell} className="ar-storm" /> : null
          )))}
          {(v.powerup ?? []).map((pu: any, k: number) => (
            <text key={`pu${k}`} x={(pu.kolom + 0.5) * cell} y={(pu.baris + 0.72) * cell} fontSize={cell * 0.62} textAnchor="middle">{PU_ICON[pu.jenis] ?? '?'}</text>
          ))}
          {v.kristal.map(([r, c]: [number, number], k: number) => (
            <polygon key={k} className="ar-gem" points={`${(c + 0.5) * cell},${(r + 0.15) * cell} ${(c + 0.85) * cell},${(r + 0.5) * cell} ${(c + 0.5) * cell},${(r + 0.85) * cell} ${(c + 0.15) * cell},${(r + 0.5) * cell}`} />
          ))}
          {shots.map((s: any, k: number) => (
            <line key={k} className="ar-shot" x1={(s.dari[1] + 0.5) * cell} y1={(s.dari[0] + 0.5) * cell} x2={(s.sampai[1] + 0.5) * cell} y2={(s.sampai[0] + 0.5) * cell}
              style={{ stroke: seatColor(names.indexOf(s.pemain)) }} />
          ))}
          {names.map((nm, i) => {
            const b = v.robot?.[nm];
            if (!b) return null;
            const cx = (b.kolom + 0.5) * cell;
            const cy = (b.baris + 0.5) * cell;
            return (
              <g key={nm} className={`ar-bot ${b.hidup ? '' : 'dead'} ${nm === myName ? 'me' : ''}`}>
                <circle cx={cx} cy={cy} r={cell * 0.38} style={{ fill: seatColor(i) }} />
                <text x={cx} y={cy + cell * 0.14} fontSize={cell * 0.42} textAnchor="middle">{nm.slice(0, 1).toUpperCase()}</text>
                {b.hidup && Array.from({ length: b.nyawa }, (_, k) => (
                  <rect key={k} x={cx - cell * 0.4 + k * cell * 0.18} y={cy - cell * 0.62} width={cell * 0.14} height={cell * 0.1} className="ar-hp" />
                ))}
                {b.perisai && <circle cx={cx} cy={cy} r={cell * 0.48} className="ar-shield" />}
              </g>
            );
          })}
          {fogOn && Array.from({ length: n }, (_, r) => Array.from({ length: n }, (_, c) => (
            sees(r, c) ? null : <rect key={`f${r}-${c}`} x={c * cell} y={r * cell} width={cell} height={cell} className="ar-fog" />
          )))}
        </svg>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Panah/WASD = jalan, Shift+panah atau IJKL = tembak, spasi = diam.</TurnNote>
        {canAct && mine?.hidup && (
          <div className="robot-ctrl">
            <div className="pad">
              <span />
              <button type="button" className="btn" onClick={() => act('atas')} aria-label="jalan atas">↑</button>
              <span />
              <button type="button" className="btn" onClick={() => act('kiri')} aria-label="jalan kiri">←</button>
              <button type="button" className="btn" onClick={() => act('diam')} aria-label="diam">•</button>
              <button type="button" className="btn" onClick={() => act('kanan')} aria-label="jalan kanan">→</button>
              <span />
              <button type="button" className="btn" onClick={() => act('bawah')} aria-label="jalan bawah">↓</button>
              <span />
            </div>
            <div className="pad shoot">
              {(['atas', 'kiri', 'kanan', 'bawah'] as const).map((d) => (
                <button key={d} type="button" className="btn danger" disabled={!ready} onClick={() => act(`tembak_${d}`)} aria-label={`tembak ${d}`} style={{ gridArea: d }}>
                  💥{ARROW[d]}
                </button>
              ))}
            </div>
          </div>
        )}
        {mine && !mine.hidup && <p className="hint">Robotmu hancur{mine.bangkit_dalam != null ? `, bangkit lagi dalam ${mine.bangkit_dalam} giliran` : ''}.</p>}
        {!replay && <p className="hint">Urutan tiap giliran: semua robot <b>bergerak dulu</b>, baru tembakan dihitung. Tembaklah ke petak tujuan lawan, dan keluar dari garis tembak untuk menghindar.</p>}
      </div>
      <ScoreBoard
        rows={names
          .map((nm, i) => ({ nm, i, b: skor[nm] ?? { poin: 0, hidup: true, hancur: 0 }, full: v.robot?.[nm] }))
          .sort((a, b) => b.b.poin - a.b.poin)
          .map(({ nm, i, b, full }) => ({
            name: nm, idx: i, value: fmt(b.poin), dim: !b.hidup,
            sub: b.hidup ? `${full ? `❤ ${full.nyawa} · ` : ''}hancur ${b.hancur ?? 0}×` : 'hancur',
          }))}
        me={me}
        title="Poin"
      />
    </div>
  );
}
