import { useEffect, useRef, useState, type PointerEvent as RPointerEvent } from 'react';
import { seatColor } from '../hubApi';
import { ScoreBoard, TurnNote, touchScreen, type RenderProps } from './common';

const HITUNG_MUNDUR = 3000;

type Target = { nomor: number; x: number; y: number; r: number; vx: number; vy: number; jeda: number; sandera: boolean; grup: number; kembar: boolean };
type Grup = { key: string; targets: Target[]; showAt: number; shot: Set<number>; sent: Set<number>; ronde: number };
type Pop = { id: number; x: number; y: number; text: string; cls: string };

function reflect(p: number, lo: number, hi: number) {
  const L = hi - lo;
  if (L <= 0) return lo;
  const m = (((p - lo) % (2 * L)) + 2 * L) % (2 * L);
  return lo + (m <= L ? m : 2 * L - m);
}

/** Cincin & poin, sama persis dengan hitungan server (untuk umpan balik instan). */
function nilai(d: number, r: number, ms: number, T: number) {
  if (d > r) return { cincin: 0, poin: 0 };
  const cincin = Math.max(1, Math.min(10, Math.ceil((1 - d / r) * 10)));
  const faktor = Math.max(0.3, 1 - 0.7 * Math.min(1, Math.max(0, ms) / T));
  return { cincin, poin: Math.round(cincin * 10 * faktor) };
}

function Bullseye({ sandera }: { sandera: boolean }) {
  if (sandera) {
    return (
      <svg viewBox="-50 -50 100 100" className="tj-svg">
        <circle r={48} fill="#2f6fde" stroke="#cfe0ff" strokeWidth={3} />
        <circle cy={-14} r={13} fill="#e8f0ff" />
        <path d="M-24 34 Q-24 4 0 4 Q24 4 24 34 Z" fill="#e8f0ff" />
      </svg>
    );
  }
  const rings = [48, 39, 30, 21, 12];
  return (
    <svg viewBox="-50 -50 100 100" className="tj-svg">
      {rings.map((r, k) => <circle key={r} r={r} fill={k % 2 === 0 ? '#e5484d' : '#f4f1ea'} />)}
      <circle r={4} fill="#1a1a1a" />
    </svg>
  );
}

export function RTembak({ view, names, me, canAct, act, replay }: RenderProps) {
  const v = view;
  const T: number = v.waktu_target ?? 1600;
  const rasio: number = v.rasio ?? 0.625;
  const arena = useRef<HTMLDivElement>(null);
  const shell = useRef<HTMLDivElement>(null);
  const grup = useRef<Grup | null>(null);
  const [, frame] = useState(0);
  const [pops, setPops] = useState<Pop[]>([]);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [recoil, setRecoil] = useState(0);
  const [full, setFull] = useState(false);
  const aktif: Target[] = v.aktif ?? [];
  const playing = canAct && me != null && !replay && aktif.length > 0;

  // grup sasaran baru: atur kapan muncul (hitung mundur di awal ronde + jeda acak dari seed)
  const first = aktif[0];
  const key = first ? `${v.ronde}:${first.grup}` : '';
  if (playing && key && grup.current?.key !== key) {
    const now = performance.now();
    grup.current = {
      key, targets: aktif, ronde: v.ronde, shot: new Set(), sent: new Set(),
      showAt: now + (v.ke === 0 ? HITUNG_MUNDUR : 0) + (first.jeda ?? 600),
    };
  }
  const g = playing ? grup.current : null;

  // animasi + batas waktu target
  useEffect(() => {
    if (!g) return;
    let raf = 0;
    const tick = () => {
      const now = performance.now();
      const cur = grup.current;
      if (cur && now >= cur.showAt + T && !cur.sent.has(v.ke) && canAct) {
        cur.sent.add(v.ke);
        const left = cur.targets.find((t) => !cur.shot.has(t.nomor));
        if (left) cur.shot.add(left.nomor);
        act({ target: v.ke, lewat: true });
        if (left && !left.sandera) addPop(left.x, left.y, 'terlambat', 'miss');
        if (left?.sandera) addPop(left.x, left.y, '+10 menahan diri', 'good');
      }
      frame((x) => x + 1);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  });

  useEffect(() => {
    const onFs = () => setFull(document.fullscreenElement === shell.current);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  function addPop(x: number, y: number, text: string, cls: string) {
    const id = Date.now() + Math.random();
    setPops((p) => [...p.slice(-5), { id, x, y, text, cls }]);
    window.setTimeout(() => setPops((p) => p.filter((q) => q.id !== id)), 900);
  }

  const now = performance.now();
  const elapsed = g ? now - g.showAt : -1;
  const visible = g && elapsed >= 0 && elapsed < T ? g.targets.filter((t) => !g.shot.has(t.nomor)) : [];
  const posOf = (t: Target) => {
    const sec = Math.max(0, elapsed) / 1000;
    const r = v.menyusut ? t.r * Math.max(0.45, 1 - 0.55 * Math.min(1, Math.max(0, elapsed) / T)) : t.r;
    return { x: reflect(t.x + t.vx * sec, t.r, 1 - t.r), y: reflect(t.y + t.vy * sec, t.r, rasio - t.r), r };
  };
  const countdown = g && elapsed < 0 && v.ke === 0 ? Math.ceil((-elapsed - (first?.jeda ?? 0)) / 1000) : 0;

  const shoot = (e: RPointerEvent<HTMLDivElement>) => {
    if (!g || !canAct || g.sent.has(v.ke)) return;
    const box = arena.current?.getBoundingClientRect();
    if (!box) return;
    const ux = (e.clientX - box.left) / box.width;
    const uy = (e.clientY - box.top) / box.width;
    setRecoil((x) => x + 1);
    if (!visible.length) return;          // belum muncul: klik diabaikan (tidak memakan peluru)
    const ms = performance.now() - g.showAt;
    const cands = visible.map((t) => ({ t, p: posOf(t) })).map((o) => ({ ...o, d: Math.hypot(ux - o.p.x, uy - o.p.y) }));
    const hit = cands.filter((o) => o.d <= o.p.r).sort((a, b) => a.d - b.d)[0];
    let target = hit;
    if (!target) {
      const normal = cands.filter((o) => !o.t.sandera).sort((a, b) => a.d - b.d)[0];
      if (!normal) return;                // hanya sandera di layar dan tembakan tidak mengenainya: abaikan
      target = normal;
    }
    g.shot.add(target.t.nomor);
    g.sent.add(v.ke);
    act({ target: v.ke, dx: ux - target.p.x, dy: uy - target.p.y, ms: Math.round(ms) });
    if (target.t.sandera) addPop(ux, uy, '−30 sandera!', 'bad');
    else {
      const n = nilai(target.d, target.p.r, ms, T);
      addPop(ux, uy, n.cincin ? `+${n.poin} · ${n.cincin} · ${Math.round(ms)} ms` : 'meleset', n.cincin ? (n.cincin >= 9 ? 'great' : 'good') : 'miss');
    }
  };

  const toggleFull = () => {
    const el = shell.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => undefined);
    else el.requestFullscreen?.().catch(() => undefined);
  };

  const myName = me != null ? names[me] : null;
  const total = v.jumlah_target ?? 0;
  const hasil = myName ? v.hasil?.[myName] ?? [] : [];
  const last = v.riwayat?.[v.riwayat.length - 1];
  const rows = names.map((n, i) => ({
    name: n, idx: i, value: v.skor?.[n] ?? 0,
    sub: `${Math.min(v.progres?.[n] ?? 0, total)}/${total} · ronde ini ${v.poin_ronde?.[n] ?? 0}`,
  })).sort((a, b) => Number(b.value) - Number(a.value));

  return (
    <div className="game-grid tj">
      <div className="panel">
        <div className="row">
          <b>Ronde {v.ronde}/{v.ronde_total}</b>
          <span className="tag-mini">target {Math.min((v.ke ?? 0) + 1, total)}/{total}</span>
          <span className="hint">{(T / 1000).toFixed(1)} dtk per target{v.gerak !== 'diam' ? ' · bergerak' : ''}{v.menyusut ? ' · menyusut' : ''}</span>
          <span className="spacer" />
          <button type="button" className="btn small" onClick={toggleFull} title="Layar penuh">⛶ {full ? 'Keluar layar penuh' : 'Layar penuh'}</button>
        </div>
        <TurnNote canAct={canAct} acted={false} replay={replay} me={me}>
          {touchScreen ? 'Ketuk tepat di tengah sasaran secepat mungkin.' : 'Klik tepat di tengah sasaran secepat mungkin. Satu peluru per sasaran.'}
        </TurnNote>
        {!replay && me != null && !aktif.length && <div className="turn-note done">Semua sasaranmu sudah selesai. Menunggu yang lain…</div>}
        <div ref={shell} className={`tj-shell ${full ? 'full' : ''}`}>
          <div ref={arena} className={`tj-arena ${playing && !touchScreen ? 'aim' : ''}`} style={{ aspectRatio: `${1 / rasio}` }}
            onPointerDown={shoot}
            onPointerMove={(e) => {
              if (touchScreen || e.pointerType === 'touch') return;
              const b = arena.current?.getBoundingClientRect();
              if (b) setCursor({ x: e.clientX - b.left, y: e.clientY - b.top });
            }}
            onPointerLeave={() => setCursor(null)}>
            {visible.map((t) => {
              const p = posOf(t);
              return (
                <div key={t.nomor} className="tj-target" style={{ left: `${p.x * 100}%`, top: `${(p.y / rasio) * 100}%`, width: `${p.r * 200}%` }}>
                  <Bullseye sandera={t.sandera} />
                </div>
              );
            })}
            {countdown > 0 && <div className="tj-count">{countdown}</div>}
            {g && elapsed < 0 && countdown <= 0 && <div className="tj-ready">siap…</div>}
            {pops.map((p) => (
              <div key={p.id} className={`tj-pop ${p.cls}`} style={{ left: `${p.x * 100}%`, top: `${(p.y / rasio) * 100}%` }}>{p.text}</div>
            ))}
            {!playing && v.sasaran && (
              <>
                {v.sasaran.map((t: Target, k: number) => (
                  <div key={`s${k}`} className="tj-target ghost" style={{ left: `${t.x * 100}%`, top: `${(t.y / rasio) * 100}%`, width: `${t.r * 200}%` }}>
                    <Bullseye sandera={t.sandera} />
                    <span className="tj-no">{k + 1}</span>
                  </div>
                ))}
                {names.map((n, i) => (v.hasil?.[n] ?? []).map((h: any, k: number) => {
                  const t: Target | undefined = v.sasaran[h.nomor];
                  if (!t || h.dx == null) return null;
                  return <span key={`${n}${k}`} className="tj-hit" title={`${n}: cincin ${h.cincin}, ${h.ms} ms`}
                    style={{ left: `${(t.x + h.dx * t.r) * 100}%`, top: `${((t.y + h.dy * t.r) / rasio) * 100}%`, ['--c' as string]: seatColor(i) }} />;
                }))}
              </>
            )}
            {!playing && !v.sasaran && me == null && <div className="tj-ready">Sasaran hanya terlihat oleh penembaknya. Lihat skor di samping.</div>}
            {cursor && playing && (
              <div className="tj-cursor" style={{ left: cursor.x, top: cursor.y }}>
                <svg viewBox="-20 -20 40 40" className="tj-cross"><circle r={11} /><line x1={-18} x2={-5} y1={0} y2={0} /><line x1={5} x2={18} y1={0} y2={0} /><line y1={-18} y2={-5} x1={0} x2={0} /><line y1={5} y2={18} x1={0} x2={0} /><circle r={1.6} className="dot" /></svg>
                <svg key={recoil} viewBox="0 0 64 40" className="tj-gun">
                  <path d="M4 8 h44 l6 -4 h6 v10 h-10 v4 h-14 l-6 18 h-12 l5 -18 h-19 z" />
                  <rect x={30} y={18} width={5} height={7} className="trig" />
                </svg>
              </div>
            )}
          </div>
        </div>
        {hasil.length > 0 && (
          <div className="tj-hasil" aria-label="Hasil tembakanmu ronde ini">
            {hasil.map((h: any, k: number) => (
              <span key={k} className={`tj-chip ${h.sandera ? (h.tahan ? 'good' : 'bad') : h.cincin >= 9 ? 'great' : h.cincin ? 'good' : 'miss'}`}
                title={h.ms ? `${h.ms} ms` : undefined}>
                {h.sandera ? (h.tahan ? '🧍+10' : '😱−30') : h.cincin ? `${h.cincin}·${h.poin}` : '✕'}
              </span>
            ))}
          </div>
        )}
        {last && (
          <p className="hint">Ronde {last.ronde}: {Object.entries(last.poin).sort((a: any, b: any) => b[1] - a[1])
            .map(([n, p]) => `${n} ${p} (${last.kena?.[n] ?? 0} kena, rata-rata ${last.rata_ms?.[n] ?? '-'} ms)`).join(' · ')}</p>
        )}
      </div>
      <ScoreBoard me={me} rows={rows} />
    </div>
  );
}
