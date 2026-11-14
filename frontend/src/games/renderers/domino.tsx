import { useState } from 'react';
import { NameChip, ScoreBoard, TurnNote, idxOf, type RenderProps } from './common';

/** Posisi titik (grid 3×3, 0..2) untuk angka 0–9. */
const PIPS: Record<number, [number, number][]> = {
  0: [],
  1: [[1, 1]],
  2: [[0, 0], [2, 2]],
  3: [[0, 0], [1, 1], [2, 2]],
  4: [[0, 0], [2, 0], [0, 2], [2, 2]],
  5: [[0, 0], [2, 0], [1, 1], [0, 2], [2, 2]],
  6: [[0, 0], [0, 1], [0, 2], [2, 0], [2, 1], [2, 2]],
  7: [[0, 0], [0, 1], [0, 2], [2, 0], [2, 1], [2, 2], [1, 1]],
  8: [[0, 0], [0, 1], [0, 2], [2, 0], [2, 1], [2, 2], [1, 0], [1, 2]],
  9: [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
};

function Half({ n, x, y, s }: { n: number; x: number; y: number; s: number }) {
  const pad = s * 0.24;
  const step = (s - 2 * pad) / 2;
  return (
    <>
      {(PIPS[n] ?? []).map(([cx, cy], k) => (
        <circle key={k} cx={x + pad + cx * step} cy={y + pad + cy * step} r={s * 0.085} className={`dm-pip p${n}`} />
      ))}
    </>
  );
}

/** Kartu domino. ``vertical``: angka a di atas, b di bawah. */
export function Tile({ k, vertical, size = 26, hl, dim, back, onClick, title }: {
  k?: number[]; vertical?: boolean; size?: number; hl?: boolean; dim?: boolean; back?: boolean; onClick?: () => void; title?: string;
}) {
  const w = vertical ? size : size * 2;
  const h = vertical ? size * 2 : size;
  const body = (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className={`dm-tile ${hl ? 'hl' : ''} ${dim ? 'dim' : ''} ${back ? 'back' : ''}`}
      role="img" aria-label={back || !k ? 'kartu tertutup' : `${k[0]}-${k[1]}`}>
      <rect x={0.75} y={0.75} width={w - 1.5} height={h - 1.5} rx={size * 0.18} className="dm-face" />
      {!back && k && (
        <>
          {vertical
            ? <line x1={size * 0.18} y1={size} x2={size * 0.82} y2={size} className="dm-line" />
            : <line x1={size} y1={size * 0.18} x2={size} y2={size * 0.82} className="dm-line" />}
          <Half n={k[0]} x={0} y={0} s={size} />
          <Half n={k[1]} x={vertical ? 0 : size} y={vertical ? size : 0} s={size} />
        </>
      )}
    </svg>
  );
  if (!onClick) return <span className="dm-wrap" title={title}>{body}</span>;
  return <button type="button" className="dm-wrap dm-btn" onClick={onClick} title={title}>{body}</button>;
}

export function RDomino({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const [pick, setPick] = useState<number | null>(null);
  const myName = me != null ? names[me] : null;
  const hand: number[][] = v.tangan ?? (myName && v.tangan_semua ? v.tangan_semua[myName] : null) ?? [];
  const sah: { kartu: number; sisi: string }[] = v.sah ?? [];
  const playable = new Set(sah.map((a) => a.kartu));
  const sidesOf = (i: number) => sah.filter((a) => a.kartu === i).map((a) => a.sisi);
  const meja: number[][] = v.meja ?? [];
  const ujung: number[] | null = v.ujung;
  const myTurn = canAct && v.giliran === myName;

  const choose = (i: number) => {
    const sides = sidesOf(i);
    if (!sides.length) return;
    if (sides.length === 1) {
      setPick(null);
      act({ kartu: i, sisi: sides[0] });
    } else setPick(pick === i ? null : i);
  };
  const tim: string[][] | null = v.tim;
  const timOf = (n: string) => (tim ? (tim[0].includes(n) ? 0 : 1) : null);
  const last = v.riwayat?.[v.riwayat.length - 1];

  return (
    <div className="game-grid dm">
      <div className="panel">
        <div className="row">
          <b>Ronde {v.ronde}/{v.ronde_total}</b>
          <span className="tag-mini">{v.aturan === 'gaple' ? 'Gaple' : 'Draw'}</span>
          <span className="tag-mini">balak {v.set}</span>
          {v.aturan === 'draw' && <span className="hint">tumpukan {v.tumpukan}</span>}
          <span className="spacer" />
          {v.giliran && <span className="hint">giliran <NameChip name={v.giliran} idx={idxOf(names, v.giliran)} /></span>}
        </div>
        {last && last.ronde === v.ronde - 1 && meja.length === 0 && (
          <div className="dm-last">
            Ronde {last.ronde}: <b>{last.pemenang}</b> menang ({last.cara === 'habis' ? 'kartu habis' : 'meja buntu'}){last.kali > 1 ? ' · tutup balak ×2' : ''}
            {' · '}{Object.entries(last.poin).filter(([, p]) => p !== 0).map(([n, p]) => `${n} ${Number(p) > 0 ? '+' : ''}${p}`).join(', ') || 'tanpa poin'}
          </div>
        )}
        <div className="dm-table" aria-label="Meja">
          {meja.length === 0 && <span className="hint">Meja masih kosong{v.wajib ? ` — dibuka dengan balak ${v.wajib[0]}-${v.wajib[1]}` : ''}.</span>}
          {meja.map((k, i) => (
            <Tile key={i} k={k} vertical={k[0] === k[1]} size={22} hl={i === 0 || i === meja.length - 1} />
          ))}
        </div>
        {ujung && (
          <div className="dm-ends">
            <span>ujung kiri <b>{ujung[0]}</b></span>
            <span>ujung kanan <b>{ujung[1]}</b></span>
          </div>
        )}
        <div className="dm-others">
          {names.map((n, i) => (n === myName ? null : (
            <div key={n} className={`dm-opp ${v.giliran === n ? 'turn' : ''}`}>
              <NameChip name={n} idx={i} />{tim && <span className="tag-mini">tim {timOf(n)! + 1}</span>}
              <span className="dm-backs">
                {v.tangan_semua
                  ? v.tangan_semua[n].map((k: number[], j: number) => <Tile key={j} k={k} vertical size={12} />)
                  : <><Tile back vertical size={10} /> ×{v.jumlah_kartu?.[n] ?? 0}</>}
              </span>
              {(v.lewat_pada?.[n] ?? []).length > 0 && <small className="hint">pernah buntu di {v.lewat_pada[n].join(', ')}</small>}
            </div>
          )))}
        </div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {v.bom > 0 ? 'Kena bom 0-0: ambil kartu!' : sah.length ? 'Pilih kartu yang mau ditempel.' : v.bisa_ambil ? 'Tidak ada yang cocok: ambil kartu.' : 'Tidak ada yang cocok: lewat.'}
        </TurnNote>
        {me != null && !replay && (
          <div className="dm-hand" aria-label="Kartumu">
            {hand.map((k, i) => (
              <Tile key={i} k={k} vertical size={30} hl={pick === i} dim={myTurn && !playable.has(i)}
                onClick={myTurn && playable.has(i) ? () => choose(i) : undefined} title={myTurn && playable.has(i) ? 'Tempel kartu ini' : undefined} />
            ))}
            {!hand.length && <span className="hint">Kartumu habis.</span>}
          </div>
        )}
        {myTurn && pick != null && (
          <div className="row dm-side">
            <span className="hint">Tempel di:</span>
            <button type="button" className="btn primary" onClick={() => { setPick(null); act({ kartu: pick, sisi: 'kiri' }); }}>← kiri ({ujung?.[0]})</button>
            <button type="button" className="btn primary" onClick={() => { setPick(null); act({ kartu: pick, sisi: 'kanan' }); }}>kanan ({ujung?.[1]}) →</button>
          </div>
        )}
        {myTurn && !sah.length && (
          <div className="row">
            {(v.bom > 0 || v.bisa_ambil) ? <button type="button" className="btn primary" onClick={() => act('ambil')}>🂠 Ambil kartu</button>
              : <button type="button" className="btn primary" onClick={() => act('lewat')}>Lewat</button>}
          </div>
        )}
        {(v.riwayat ?? []).length > 0 && (
          <details className="dm-hist">
            <summary>Riwayat ronde</summary>
            <ul className="hist">
              {v.riwayat.slice().reverse().map((r: any) => (
                <li key={r.ronde}><b>Ronde {r.ronde}</b>: {r.pemenang} ({r.cara === 'habis' ? 'habis' : 'buntu'}) · sisa mata {Object.entries(r.sisa).map(([n, x]) => `${n} ${x}`).join(', ')}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
      <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, sub: `${v.jumlah_kartu?.[n] ?? 0} kartu`, tag: tim ? `tim ${timOf(n)! + 1}` : undefined }))
        .sort((a, b) => Number(b.value) - Number(a.value))} />
    </div>
  );
}
