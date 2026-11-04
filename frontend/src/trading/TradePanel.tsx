import { useEffect, useState } from 'react';
import type { AccountSnap, SessionInfo } from './api';
import { fmtMoney, fmtNum, fmtPct, fmtQty } from './format';

interface Props {
  session: SessionInfo;
  account: AccountSnap | null;
  price: number;
  send: (m: Record<string, any>) => void;
  disabled?: boolean;
}

type Side = 'buy' | 'sell';
type Kind = 'market' | 'limit' | 'stop';

export function TradePanel({ session, account, price, send, disabled }: Props) {
  const [side, setSide] = useState<Side>('buy');
  const [kind, setKind] = useState<Kind>('market');
  const [qty, setQty] = useState('');
  const [px, setPx] = useState('');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [psl, setPsl] = useState('');
  const [ptp, setPtp] = useState('');
  const lot = session.lot > 1 ? session.lot : 1;
  const unit = lot > 1 ? 'lot' : session.satuan;
  const dec = session.decimals;
  const cur = session.currency;

  useEffect(() => {
    if (kind !== 'market' && !px) setPx(price.toFixed(dec));
  }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  const a = account;
  const refPrice = kind === 'market' ? price : Number(px) || price;
  const qtyUnits = Number(qty.replace(',', '.')) || 0;
  const shares = qtyUnits * lot;
  const notional = shares * refPrice;
  const feeRate = side === 'buy' ? session.fees.beli : session.fees.jual;
  const fee = notional * feeRate;
  const step = session.qty_step; // dalam lembar/unit
  const unitStep = step / lot; // IDX: 1 lot
  const floorUnits = (v: number) => Math.floor(v / unitStep + 1e-9) * unitStep;
  const maxShares = !a ? 0 : side === 'sell' ? a.free_qty
    : kind === 'market' ? a.max_buy
    : a.free_cash / (refPrice * (1 + session.fees.beli) * (kind === 'stop' ? 1 + session.fees.slippage : 1));
  const maxUnits = floorUnits(maxShares / lot);

  const setPct = (pct: number) => {
    const v = floorUnits(maxUnits * pct);
    setQty(v > 0 ? String(+v.toFixed(8)) : '');
  };

  const submit = () => {
    if (!qtyUnits) return;
    const msg: Record<string, any> = { type: 'order', side, kind, qty: shares };
    if (kind !== 'market') msg.price = Number(px);
    if (side === 'buy') {
      if (sl) msg.sl = Number(sl);
      if (tp) msg.tp = Number(tp);
    }
    send(msg);
    setQty('');
  };

  const pctPrice = (base: number, pct: number) => (base * (1 + pct / 100)).toFixed(dec);
  const holding = a && a.qty > 0;
  const pnlPct = holding && a.avg_cost ? (price / a.avg_cost - 1) * 100 : null;

  return (
    <div className="trade-panel">
      <div className="tp-stats">
        <div><span>Ekuitas</span><b>{fmtMoney(a?.equity, cur)}</b><em className={(a?.return_pct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(a?.return_pct)}</em></div>
        <div><span>Saldo bebas</span><b>{fmtMoney(a?.free_cash, cur)}</b>{a && a.reserved_cash > 0 && <em>terkunci {fmtMoney(a.reserved_cash, cur)}</em>}</div>
        <div>
          <span>Posisi</span>
          <b>{a ? `${fmtQty(a.qty / lot, lot > 1 ? 1 : session.qty_step)} ${unit}` : '–'}</b>
          {holding && <em>rata-rata {fmtNum(a.avg_cost, dec)} · <span className={(pnlPct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(pnlPct)}</span></em>}
        </div>
        <div><span>Fee dibayar</span><b>{fmtMoney(a?.fees_paid, cur)}</b><em>max DD {fmtPct(a?.max_dd_pct, 1, false)}</em></div>
      </div>

      <div className="seg2" role="group" aria-label="Sisi">
        <button type="button" className={side === 'buy' ? 'on buy' : ''} onClick={() => setSide('buy')}>Beli</button>
        <button type="button" className={side === 'sell' ? 'on sell' : ''} onClick={() => setSide('sell')}>Jual</button>
      </div>
      <div className="seg3" role="group" aria-label="Jenis order">
        {(['market', 'limit', 'stop'] as Kind[]).map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
            title={k === 'market' ? 'Langsung di harga sekarang' : k === 'limit' ? (side === 'buy' ? 'Beli saat harga turun ke…' : 'Jual saat harga naik ke… (take profit)') : (side === 'buy' ? 'Beli saat harga menembus ke atas… (breakout)' : 'Jual saat harga turun ke… (stop loss)')}>
            {k === 'market' ? 'Market' : k === 'limit' ? 'Limit' : 'Stop'}
          </button>
        ))}
      </div>

      {kind !== 'market' && (
        <label className="field" htmlFor="tp-price">
          Harga {kind === 'limit' ? 'limit' : 'stop'}
          <div className="inrow">
            <input id="tp-price" inputMode="decimal" value={px} onChange={(e) => setPx(e.target.value)} />
            <button type="button" className="btn small" onClick={() => setPx(price.toFixed(dec))}>Sekarang</button>
          </div>
        </label>
      )}
      <label className="field" htmlFor="tp-qty">
        Jumlah ({unit}{lot > 1 ? ` · 1 lot = ${lot} lembar` : ''})
        <input id="tp-qty" inputMode="decimal" value={qty} placeholder="0" onChange={(e) => setQty(e.target.value)} />
      </label>
      <div className="pct-row">
        {[0.25, 0.5, 0.75, 1].map((x) => (
          <button key={x} type="button" className="btn small" onClick={() => setPct(x)}>{x * 100}%</button>
        ))}
      </div>
      {side === 'buy' && (
        <div className="fields">
          <label className="field" htmlFor="tp-sl">
            Stop loss (opsional)
            <input id="tp-sl" inputMode="decimal" value={sl} placeholder={pctPrice(refPrice, -3)} onChange={(e) => setSl(e.target.value)} />
          </label>
          <label className="field" htmlFor="tp-tp">
            Take profit (opsional)
            <input id="tp-tp" inputMode="decimal" value={tp} placeholder={pctPrice(refPrice, 6)} onChange={(e) => setTp(e.target.value)} />
          </label>
          <div className="pct-row" style={{ gridColumn: '1 / -1' }}>
            {[-2, -5].map((x) => <button key={x} type="button" className="btn small" onClick={() => setSl(pctPrice(refPrice, x))}>SL {x}%</button>)}
            {[4, 10].map((x) => <button key={x} type="button" className="btn small" onClick={() => setTp(pctPrice(refPrice, x))}>TP +{x}%</button>)}
          </div>
        </div>
      )}
      <div className="tp-est">
        <span>Nilai ≈ {fmtMoney(notional, cur)}</span>
        <span>Fee ≈ {fmtMoney(fee, cur)} ({fmtNum(feeRate * 100, 2)}%)</span>
      </div>
      <button className={`btn big ${side === 'buy' ? 'good' : 'danger-fill'}`} type="button" disabled={disabled || !qtyUnits} onClick={submit}>
        {side === 'buy' ? 'Beli' : 'Jual'} {kind === 'market' ? 'sekarang' : kind}
      </button>

      {holding && a.free_qty > 0 && (
        <details className="protect">
          <summary>Lindungi posisi (SL/TP untuk aset yang sudah dimiliki)</summary>
          <div className="fields">
            <label className="field" htmlFor="pp-sl">Stop loss<input id="pp-sl" inputMode="decimal" value={psl} placeholder={pctPrice(price, -3)} onChange={(e) => setPsl(e.target.value)} /></label>
            <label className="field" htmlFor="pp-tp">Take profit<input id="pp-tp" inputMode="decimal" value={ptp} placeholder={pctPrice(price, 6)} onChange={(e) => setPtp(e.target.value)} /></label>
          </div>
          <button className="btn" type="button" disabled={disabled || (!psl && !ptp)}
            onClick={() => { send({ type: 'protect', qty: a.free_qty, sl: psl ? Number(psl) : null, tp: ptp ? Number(ptp) : null }); setPsl(''); setPtp(''); }}>
            Pasang untuk {fmtQty(a.free_qty / lot, lot > 1 ? 1 : session.qty_step)} {unit}
          </button>
        </details>
      )}

      <div className="orders">
        <h3>Order aktif ({a?.orders.length ?? 0})</h3>
        {!a?.orders.length && <p className="hint">Belum ada order yang menunggu.</p>}
        {a?.orders.map((o) => (
          <div key={o.id} className={`order-row ${o.side}`}>
            <span className="ol">{o.side === 'buy' ? (o.kind === 'limit' ? 'Limit beli' : 'Stop beli') : o.label || (o.kind === 'limit' ? 'Limit jual' : 'Stop jual')}</span>
            <span className="op">{fmtNum(o.price, dec)}</span>
            <span className="oq">{fmtQty(o.qty / lot, lot > 1 ? 1 : session.qty_step)} {unit}</span>
            {(o.sl || o.tp) && <span className="ob">{o.sl ? `SL ${fmtNum(o.sl, dec)}` : ''} {o.tp ? `TP ${fmtNum(o.tp, dec)}` : ''}</span>}
            <button className="btn small" type="button" disabled={disabled} onClick={() => send({ type: 'cancel', id: o.id })} aria-label="Batalkan order">✕</button>
          </div>
        ))}
      </div>
      <p className="hint fee-note">{session.fees.catatan} Slippage {fmtNum(session.fees.slippage * 100, 2)}% untuk order market & stop.</p>
    </div>
  );
}
