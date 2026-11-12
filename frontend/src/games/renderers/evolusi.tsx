import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { seatColor } from '../hubApi';
import { NameChip, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const ARAH: Record<string, [number, number]> = {
  timur: [1, 0], timur_laut: [1, -1], barat_laut: [0, -1], barat: [-1, 0], barat_daya: [-1, 1], tenggara: [0, 1],
};
const PANAH: Record<string, string> = { timur: '→', timur_laut: '↗', barat_laut: '↖', barat: '←', barat_daya: '↙', tenggara: '↘' };
const PAD = [['barat_laut', 'timur_laut'], ['barat', 'timur'], ['barat_daya', 'tenggara']];
const MAKAN: Record<string, string> = { rumput: '🌱', buah: '🍎', daging: '🍖' };
const SIFAT: [string, string, string][] = [['pandangan', '👁️', 'Pandangan'], ['kelincahan', '🐾', 'Kelincahan'], ['ukuran', '🦣', 'Ukuran']];
const MODE: [string, string][] = [['naluri', '🧠 Naluri'], ['tujuan', '🎯 Tujuan'], ['manual', '🕹️ Manual'], ['diam', '⏸ Diam']];
const S = 16;
const SQ3 = Math.sqrt(3);

const xy = (q: number, r: number) => [S * SQ3 * (q + r / 2), S * 1.5 * r];
const hexPts = (cx: number, cy: number, s = S) =>
  Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 180) * (60 * i - 30);
    return `${(cx + s * Math.cos(a)).toFixed(1)},${(cy + s * Math.sin(a)).toFixed(1)}`;
  }).join(' ');

const stepCost = (u: number, a: number) => Math.max(0.05, Math.round((u / 5) ** 3 * (a / 5) * 1000) / 1000);

type Order = {
  perintah?: Record<string, { mode: string; tujuan?: number[]; jalan?: string[] }>;
  beranak?: Record<string, boolean>;
  nama?: Record<string, string>;
  desain?: Record<string, number>;
  pasang?: { makhluk: string; arah: string; jenis: string };
};

function DesignPicker({ value, budget, onChange, disabled }: { value: Record<string, number>; budget: number; onChange: (v: Record<string, number>) => void; disabled?: boolean }) {
  const total = SIFAT.reduce((a, [id]) => a + (value[id] ?? 1), 0);
  const u = value.ukuran ?? 1;
  const ag = value.kelincahan ?? 1;
  return (
    <div className="evo-design">
      {SIFAT.map(([id, ikon, label]) => (
        <label key={id} className="evo-trait">
          <span>{ikon} {label}</span>
          <input type="range" min={1} max={9} value={value[id] ?? 1} disabled={disabled}
            onChange={(e) => {
              const next = { ...value, [id]: Number(e.target.value) };
              if (SIFAT.reduce((a, [x]) => a + (next[x] ?? 1), 0) <= budget) onChange(next);
            }} />
          <b>{value[id] ?? 1}</b>
        </label>
      ))}
      <p className={`hint ${total > budget ? 'bad' : ''}`}>
        Poin dipakai {total}/{budget} · HP {10 + 5 * u} · energi maks {40 + 12 * u} · langkah {stepCost(u, ag)} energi ·
        pandangan {(0.25 * (value.pandangan ?? 1)).toFixed(2)}/giliran · lahir {25 + 5 * u} energi
      </p>
    </div>
  );
}

export function REvolusi({ view, names, me, canAct, acted, act, draft, replay }: RenderProps) {
  const v = view;
  const R: number = v.radius;
  const mine: any[] = v.makhluk_saya ?? [];
  const myName = me != null ? names[me] : null;
  const [order, setOrderRaw] = useResetState<Order>({}, `${v.giliran}-${v.fase}`);
  const [sel, setSel] = useState<string | null>(null);
  const [design, setDesign] = useResetState<Record<string, number>>(v.desain ?? { pandangan: 5, kelincahan: 5, ukuran: 5 }, `${v.fase}`);
  const [pasangJenis, setPasangJenis] = useState<'batu' | 'duri'>('duri');
  const setOrder = (o: Order) => {
    setOrderRaw(o);
    draft?.(o);
  };
  useEffect(() => {
    if (v.fase === 'desain' && canAct) draft?.({ desain: design });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAct, v.fase]);
  const selected = mine.find((m) => m.id === sel) ?? null;
  const vis = useMemo(() => (v.terlihat ? new Set<string>(v.terlihat) : null), [v.terlihat]);

  if (v.fase === 'desain') {
    return (
      <div className="game-grid evo">
        <div className="panel">
          <h3>🧬 Desain spesiesmu</h3>
          <p className="hint">Bagi {v.poin_sifat} poin ke tiga sifat. Makhluk besar & cepat boros energi; pandangan membayar tiap giliran.</p>
          <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Atur sifat lalu tekan Siap.</TurnNote>
          {me != null && !replay && (
            <>
              <DesignPicker value={design} budget={v.poin_sifat} disabled={!canAct}
                onChange={(d) => { setDesign(d); draft?.({ desain: d }); }} />
              {canAct && <button type="button" className="btn primary" onClick={() => act({ desain: design })}>✅ Siap</button>}
            </>
          )}
        </div>
        <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: 0 }))} />
      </div>
    );
  }

  const ord = order;
  const cmdOf = (id: string) => ord.perintah?.[id];
  const modeOf = (m: any) => cmdOf(m.id)?.mode ?? m.mode;
  const planned: Record<string, number[][]> = {};
  for (const m of mine) {
    const c = cmdOf(m.id);
    if (c?.jalan?.length) {
      let cur = m.posisi;
      planned[m.id] = c.jalan.map((a) => (cur = [cur[0] + ARAH[a][0], cur[1] + ARAH[a][1]]));
    }
  }
  const setCmd = (id: string, c: { mode: string; tujuan?: number[]; jalan?: string[] }) =>
    setOrder({ ...ord, perintah: { ...(ord.perintah ?? {}), [id]: c } });
  const clickHex = (q: number, r: number) => {
    const own = mine.find((m) => m.posisi[0] === q && m.posisi[1] === r);
    if (own) {
      setSel(own.id);
      return;
    }
    if (selected && canAct) setCmd(selected.id, { mode: 'tujuan', tujuan: [q, r] });
  };
  const addStep = (a: string) => {
    if (!selected) return;
    const c = cmdOf(selected.id);
    const jalan = [...(c?.jalan ?? []), a].slice(0, selected.kelincahan);
    setCmd(selected.id, { mode: 'manual', jalan });
  };

  const cells: ReactNode[] = [];
  const [minX, maxX] = [-S * SQ3 * (R + 0.6), S * SQ3 * (R + 0.6)];
  const [minY, maxY] = [-S * 1.5 * R - S * 1.2, S * 1.5 * R + S * 1.2];
  for (const [kk, t] of Object.entries(v.peta as Record<string, string>)) {
    const [q, r] = kk.split(',').map(Number);
    const [cx, cy] = xy(q, r);
    const dim = vis != null && !vis.has(kk);
    cells.push(
      <g key={kk} onClick={() => clickHex(q, r)} className="evo-cell">
        <polygon points={hexPts(cx, cy, S - 0.6)} className={`evo-hex t-${t === '#' ? 'batu' : t === 's' ? 'semak' : 'tanah'} ${dim ? 'dim' : ''}`} />
        {t === '#' && <text x={cx} y={cy} className="evo-ico">🪨</text>}
        {t === 's' && <text x={cx} y={cy} className="evo-ico bush">🌿</text>}
      </g>,
    );
  }
  const tujuanLines = mine.filter((m) => modeOf(m) === 'tujuan').map((m) => {
    const t = cmdOf(m.id)?.tujuan ?? m.tujuan;
    if (!t) return null;
    const [x1, y1] = xy(m.posisi[0], m.posisi[1]);
    const [x2, y2] = xy(t[0], t[1]);
    return <line key={`t${m.id}`} x1={x1} y1={y1} x2={x2} y2={y2} className="evo-goal" />;
  });
  const manualLines = Object.entries(planned).map(([id, pts]) => {
    const m = mine.find((x) => x.id === id);
    const all = [m.posisi, ...pts].map(([q, r]) => xy(q, r).join(',')).join(' ');
    return <polyline key={`m${id}`} points={all} className="evo-path" />;
  });

  return (
    <div className="game-grid evo">
      <div className="panel">
        <div className="row"><b>Giliran {v.giliran}/{v.giliran_total}</b><span className="spacer" />
          <span className="hint">{v.terlihat ? '🌫️ kabut' : '☀️ terang'} · memangsa kalau ukuran ≥ {v.rasio_mangsa}× lawan</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          Pilih makhluk (klik di peta / daftar), atur perintahnya, lalu kirim. Tanpa perintah baru, makhluk melanjutkan perintah lamanya.
        </TurnNote>
        <div className="evo-wrap">
          <svg className="evo-svg" viewBox={`${minX} ${minY} ${maxX - minX} ${maxY - minY}`} role="img" aria-label="Peta heksagon">
            <g>{cells}</g>
            {Object.entries(v.sarang_semua ?? {}).map(([n, p]: [string, any]) => {
              const [cx, cy] = xy(p[0], p[1]);
              return <polygon key={`n${n}`} points={hexPts(cx, cy, S - 2)} className="evo-nest" style={{ stroke: seatColor(idxOf(names, n)) }} />;
            })}
            {(v.makanan ?? []).map((f: any) => {
              const [cx, cy] = xy(f[0], f[1]);
              return <text key={`f${f[0]},${f[1]}`} x={cx} y={cy} className="evo-ico food">{MAKAN[f[2]]}</text>;
            })}
            {(v.jebakan ?? []).map((t: any) => {
              const [cx, cy] = xy(t[0], t[1]);
              return <text key={`j${t[0]},${t[1]}`} x={cx} y={cy} className="evo-ico">{t[2] === 'duri' ? '🌵' : '🕳️'}</text>;
            })}
            <g>{tujuanLines}</g>
            <g>{manualLines}</g>
            {[...mine.map((m) => ({ ...m, pemilik: myName, mine: true })), ...(v.makhluk_lain ?? [])].map((m: any) => {
              const [cx, cy] = xy(m.posisi[0], m.posisi[1]);
              const rad = S * (0.32 + 0.06 * m.ukuran);
              const isSel = m.id === sel;
              return (
                <g key={`c${m.id}`} onClick={() => m.mine && setSel(m.id)} className={m.mine ? 'evo-own' : ''}>
                  <circle cx={cx} cy={cy} r={Math.min(rad, S * 0.9)} className={`evo-crit ${isSel ? 'sel' : ''}`}
                    style={{ fill: seatColor(idxOf(names, m.pemilik)) }} />
                  {m.mine && <text x={cx} y={cy} className="evo-num">{String(m.nama).replace('#', '').slice(0, 3)}</text>}
                </g>
              );
            })}
          </svg>
        </div>
        {me != null && !replay && (
          <div className="evo-side">
            <h3>Spesiesku ({mine.length}/{v.maks_populasi})</h3>
            {mine.length === 0 && <p className="hint">Spesiesmu punah{v.giliran ? '. Tunggu bangkit di sarang (kalau diaktifkan host).' : '.'}</p>}
            <ul className="evo-list">
              {mine.map((m) => {
                const mode = modeOf(m);
                const beranak = ord.beranak?.[m.id] ?? m.beranak;
                const nama = ord.nama?.[m.id] ?? m.nama;
                return (
                  <li key={m.id} className={m.id === sel ? 'sel' : ''} onClick={() => setSel(m.id)}>
                    <div className="row">
                      <span className="dot" style={{ ['--c' as string]: seatColor(me) }} />
                      {canAct ? (
                        <input className="input evo-name" value={nama} maxLength={16} onClick={(e) => e.stopPropagation()}
                          onChange={(e) => setOrder({ ...ord, nama: { ...(ord.nama ?? {}), [m.id]: e.target.value } })} />
                      ) : <b>{nama}</b>}
                      <small className="hint">👁️{m.pandangan} 🐾{m.kelincahan} 🦣{m.ukuran}</small>
                    </div>
                    <div className="evo-bars">
                      <span className="evo-bar hp" title={`HP ${m.hp}/${m.hp_maks}`}><i style={{ width: `${(m.hp / m.hp_maks) * 100}%` }} /></span>
                      <span className="evo-bar en" title={`Energi ${m.energi}/${m.energi_maks}`}><i style={{ width: `${(m.energi / m.energi_maks) * 100}%` }} /></span>
                      <small className="hint">⚡{Math.round(m.energi)}</small>
                    </div>
                    {canAct && (
                      <div className="row evo-ctl" onClick={(e) => e.stopPropagation()}>
                        <select className="input" value={mode} onChange={(e) => setCmd(m.id, { mode: e.target.value, ...(e.target.value === 'tujuan' && m.tujuan ? { tujuan: m.tujuan } : {}) })}>
                          {MODE.map(([id, l]) => <option key={id} value={id}>{l}</option>)}
                        </select>
                        <button type="button" className={`btn small ${beranak ? 'primary' : ''}`} title="Beranak kalau energi cukup"
                          onClick={() => setOrder({ ...ord, beranak: { ...(ord.beranak ?? {}), [m.id]: !beranak } })}>🍼 {beranak ? 'ON' : 'OFF'}</button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            {canAct && selected && (
              <div className="evo-sel">
                <b>{ord.nama?.[selected.id] ?? selected.nama}</b>{' '}
                {modeOf(selected) === 'tujuan' && <span className="hint">🎯 klik petak di peta untuk memilih tujuan.</span>}
                <div className="evo-pad">
                  {PAD.map((row, i) => (
                    <div key={i} className={`row evo-pad-row r${i}`}>
                      {row.map((a) => <button key={a} type="button" className="btn small" onClick={() => addStep(a)} title={a}>{PANAH[a]}</button>)}
                    </div>
                  ))}
                </div>
                <p className="hint">Langkah manual giliran ini: {(cmdOf(selected.id)?.jalan ?? []).map((a) => PANAH[a]).join(' ') || '–'} (maks {selected.kelincahan})
                  {cmdOf(selected.id)?.jalan?.length ? <button type="button" className="btn small" onClick={() => setCmd(selected.id, { mode: 'manual', jalan: [] })}>Hapus</button> : null}</p>
                {v.rintangan_sisa > 0 && (
                  <div className="row evo-pasang">
                    <span>Pasang ({v.rintangan_sisa}):</span>
                    <select className="input" value={pasangJenis} onChange={(e) => setPasangJenis(e.target.value as 'batu' | 'duri')}>
                      <option value="duri">🌵 duri</option><option value="batu">🪨 batu</option>
                    </select>
                    {Object.keys(ARAH).map((a) => (
                      <button key={a} type="button" className={`btn small ${ord.pasang?.arah === a && ord.pasang?.makhluk === selected.id ? 'primary' : ''}`}
                        onClick={() => setOrder({ ...ord, pasang: { makhluk: selected.id, arah: a, jenis: pasangJenis } })}>{PANAH[a]}</button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {canAct && (
              <details className="evo-anak">
                <summary>🧬 Desain anak berikutnya</summary>
                <DesignPicker value={ord.desain ?? v.desain} budget={v.poin_sifat} onChange={(d) => setOrder({ ...ord, desain: d })} />
              </details>
            )}
            {canAct && (
              <button type="button" className="btn primary" onClick={() => act(ord)}>
                Kirim perintah{Object.keys(ord).length ? ` (${Object.keys(ord.perintah ?? {}).length + Object.keys(ord.beranak ?? {}).length + (ord.pasang ? 1 : 0) + Object.keys(ord.nama ?? {}).length + (ord.desain ? 1 : 0)} perubahan)` : ''}
              </button>
            )}
          </div>
        )}
      </div>
      <div>
        <ScoreBoard me={me} rows={names.map((n, i) => ({
          name: n, idx: i, value: v.skor?.[n] ?? 0,
          sub: `🧬 ${v.populasi?.[n] ?? 0} hidup · 🍽️ ${v.statistik?.[n]?.makan ?? 0} · 🦷 ${v.statistik?.[n]?.mangsa ?? 0} · 🍼 ${v.statistik?.[n]?.lahir ?? 0}`,
          dim: (v.populasi?.[n] ?? 0) === 0,
        })).sort((a, b) => Number(b.value) - Number(a.value))} />
        <div className="panel evo-legend">
          <h3>Legenda</h3>
          <p className="hint">🌱 +12 · 🍎 +25 · 🍖 +45 energi · 🌿 semak (isi tersembunyi) · 🪨 batu · 🌵 duri · 🕳️ jebakan.
            Lingkaran = makhluk (makin besar = makin besar ukurannya). Segi enam bergaris = sarang.</p>
          {myName == null && <p className="hint">Penonton: {Object.entries(v.populasi ?? {}).map(([n, x]) => <span key={n}><NameChip name={n} idx={idxOf(names, n)} /> {String(x)} </span>)}</p>}
        </div>
      </div>
    </div>
  );
}
