import { useEffect, useRef, useState, type TouchEvent } from 'react';
import { seatColor } from '../hubApi';
import { ScoreBoard, TurnNote, touchScreen, type RenderProps } from './common';

const KEYS: Record<string, string> = {
  ArrowUp: 'atas', ArrowDown: 'bawah', ArrowLeft: 'kiri', ArrowRight: 'kanan',
  w: 'atas', s: 'bawah', a: 'kiri', d: 'kanan', W: 'atas', S: 'bawah', A: 'kiri', D: 'kanan',
};
const BALIK: Record<string, string> = { atas: 'bawah', bawah: 'atas', kiri: 'kanan', kanan: 'kiri' };
const FRUIT: Record<string, string> = { apel: '#e5484d', emas: '#f5c542', busuk: '#7a3b2e' };

export function RUlar({ view, names, me, canAct, act, replay }: RenderProps) {
  const v = view;
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [w, setW] = useState(480);
  const myName = me != null ? names[me] : null;
  const mine = myName ? v.ular?.[myName] : null;
  const lastSent = useRef<{ d: string; t: number }>({ d: '', t: -1 });

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const fit = () => setW(Math.max(220, Math.min(el.clientWidth, 720, Math.round(window.innerHeight * 0.68))));
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const steer = (d: string) => {
    if (!canAct || !mine?.hidup) return;
    // jangan kirim arah yang sama berulang, dan jangan berbalik dari arah yang baru saja dikirim
    const cur = lastSent.current.t === v.detak ? lastSent.current.d : mine.arah;
    if (d === cur || d === BALIK[cur]) return;
    lastSent.current = { d, t: v.detak };
    act(d);
  };

  useEffect(() => {
    if (replay || me == null) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
      const d = KEYS[e.key];
      if (!d) return;
      e.preventDefault();
      steer(d);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  // gambar arena
  useEffect(() => {
    const cv = canvas.current;
    if (!cv) return;
    const N: number = v.ukuran;
    const cell = Math.floor(w / N);
    const size = cell * N;
    const dpr = window.devicePixelRatio || 1;
    cv.width = size * dpr;
    cv.height = size * dpr;
    cv.style.width = `${size}px`;
    cv.style.height = `${size}px`;
    const g = cv.getContext('2d');
    if (!g) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = '#121320';
    g.fillRect(0, 0, size, size);
    g.strokeStyle = 'rgba(255,255,255,0.035)';
    g.lineWidth = 1;
    for (let i = 1; i < N; i++) {
      g.beginPath(); g.moveTo(i * cell + 0.5, 0); g.lineTo(i * cell + 0.5, size); g.stroke();
      g.beginPath(); g.moveTo(0, i * cell + 0.5); g.lineTo(size, i * cell + 0.5); g.stroke();
    }
    if (!v.tembus_tepi) {
      g.strokeStyle = 'rgba(255,90,90,0.55)';
      g.lineWidth = 2;
      g.strokeRect(1, 1, size - 2, size - 2);
    }
    g.fillStyle = '#4a4b5e';
    for (const [x, y] of v.dinding ?? []) g.fillRect(x * cell, y * cell, cell, cell);
    for (const [x, y, j] of v.buah ?? []) {
      g.fillStyle = FRUIT[j] ?? '#e5484d';
      g.beginPath();
      g.arc(x * cell + cell / 2, y * cell + cell / 2, cell * (j === 'emas' ? 0.42 : 0.36), 0, Math.PI * 2);
      g.fill();
      if (j === 'emas') {
        g.strokeStyle = '#fff6c2'; g.lineWidth = 1.5; g.stroke();
      }
    }
    names.forEach((n, i) => {
      const u = v.ular?.[n];
      if (!u?.hidup || !u.badan?.length) return;
      const col = seatColor(i);
      u.badan.forEach(([x, y]: number[], k: number) => {
        g.globalAlpha = k === 0 ? 1 : Math.max(0.45, 1 - k * 0.025);
        g.fillStyle = col;
        const pad = k === 0 ? 0.5 : 1.5;
        g.fillRect(x * cell + pad, y * cell + pad, cell - 2 * pad, cell - 2 * pad);
      });
      g.globalAlpha = 1;
      const [hx, hy] = u.badan[0];
      if (n === myName) {
        g.strokeStyle = '#fff'; g.lineWidth = 2;
        g.strokeRect(hx * cell + 1, hy * cell + 1, cell - 2, cell - 2);
      }
      // mata
      const dir: Record<string, number[]> = { atas: [0, -1], bawah: [0, 1], kiri: [-1, 0], kanan: [1, 0] };
      const [dx, dy] = dir[u.arah] ?? [1, 0];
      g.fillStyle = '#111';
      const cx = hx * cell + cell / 2 + dx * cell * 0.18;
      const cy = hy * cell + cell / 2 + dy * cell * 0.18;
      const ox = dy !== 0 ? cell * 0.18 : 0;
      const oy = dx !== 0 ? cell * 0.18 : 0;
      g.beginPath(); g.arc(cx - ox, cy - oy, Math.max(1.2, cell * 0.09), 0, Math.PI * 2); g.fill();
      g.beginPath(); g.arc(cx + ox, cy + oy, Math.max(1.2, cell * 0.09), 0, Math.PI * 2); g.fill();
    });
  }, [v, w, names, myName]);

  // geser di HP
  const touch = useRef<{ x: number; y: number } | null>(null);
  const onTouchStart = (e: TouchEvent) => {
    const t = e.touches[0];
    touch.current = t ? { x: t.clientX, y: t.clientY } : null;
  };
  const onTouchMove = (e: TouchEvent) => {
    const a = touch.current;
    const t = e.touches[0];
    if (!a || !t) return;
    const dx = t.clientX - a.x, dy = t.clientY - a.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 22) return;
    steer(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'kanan' : 'kiri') : (dy > 0 ? 'bawah' : 'atas'));
    touch.current = { x: t.clientX, y: t.clientY };     // bisa belok berkali-kali dalam satu geseran
  };

  const kec = v.kecepatan || 6;
  const mulai = Math.ceil((v.mulai_dalam ?? 0) / kec);
  const sisa = Math.ceil((v.sisa_detak ?? 0) / kec);
  const rows = names.map((n, i) => {
    const u = v.ular?.[n];
    return {
      name: n, idx: i, value: v.skor?.[n] ?? 0, dim: !u?.hidup,
      sub: u?.keluar ? 'keluar' : !u?.hidup ? `bangkit ${Math.ceil((u?.bangkit_dalam ?? 0) / kec)} dtk` : `panjang ${u.panjang}`,
    };
  }).sort((a, b) => Number(b.value) - Number(a.value));
  const last = v.riwayat?.[v.riwayat.length - 1];

  return (
    <div className="game-grid ul">
      <div className="panel">
        <div className="row">
          <b>Ronde {v.ronde}/{v.ronde_total}</b>
          <span className="tag-mini">{v.ukuran}×{v.ukuran}</span>
          <span className="spacer" />
          <span className={`ul-clock ${sisa <= 10 ? 'low' : ''}`}>⏱ {Math.floor(sisa / 60)}:{String(sisa % 60).padStart(2, '0')}</span>
        </div>
        <TurnNote canAct={canAct} acted={false} replay={replay} me={me}>
          {touchScreen ? 'Geser di arena atau pakai tombol panah untuk belok.' : 'Belok dengan panah atau WASD.'}
        </TurnNote>
        {mine && !mine.hidup && !replay && (
          <div className="turn-note">{mine.keluar ? '💥 Ularmu tumbang dan keluar dari ronde ini.' : `💥 Tumbang! Bangkit lagi dalam ${Math.ceil((mine.bangkit_dalam ?? 0) / kec)} detik…`}</div>
        )}
        <div ref={wrap} className={`ul-wrap ${canAct ? 'swipe' : ''}`} onTouchStart={onTouchStart} onTouchMove={onTouchMove}>
          <canvas ref={canvas} className="ul-canvas" aria-label="Arena ular" />
          {mulai > 0 && <div className="ul-count">{mulai}</div>}
          {mulai === 0 && last && last.ronde === v.ronde - 1 && (v.detak ?? 0) < kec * 4.5 && (
            <div className="ul-count small">Ronde {last.ronde}: terpanjang {last.terpanjang ?? '-'}</div>
          )}
        </div>
        {me != null && !replay && (
          <div className="ul-pad">
            <span />
            <button type="button" className="btn big" onClick={() => steer('atas')} aria-label="Atas">↑</button>
            <span />
            <button type="button" className="btn big" onClick={() => steer('kiri')} aria-label="Kiri">←</button>
            <button type="button" className="btn big" onClick={() => steer('bawah')} aria-label="Bawah">↓</button>
            <button type="button" className="btn big" onClick={() => steer('kanan')} aria-label="Kanan">→</button>
          </div>
        )}
        <p className="hint ul-legend">
          <span style={{ color: FRUIT.apel }}>●</span> apel +1 · <span style={{ color: FRUIT.emas }}>●</span> emas +3
          {(v.buah ?? []).some((b: any[]) => b[2] === 'busuk') && <> · <span style={{ color: FRUIT.busuk }}>●</span> busuk −2</>}
          {' · '}tabrak = {v.tabrakan === 'habis' ? 'keluar ronde' : '−3 lalu bangkit'}{v.tembus_tepi ? ' · tepi tembus' : ''}
        </p>
      </div>
      <ScoreBoard me={me} rows={rows} />
    </div>
  );
}
