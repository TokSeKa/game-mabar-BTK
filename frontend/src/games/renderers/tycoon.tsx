import { useMemo, useState } from 'react';
import { rupiah, seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const CUACA_ICON: Record<string, string> = { cerah: '☀️', panas: '🔥', mendung: '☁️', hujan: '🌧️' };
const PRODUK_ICON: Record<string, string> = { sate: '🍢', es_teh: '🧋', bakso: '🍲', mainan: '🧸' };
const IKLAN_SETENGAH = 30000;

function weight(price: number, ads: number, wajar: number) {
  const appeal = Math.max(0, 2 - price / wajar);
  return appeal * appeal * (1 + ads / (ads + IKLAN_SETENGAH));
}

export function RTycoon({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const cash = myName ? v.uang[myName] ?? 0 : 0;
  const [prod, setProd] = useResetState<string>('sate', v.hari);
  const p = v.produk[prod];
  const [harga, setHarga] = useState<number>(p?.wajar ?? 10000);
  const [iklan, setIklan] = useResetState<number>(0, v.hari);
  const maxQty = p ? Math.max(0, Math.floor((cash - iklan) / p.modal)) : 0;
  const yesterday = v.riwayat?.[v.riwayat.length - 1];

  const estimate = useMemo(() => {
    if (!p) return 0;
    const market = 2 * p.permintaan * (1 + (names.length - 1) * 0.35) * p.pengaruh;
    const mine = weight(harga, iklan, p.wajar);
    let others = 0;
    if (yesterday) {
      for (const [nm, a] of Object.entries(yesterday.jual) as [string, any][]) {
        if (nm !== myName && a && typeof a === 'object' && a.produk === prod) others += weight(a.harga, a.iklan, p.wajar);
      }
    }
    return Math.floor((market * mine) / (1 + mine + others));
  }, [p, harga, iklan, names.length, yesterday, myName, prod]);

  const [qty, setQty] = useResetState<number>(0, `${v.hari}-${prod}`);
  const q = Math.min(qty || Math.min(estimate, maxQty), maxQty);
  const cost = q * (p?.modal ?? 0) + iklan;
  const estProfit = Math.min(q, estimate) * harga - cost;

  const choose = (k: string) => {
    setProd(k);
    setHarga(v.produk[k].wajar);
  };

  return (
    <div className="game-grid">
      <div className="panel tycoon">
        <div className="row">
          <b>Hari {v.hari}/{v.hari_total} · {v.nama_hari}</b>
          <span className="tag-mini">{CUACA_ICON[v.cuaca]} {v.cuaca}</span>
          {v.akhir_pekan && <span className="tag-mini ready">akhir pekan</span>}
          {v.acara && <span className="tag-mini host">🎉 {v.acara}</span>}
          <span className="spacer" />
          {v.ramalan_besok && <span className="hint">ramalan besok: {CUACA_ICON[v.ramalan_besok]} {v.ramalan_besok}</span>}
        </div>
        <div className="prod-row">
          {Object.entries(v.produk).map(([k, d]: [string, any]) => (
            <button key={k} type="button" className={`prod ${prod === k ? 'sel' : ''}`} onClick={() => choose(k)} disabled={!canAct}>
              <span className="pi">{PRODUK_ICON[k] ?? '🛒'}</span>
              <b>{d.nama}</b>
              <span className="hint">modal {rupiah(d.modal)} · wajar {rupiah(d.wajar)}</span>
              <span className={d.pengaruh >= 1.1 ? 'good' : d.pengaruh <= 0.85 ? 'bad' : 'hint'}>permintaan ×{d.pengaruh.toFixed(2)}</span>
            </button>
          ))}
        </div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Uangmu {rupiah(cash)}.</TurnNote>
        {canAct && p && (
          <div className="act-box">
            <NumberPicker label="Harga" value={harga} onChange={setHarga} min={Math.round(p.modal / 2)} max={p.wajar * 2} step={500} />
            <NumberPicker label="Iklan" value={iklan} onChange={setIklan} min={0} max={Math.min(cash, 200000)} step={5000} />
            <NumberPicker label="Jumlah" value={q} onChange={setQty} min={0} max={maxQty} />
            <p className="hint">
              Perkiraan pembeli (kalau pesaing seperti kemarin): <b>{estimate}</b> · biaya {rupiah(cost)} · perkiraan untung{' '}
              <b className={estProfit >= 0 ? 'good' : 'bad'}>{rupiah(estProfit)}</b>
            </p>
            <div className="row">
              <button type="button" className="btn primary" disabled={q <= 0} onClick={() => act({ produk: prod, jumlah: q, harga, iklan })}>Buka lapak {p.nama}</button>
              <button type="button" className="btn" onClick={() => act('tutup')}>Tutup hari ini</button>
            </div>
          </div>
        )}
        {yesterday && (
          <div className="table-wrap">
            <table className="tbl">
              <caption className="hint">Hasil hari {yesterday.hari} ({CUACA_ICON[yesterday.cuaca]} {yesterday.cuaca}{yesterday.acara ? `, ${yesterday.acara}` : ''})</caption>
              <thead><tr><th>Pedagang</th><th>Dagangan</th><th>Harga</th><th>Iklan</th><th>Laku</th><th>Untung</th></tr></thead>
              <tbody>
                {Object.entries(yesterday.jual).map(([nm, a]: [string, any]) => (
                  <tr key={nm}>
                    <td><NameChip name={nm} idx={idxOf(names, nm)} /></td>
                    {a === 'tutup' ? <td colSpan={5} className="hint">tutup</td> : (
                      <>
                        <td>{PRODUK_ICON[a.produk]} {v.produk[a.produk]?.nama}</td>
                        <td>{rupiah(a.harga)}</td>
                        <td>{rupiah(a.iklan)}</td>
                        <td>{a.terjual}/{a.jumlah}</td>
                        <td className={a.untung >= 0 ? 'good' : 'bad'}>{rupiah(a.untung)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {(v.riwayat?.length ?? 0) > 1 && <MoneyChart riwayat={v.riwayat} names={names} />}
      </div>
      <ScoreBoard
        rows={names.map((n, i) => ({ n, i, u: v.uang[n] ?? 0 })).sort((a, b) => b.u - a.u).map((r) => ({ name: r.n, idx: r.i, value: rupiah(r.u) }))}
        me={me}
        title="Uang"
      />
    </div>
  );
}

function MoneyChart({ riwayat, names }: { riwayat: any[]; names: string[] }) {
  const W = 300;
  const H = 120;
  const all = riwayat.flatMap((r) => Object.values(r.uang) as number[]);
  const max = Math.max(1, ...all);
  const x = (k: number) => (k / Math.max(1, riwayat.length - 1)) * (W - 10) + 5;
  const y = (u: number) => H - 5 - (u / max) * (H - 10);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Grafik uang per hari">
        <line className="ax" x1="5" y1={H - 5} x2={W - 5} y2={H - 5} />
        {names.map((n, i) => (
          <polyline key={n} points={riwayat.map((r, k) => `${x(k)},${y(r.uang[n] ?? 0)}`).join(' ')} style={{ stroke: seatColor(i) }} strokeWidth={2} />
        ))}
      </svg>
    </div>
  );
}
