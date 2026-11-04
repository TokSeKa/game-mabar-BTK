import { useMemo, useState } from 'react';
import { NameChip, TurnNote, idxOf, useResetState, type RenderProps } from './common';

type Place = [number, number, 'H' | 'V'] | null;

const CELL_LABEL: Record<string, string> = { '.': 'kosong', K: 'kapalku', x: 'meleset', o: 'kena', '#': 'tenggelam' };

function cellsOf(p: Place, size: number): [number, number][] {
  if (!p) return [];
  const [r, c, o] = p;
  return Array.from({ length: size }, (_, k) => [r + (o === 'V' ? k : 0), c + (o === 'H' ? k : 0)] as [number, number]);
}

function layoutProblems(layout: Place[], fleet: number[], n: number): Set<number> {
  const bad = new Set<number>();
  const used = new Map<string, number>();
  layout.forEach((p, i) => {
    for (const [r, c] of cellsOf(p, fleet[i])) {
      if (r < 0 || c < 0 || r >= n || c >= n) bad.add(i);
      const key = `${r},${c}`;
      if (used.has(key)) {
        bad.add(i);
        bad.add(used.get(key)!);
      }
      used.set(key, i);
    }
  });
  return bad;
}

function randomLayout(fleet: number[], n: number): Place[] {
  for (let attempt = 0; attempt < 200; attempt++) {
    const used = new Set<string>();
    const out: Place[] = [];
    let ok = true;
    for (const size of fleet) {
      let placed = false;
      for (let t = 0; t < 300 && !placed; t++) {
        const o = Math.random() < 0.5 ? 'H' : 'V';
        const r = Math.floor(Math.random() * (n - (o === 'V' ? size - 1 : 0)));
        const c = Math.floor(Math.random() * (n - (o === 'H' ? size - 1 : 0)));
        const cs = cellsOf([r, c, o], size);
        if (cs.every(([a, b]) => !used.has(`${a},${b}`))) {
          cs.forEach(([a, b]) => used.add(`${a},${b}`));
          out.push([r, c, o]);
          placed = true;
        }
      }
      if (!placed) {
        ok = false;
        break;
      }
    }
    if (ok) return out;
  }
  return fleet.map(() => null);
}

export function Grid({ rows, onCell, label, highlight, preview }: {
  rows: string[]; onCell?: (r: number, c: number) => void; label: string;
  highlight?: [number, number] | null; preview?: Map<string, 'ok' | 'bad' | 'sel'>;
}) {
  const n = rows.length;
  return (
    <div className="sea" style={{ ['--n' as string]: n }} role="grid" aria-label={label}>
      {rows.map((row, r) =>
        row.split('').map((ch, c) => {
          const pv = preview?.get(`${r},${c}`);
          const hl = highlight && highlight[0] === r && highlight[1] === c;
          return (
            <button
              key={`${r}-${c}`}
              type="button"
              role="gridcell"
              className={`cell s-${ch === '#' ? 'sunk' : ch === '.' ? 'e' : ch} ${pv ? `pv-${pv}` : ''} ${hl ? 'hl' : ''}`}
              disabled={!onCell}
              onClick={onCell ? () => onCell(r, c) : undefined}
              aria-label={`baris ${r} kolom ${c}: ${CELL_LABEL[ch] ?? ch}`}
            />
          );
        }),
      )}
    </div>
  );
}

export function RKapal({ view, names, me, canAct, acted, act, replay, events }: RenderProps) {
  const v = view;
  const n: number = v.ukuran;
  const fleet: number[] = v.armada;
  const lastShot = (events ?? []).find((e) => e.jenis === 'tembak');
  const [layout, setLayout] = useResetState<Place[]>(fleet.map(() => null), `${v.fase}-${me}`);
  const [sel, setSel] = useState(0);
  const [orient, setOrient] = useState<'H' | 'V'>('H');
  const bad = useMemo(() => layoutProblems(layout, fleet, n), [layout, fleet, n]);
  const myName = me != null ? names[me] : null;
  const placing = v.fase === 'susun' && canAct;

  const placePreview = useMemo(() => {
    const m = new Map<string, 'ok' | 'bad' | 'sel'>();
    layout.forEach((p, i) => cellsOf(p, fleet[i]).forEach(([r, c]) => m.set(`${r},${c}`, bad.has(i) ? 'bad' : i === sel ? 'sel' : 'ok')));
    return m;
  }, [layout, fleet, bad, sel]);

  const emptyBoard = useMemo(() => Array.from({ length: n }, () => '.'.repeat(n)), [n]);

  const onPlace = (r: number, c: number) => {
    const next = layout.slice();
    next[sel] = [r, c, orient];
    setLayout(next);
    const free = next.findIndex((p) => p == null);
    if (free >= 0) setSel(free);
  };

  const status = v.pemenang ? `${v.pemenang} menang!` : v.fase === 'susun' ? 'Fase menyusun armada' : `Giliran menembak: ${v.giliran}`;

  return (
    <div className="panel kapal">
      <div className="row"><b>{status}</b><span className="spacer" />
        <span className="hint">Armada: {fleet.join(', ')}</span></div>
      <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
        {placing ? 'Pilih kapal, atur arah, lalu klik papanmu.' : 'Klik petak di papan lawan untuk menembak.'}
      </TurnNote>
      {placing && (
        <div className="act-box">
          <div className="row">
            {fleet.map((size, i) => (
              <button key={i} type="button" className={`btn small ${sel === i ? 'primary' : ''} ${bad.has(i) ? 'danger' : ''}`} onClick={() => setSel(i)}>
                {'■'.repeat(size)} {layout[i] ? '✓' : ''}
              </button>
            ))}
          </div>
          <div className="row">
            <button type="button" className="btn small" onClick={() => setOrient(orient === 'H' ? 'V' : 'H')}>Arah: {orient === 'H' ? 'mendatar →' : 'menurun ↓'}</button>
            <button type="button" className="btn small" onClick={() => setLayout(randomLayout(fleet, n))}>Acak</button>
            <button type="button" className="btn small" onClick={() => setLayout(fleet.map(() => null))}>Kosongkan</button>
            <span className="spacer" />
            <button type="button" className="btn primary" disabled={layout.some((p) => !p) || bad.size > 0} onClick={() => act(layout)}>Siap!</button>
          </div>
        </div>
      )}
      {myName && v.papan_saya ? (
        <div className="seas">
          <div>
            <h3 className="sub-h">Papanku</h3>
            <Grid rows={placing ? emptyBoard : v.papan_saya} label="Papanku" onCell={placing ? onPlace : undefined} preview={placing ? placePreview : undefined}
              highlight={lastShot && lastShot.penembak !== myName ? [lastShot.baris, lastShot.kolom] : null} />
          </div>
          <div>
            <h3 className="sub-h">Papan {v.lawan} <span className="hint">(sisa kapal: {(v.kapal_lawan_sisa ?? []).join(', ') || '–'})</span></h3>
            <Grid rows={v.papan_tembak} label={`Papan ${v.lawan}`}
              onCell={canAct && v.fase === 'tembak' ? (r, c) => v.papan_tembak[r][c] === '.' && act([r, c]) : undefined}
              highlight={lastShot && lastShot.penembak === myName ? [lastShot.baris, lastShot.kolom] : null} />
          </div>
        </div>
      ) : (
        <div className="seas">
          {names.map((nm) => {
            const target = names.find((x) => x !== nm)!;
            return (
              <div key={nm}>
                <h3 className="sub-h">Tembakan {nm} → {target} <span className="hint">(sisa: {(v.sisa?.[target] ?? []).join(', ') || '–'})</span></h3>
                <Grid rows={v.tembakan?.[nm] ?? emptyBoard} label={`Tembakan ${nm}`}
                  highlight={lastShot && lastShot.penembak === nm ? [lastShot.baris, lastShot.kolom] : null} />
              </div>
            );
          })}
        </div>
      )}
      {v.fase === 'susun' && (
        <p className="hint">Sudah siap: {Object.entries(v.sudah_susun ?? {}).filter(([, ok]) => ok).map(([nm]) => nm).join(', ') || 'belum ada'}</p>
      )}
      {(v.riwayat?.length ?? 0) > 0 && (
        <div className="act-log">
          {v.riwayat.slice(-12).reverse().map((r: any, k: number) => (
            <span key={k} className={`chip shot-${r.hasil}`}>
              <NameChip name={r.penembak} idx={idxOf(names, r.penembak)} /> ({r.baris},{r.kolom}) {r.hasil}{r.ukuran ? ` ${r.ukuran}` : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
