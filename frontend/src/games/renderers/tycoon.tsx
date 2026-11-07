import { useEffect, useMemo, useState } from 'react';
import { rupiah, seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const CUACA_ICON: Record<string, string> = { cerah: '☀️', panas: '🔥', mendung: '☁️', hujan: '🌧️' };
const PRODUK_ICON: Record<string, string> = { sate: '🍢', es_teh: '🧋', bakso: '🍲', mainan: '🧸' };
const IKLAN_SETENGAH = 30000;

function weight(price: number, ads: number, wajar: number) {
  const appeal = Math.max(0, 2 - price / wajar);
  return appeal * appeal * (1 + ads / (ads + IKLAN_SETENGAH));
}

export function RTycoon({ view, names, me, canAct, acted, act, replay, draft }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const cash = myName ? v.uang[myName] ?? 0 : 0;
  // dagangan, harga & iklan terakhir diingat antar hari (biasanya pedagang jualan hal yang sama lagi)
  const [prod, setProdRaw] = useState<string>('sate');
  const p = v.produk[prod];
  const [harga, setHargaRaw] = useState<number>(p?.wajar ?? 10000);
  const [iklan, setIklanRaw] = useState<number>(0);
  const setHarga = (x: number) => {
    setHargaRaw(x);
  };
  const setIklan = (x: number) => {
    setIklanRaw(x);
  };
  const maxQty = p ? Math.max(0, Math.floor((cash - iklan) / p.modal)) : 0;
  const yesterday = v.riwayat?.[v.riwayat.length - 1];

  const estimate = useMemo(() => {
    if (!p) return 0;
    const market = 2 * p.permintaan * (1 + (names.length - 1) * 0.35) * p.pengaruh;
    const mine = weight(harga, iklan, p.wajar);
    let others = 0;
    if (yesterday) {
      if (v.pesaing_rahasia) {
        // harga pesaing rahasia: anggap tiap penjual lain menjual seharga wajar tanpa iklan (daya tarik 1)
        const mineYesterday = myName && yesterday.jual?.[myName]?.produk === prod ? 1 : 0;
        others = Math.max(0, (yesterday.penjual?.[prod] ?? 0) - mineYesterday);
      } else {
        for (const [nm, a] of Object.entries(yesterday.jual) as [string, any][]) {
          if (nm !== myName && a && typeof a === 'object' && a.produk === prod) others += weight(a.harga, a.iklan, p.wajar);
        }
      }
    }
    return p.dilarang ? 0 : Math.floor((market * mine) / (1 + mine + others));
  }, [p, harga, iklan, names.length, yesterday, myName, prod, v.pesaing_rahasia]);
  const stok = v.stok_saya && v.stok_saya.produk === prod ? v.stok_saya.jumlah : 0;

  const [qty, setQtyRaw] = useResetState<number>(0, `${v.hari}-${prod}`);
  const q = Math.max(0, Math.min(qty || Math.max(0, Math.min(estimate - stok, maxQty)), maxQty));
  const cost = q * (p?.modal ?? 0) + iklan;
  const estProfit = Math.min(q + stok, estimate) * harga - cost;
  const canOpen = (q > 0 || stok > 0) && !p?.dilarang;
  const setQty = (x: number) => {
    setQtyRaw(x);
  };

  const choose = (k: string) => {
    setProdRaw(k);
    setHargaRaw(v.produk[k].wajar);
  };

  // submit otomatis: lapak yang sedang terlihat di layar dikirim kalau waktu habis
  useEffect(() => {
    if (!canAct || !p) return;
    draft?.(canOpen ? { produk: prod, jumlah: q, harga, iklan } : 'tutup');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAct, prod, q, harga, iklan, canOpen, v.hari]);

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
        {v.kejadian && <div className="kejutan-banner">{v.kejadian.teks}</div>}
        {v.stok_saya && <p className="hint">📦 Stok kemarin: {v.stok_saya.jumlah} {v.produk[v.stok_saya.produk]?.nama} (dijual lebih dulu tanpa modal; basi kalau tidak dijual hari ini)</p>}
        <div className="prod-row">
          {Object.entries(v.produk).map(([k, d]: [string, any]) => (
            <button key={k} type="button" className={`prod ${prod === k ? 'sel' : ''} ${d.dilarang ? 'banned' : ''}`} onClick={() => choose(k)} disabled={!canAct || d.dilarang}>
              <span className="pi">{PRODUK_ICON[k] ?? '🛒'}</span>
              <b>{d.nama}{d.dilarang ? ' 🚨' : ''}</b>
              <span className="hint">modal {rupiah(d.modal)}{d.modal_biasa && d.modal !== d.modal_biasa ? ` (biasa ${rupiah(d.modal_biasa)})` : ''} · wajar {rupiah(d.wajar)}</span>
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
              <button type="button" className="btn primary" disabled={!canOpen} onClick={() => act({ produk: prod, jumlah: q, harga, iklan })}>Buka lapak {p.nama}</button>
              <button type="button" className="btn" onClick={() => act('tutup')}>Tutup hari ini</button>
            </div>
            <p className="hint">{canOpen ? `Kalau waktu habis, lapak di atas (${p.nama} ×${q}${stok ? ` + stok ${stok}` : ''}) dibuka otomatis.` : 'Kalau waktu habis, lapakmu tutup hari ini.'}</p>
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
                    {a === 'tutup' ? <td colSpan={5} className="hint">tutup</td> : a?.rahasia ? <td colSpan={5} className="hint">🔒 rahasia</td> : (
                      <>
                        <td>{PRODUK_ICON[a.produk]} {v.produk[a.produk]?.nama}</td>
                        <td>{rupiah(a.harga)}</td>
                        <td>{rupiah(a.iklan)}</td>
                        <td>{a.terjual}/{a.jumlah + (a.stok ?? 0)}{a.disimpan ? ` · simpan ${a.disimpan}` : ''}</td>
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
        {(v.riwayat?.length ?? 0) > 0 && <TycoonHistory riwayat={v.riwayat} names={names} produk={v.produk} me={me} />}
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

interface DaySale {
  produk: string;
  jumlah: number;
  harga: number;
  iklan: number;
  terjual: number;
  untung: number;
  stok?: number;
  disimpan?: number;
}

/** Rekap per pedagang dari seluruh riwayat (dipakai juga di layar hasil). */
export function tycoonRecap(riwayat: any[], names: string[]) {
  return names.map((n, i) => {
    let untung = 0;
    let buka = 0;
    let laku = 0;
    let beli = 0;
    let basi = 0;
    let best: { hari: number; untung: number } | null = null;
    const per: Record<string, number> = {};
    for (const d of riwayat) {
      const a = d.jual?.[n] as DaySale | 'tutup' | { rahasia: true } | undefined;
      if (!a || a === 'tutup' || 'rahasia' in a) continue;
      buka += 1;
      untung += a.untung;
      laku += a.terjual;
      beli += a.jumlah + (a.stok ?? 0);
      basi += a.jumlah + (a.stok ?? 0) - a.terjual - (a.disimpan ?? 0);
      per[a.produk] = (per[a.produk] ?? 0) + a.untung;
      if (!best || a.untung > best.untung) best = { hari: d.hari, untung: a.untung };
    }
    const fav = Object.entries(per).sort((x, y) => y[1] - x[1])[0]?.[0] ?? null;
    const last = riwayat[riwayat.length - 1];
    return { n, i, untung, buka, laku, beli, basi, best, fav, per, uang: last?.uang?.[n] ?? 0 };
  });
}

const pct = (x: number) => `${x >= 1 ? '+' : ''}${Math.round((x - 1) * 100)}%`;

/** Riwayat lengkap: rekap per pedagang + rincian setiap hari (dagangan, harga, iklan, laku, basi, untung). */
export function TycoonHistory({ riwayat, names, produk, me }: { riwayat: any[]; names: string[]; produk: Record<string, any>; me: number | null }) {
  const recap = useMemo(() => tycoonRecap(riwayat, names).sort((a, b) => b.uang - a.uang), [riwayat, names]);
  const days = riwayat.slice().reverse();
  return (
    <div className="tycoon-history">
      <h3 className="sub-h">Rekap pedagang ({riwayat.length} hari)</h3>
      <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>Pedagang</th><th>Uang</th><th>Total untung</th><th>Buka</th><th>Laku/beli</th><th>Basi</th><th>Andalan</th><th>Hari terbaik</th></tr></thead>
          <tbody>
            {recap.map((r) => (
              <tr key={r.n} className={r.i === me ? 'me' : ''}>
                <td><NameChip name={r.n} idx={r.i} /></td>
                <td className="num">{rupiah(r.uang)}</td>
                <td className={`num ${r.untung >= 0 ? 'good' : 'bad'}`}>{rupiah(r.untung)}</td>
                <td className="num">{r.buka}/{riwayat.length}</td>
                <td className="num">{r.laku}/{r.beli}</td>
                <td className="num">{r.basi}</td>
                <td>{r.fav ? `${PRODUK_ICON[r.fav] ?? ''} ${produk[r.fav]?.nama ?? r.fav}` : '–'}</td>
                <td>{r.best ? <>H{r.best.hari} <span className={r.best.untung >= 0 ? 'good' : 'bad'}>{rupiah(r.best.untung)}</span></> : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="sub-h">Rincian per hari</h3>
      <div className="day-list">
        {days.map((d, k) => {
          const rows = Object.entries(d.jual ?? {}) as [string, DaySale | 'tutup' | { rahasia: true }][];
          return (
            <details key={d.hari} className="day-card" open={k === 0}>
              <summary>
                <b>Hari {d.hari}</b> {d.nama_hari ?? ''} · {CUACA_ICON[d.cuaca]} {d.cuaca}{d.acara ? ` · 🎉 ${d.acara}` : ''}{d.kejadian ? ` · ${d.kejadian.teks}` : ''}
                <span className="hint">
                  {' '}· pembeli: {Object.entries(d.pembeli ?? {}).map(([pk, x]) => `${PRODUK_ICON[pk] ?? ''}${x}${d.penjual?.[pk] ? ` (${d.penjual[pk]} penjual)` : ''}`).join(' ') || 'tidak ada yang buka'}
                </span>
              </summary>
              <div className="table-wrap">
                <table className="tbl">
                  <thead><tr><th>Pedagang</th><th>Dagangan</th><th>Harga</th><th>Iklan</th><th>Beli</th><th>Laku</th><th>Basi</th><th>Untung</th><th>Uang akhir</th></tr></thead>
                  <tbody>
                    {rows.map(([nm, a]) => (
                      <tr key={nm} className={idxOf(names, nm) === me ? 'me' : ''}>
                        <td><NameChip name={nm} idx={idxOf(names, nm)} /></td>
                        {a === 'tutup' ? <td colSpan={7} className="hint">tutup</td> : 'rahasia' in a ? <td colSpan={7} className="hint">🔒 rahasia</td> : (
                          <>
                            <td>{PRODUK_ICON[a.produk]} {produk[a.produk]?.nama ?? a.produk}</td>
                            <td className="num">{rupiah(a.harga)}</td>
                            <td className="num">{rupiah(a.iklan)}</td>
                            <td className="num">{a.jumlah}{a.stok ? ` +${a.stok} stok` : ''}</td>
                            <td className="num">{a.terjual}</td>
                            <td className="num">{a.jumlah + (a.stok ?? 0) - a.terjual - (a.disimpan ?? 0)}{a.disimpan ? ` (simpan ${a.disimpan})` : ''}</td>
                            <td className={`num ${a.untung >= 0 ? 'good' : 'bad'}`}>{rupiah(a.untung)}</td>
                          </>
                        )}
                        <td className="num">{rupiah(d.uang?.[nm] ?? 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {d.gejolak && (
                <p className="hint">
                  Gejolak permintaan malam itu: {Object.entries(d.gejolak).map(([pk, x]) => `${produk[pk]?.nama ?? pk} ${pct(Number(x))}`).join(' · ')}
                </p>
              )}
            </details>
          );
        })}
      </div>
    </div>
  );
}
