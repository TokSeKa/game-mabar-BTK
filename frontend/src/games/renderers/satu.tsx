import { useState } from 'react';
import { NameChip, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const WARNA = ['merah', 'kuning', 'hijau', 'biru'];
const IKON: Record<string, string> = { merah: '🟥', kuning: '🟨', hijau: '🟩', biru: '🟦', liar: '🌈' };
const URUT_JENIS: Record<string, number> = { angka: 0, lewati: 1, balik: 2, tambah2: 3, kustom: 4, ganti: 5, tambah4: 6 };

function Kartu({ c, kustom, onClick, playable, fresh, big, disabled }: {
  c: any; kustom: any[]; onClick?: () => void; playable?: boolean; fresh?: boolean; big?: boolean; disabled?: boolean;
}) {
  const nama = c.jenis === 'kustom' ? kustom[c.kustom]?.nama : null;
  const cls = `satu-card w-${c.warna} ${playable ? 'ok' : ''} ${fresh ? 'fresh' : ''} ${big ? 'big' : ''} ${onClick ? 'btnlike' : ''}`;
  const body = (
    <>
      <span className="sc-corner">{c.teks}</span>
      <span className="sc-mid">{c.teks}</span>
      {nama && <span className="sc-name">{nama}</span>}
    </>
  );
  if (!onClick) return <span className={cls} title={nama ?? undefined}>{body}</span>;
  return <button type="button" className={cls} disabled={disabled} onClick={onClick} title={nama ?? undefined}>{body}</button>;
}

export function RSatu({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const kustom: any[] = v.kustom ?? [];
  const hand: any[] = v.tangan ?? [];
  const playable = new Set<number>(v.bisa_main ?? []);
  const myName = me != null ? names[me] : null;
  const turnKey = `${v.ronde}-${v.giliran}-${hand.length}-${v.fase}`;
  const [pick, setPick] = useResetState<{ idx: number; warna?: string; target?: string } | null>(null, turnKey);
  const [satu, setSatu] = useState(false);
  const needSatu = v.aturan?.teriak_satu && hand.length === 2;

  const order = hand.map((c, i) => i).sort((a, b) => {
    const x = hand[a];
    const y = hand[b];
    const wa = x.warna === 'liar' ? 9 : WARNA.indexOf(x.warna);
    const wb = y.warna === 'liar' ? 9 : WARNA.indexOf(y.warna);
    return wa - wb || URUT_JENIS[x.jenis] - URUT_JENIS[y.jenis] || (x.angka ?? 0) - (y.angka ?? 0);
  });

  const needsTarget = (c: any) => (c.jenis === 'kustom' && kustom[c.kustom]?.target) || (c.jenis === 'angka' && c.angka === 7 && v.aturan?.aturan_70);
  const send = (idx: number, warna?: string, target?: string) => {
    act({ main: idx, warna: warna ?? null, satu: needSatu && satu, target: target ?? null });
    setPick(null);
    setSatu(false);
  };
  const choose = (idx: number) => {
    const c = hand[idx];
    const wantColor = c.warna === 'liar';
    const wantTarget = needsTarget(c);
    if (!wantColor && !wantTarget) return send(idx);
    setPick({ idx });
  };
  const pc = pick ? hand[pick.idx] : null;
  const pickColor = (w: string) => {
    if (!pick || !pc) return;
    if (!needsTarget(pc)) send(pick.idx, w);
    else setPick({ ...pick, warna: w });
  };
  const pickTarget = (t: string) => {
    if (pick) send(pick.idx, pick.warna, t);
  };

  const others = names.filter((n) => n !== myName);
  const turnName = v.giliran;
  const counts = v.jumlah_kartu ?? {};
  return (
    <div className="game-grid satu">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">arah {v.arah === 1 ? '⟳' : '⟲'} · dek {v.sisa_dek}</span></div>
        <div className="satu-players">
          {names.map((n) => (
            <span key={n} className={`satu-seat ${n === turnName ? 'turn' : ''} ${n === myName ? 'me' : ''}`}>
              <NameChip name={n} idx={idxOf(names, n)} />
              <span className="satu-count">🂠 {counts[n] ?? '?'}</span>
              {(v.teriak ?? []).includes(n) && <span className="satu-call">SATU!</span>}
            </span>
          ))}
        </div>
        <div className="satu-table">
          <div className="satu-deck" title="Dek">
            <span className="satu-card back">🂠</span>
            <small className="hint">{v.sisa_dek}</small>
          </div>
          <div className="satu-top">
            <Kartu c={v.atas} kustom={kustom} big />
            <span className={`satu-color w-${v.warna}`}>{IKON[v.warna]} {v.warna}</span>
            {v.tumpukan_tarik > 0 && <span className="satu-stack">+{v.tumpukan_tarik}</span>}
          </div>
          <ul className="satu-last">
            {(v.terakhir ?? []).slice().reverse().slice(0, 4).map((x: any, k: number) => (
              <li key={k}><NameChip name={x.pemain} idx={idxOf(names, x.pemain)} /> {x.kartu.teks}{x.kartu.warna === 'liar' ? ` → ${IKON[x.warna]}` : ''}</li>
            ))}
          </ul>
        </div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {v.tumpukan_tarik > 0 ? `Ada +${v.tumpukan_tarik} untukmu: balas dengan +2/+4 atau ambil semuanya.` : v.fase === 'setelah_ambil' ? 'Kartu baru bisa dimainkan, atau lewat.' : 'Mainkan kartu yang cocok atau ambil.'}
        </TurnNote>
        {!canAct && !replay && turnName && turnName !== myName && <p className="hint">Giliran <NameChip name={turnName} idx={idxOf(names, turnName)} />…</p>}
        {me != null && hand.length > 0 && (
          <div className="satu-hand">
            {order.map((i) => (
              <Kartu key={hand[i].id} c={hand[i]} kustom={kustom} playable={canAct && playable.has(i)} fresh={v.kartu_baru === i}
                disabled={!canAct || !playable.has(i)} onClick={() => choose(i)} />
            ))}
          </div>
        )}
        {canAct && (
          <div className="row satu-actions">
            {needSatu && (
              <button type="button" className={`btn ${satu ? 'primary' : 'satu-pulse'}`} onClick={() => setSatu(!satu)}>
                📢 SATU!{satu ? ' ✓' : ''}
              </button>
            )}
            {v.fase === 'setelah_ambil'
              ? <button type="button" className="btn" onClick={() => act('lewat')}>⏭️ Lewat</button>
              : <button type="button" className="btn" onClick={() => act('ambil')}>{v.tumpukan_tarik > 0 ? `🂠 Ambil ${v.tumpukan_tarik}` : '🂠 Ambil kartu'}</button>}
            {needSatu && !satu && <span className="hint">Kartumu tinggal 2: tekan SATU! sebelum memainkan kartu (lupa = tarik 2).</span>}
          </div>
        )}
        {canAct && pick && pc && (
          <div className="satu-picker">
            {pc.warna === 'liar' && !pick.warna && (
              <div className="row"><b>Pilih warna:</b>
                {WARNA.map((w) => <button key={w} type="button" className={`btn satu-wbtn w-${w}`} onClick={() => pickColor(w)}>{IKON[w]} {w}</button>)}
              </div>
            )}
            {needsTarget(pc) && (pc.warna !== 'liar' || pick.warna) && (
              <div className="row"><b>{pc.jenis === 'angka' ? 'Tukar kartu dengan:' : 'Pilih target:'}</b>
                {others.map((n) => <button key={n} type="button" className="btn small" onClick={() => pickTarget(n)}>{n} ({counts[n] ?? '?'})</button>)}
              </div>
            )}
            <button type="button" className="btn small" onClick={() => setPick(null)}>Batal</button>
          </div>
        )}
        {kustom.length > 0 && (
          <details className="satu-legend" open={!replay && me != null}>
            <summary>Kartu power kustom ({kustom.length})</summary>
            <ul>
              {kustom.map((k, i) => (
                <li key={i}><span className={`mini-kartu w-${k.warna}`}>{k.simbol}</span> <b>{k.nama}</b>{' '}
                  <small className="hint">{k.warna === 'liar' ? 'liar' : k.warna === 'semua' ? 'semua warna' : k.warna}{k.target ? ' · bertarget' : ''} · {k.nilai} poin</small>
                  {k.ket && <> — {k.ket}</>}</li>
              ))}
            </ul>
          </details>
        )}
        {v.semua_tangan && (
          <div className="satu-all">
            {Object.entries(v.semua_tangan).map(([n, cards]: [string, any]) => (
              <div key={n} className="row"><NameChip name={n} idx={idxOf(names, n)} />
                <span className="satu-mini-hand">{cards.map((c: any) => <Kartu key={c.id} c={c} kustom={kustom} />)}</span></div>
            ))}
          </div>
        )}
        {(v.riwayat ?? []).length > 0 && (
          <ul className="hist">
            {(v.riwayat ?? []).slice().reverse().map((r: any) => (
              <li key={r.ronde}><b>Ronde {r.ronde}</b> 🏆 {r.pemenang} <b className="gold">+{r.poin}</b>{r.batas ? ' (batas giliran)' : ''}
                <span className="hint"> · sisa {Object.entries(r.sisa).filter(([n]) => n !== r.pemenang).map(([n, x]) => `${n} ${x}`).join(', ')}</span></li>
            ))}
          </ul>
        )}
      </div>
      <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, sub: `${counts[n] ?? '?'} kartu`, tag: n === turnName ? '▶' : undefined }))
        .sort((a, b) => Number(b.value) - Number(a.value))} />
    </div>
  );
}
