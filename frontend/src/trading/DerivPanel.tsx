import { useEffect, useState } from 'react';
import type { AccountSnap, Order, SessionInfo } from './api';
import { fmtMoney, fmtNum, fmtPct, fmtQty, makeTimeFmt } from './format';

interface Props {
  session: SessionInfo;
  account: AccountSnap | null;
  price: number;
  send: (m: Record<string, any>) => void;
  disabled?: boolean;
}

type Kind = 'limit' | 'market' | 'stop' | 'stop_limit';
const KIND_LABEL: Record<Kind, string> = { limit: 'Limit', market: 'Market', stop: 'Stop', stop_limit: 'Stop-limit' };
const LEV_PRESETS = [1, 2, 3, 5, 10, 20, 25, 50, 75, 100, 125];

export function orderLabel(o: Order): string {
  if (o.label === 'SL' || o.label === 'TP') return o.label;
  if (o.label === 'Tutup') return 'Tutup posisi';
  const sisi = o.side === 'buy' ? 'beli' : 'jual';
  if (o.kind === 'stop') return `Stop ${sisi}`;
  if (o.kind === 'stop_limit') return o.triggered ? `Limit ${sisi} (terpicu)` : `Stop-limit ${sisi}`;
  return `Limit ${sisi}`;
}

/** Panel order ala exchange untuk Futures perpetual dan akun Margin (long & short). */
export function DerivPanel({ session, account: a, price, send, disabled }: Props) {
  const p = session.product!;
  const perp = p.kind === 'perp';
  const [kind, setKind] = useState<Kind>('market');
  const [px, setPx] = useState('');
  const [stopPx, setStopPx] = useState('');
  const [qty, setQty] = useState('');
  const [bracket, setBracket] = useState(false);
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [reduceOnly, setReduceOnly] = useState(false);
  const [postOnly, setPostOnly] = useState(false);
  const [levOpen, setLevOpen] = useState(false);
  const [levDraft, setLevDraft] = useState(a?.lev ?? p.default_lev);
  const [closePx, setClosePx] = useState('');
  const [psl, setPsl] = useState('');
  const [ptp, setPtp] = useState('');
  const [adj, setAdj] = useState('');
  const lot = session.lot > 1 ? session.lot : 1;
  const unit = lot > 1 ? 'lot' : session.satuan;
  const dec = session.decimals;
  const cur = session.currency;
  const qstep = lot > 1 ? 1 : session.qty_step;
  const fmt = makeTimeFmt(session.blind.tanggal, session.start_time);

  useEffect(() => {
    if ((kind === 'limit' || kind === 'stop_limit') && !px) setPx(price.toFixed(dec));
    if ((kind === 'stop' || kind === 'stop_limit') && !stopPx) setStopPx(price.toFixed(dec));
  }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (a?.lev && !levOpen) setLevDraft(a.lev);
  }, [a?.lev, levOpen]);

  const lev = a?.lev ?? p.default_lev;
  const side = a?.side ?? null;
  const shortOk = a?.short_ok ?? p.short_ok ?? p.short;
  const refPrice = kind === 'market' ? price : kind === 'stop' ? Number(stopPx) || price : Number(px) || price;
  const units = Number(qty.replace(',', '.')) || 0;
  const shares = units * lot;
  const notional = shares * refPrice;
  const taker = p.fee_beli;
  const feeRate = perp ? ((kind === 'limit' || kind === 'stop_limit') && postOnly ? p.maker ?? taker : taker) : Math.max(p.fee_beli, p.fee_jual);
  const unitStep = session.qty_step / lot;
  const floorUnits = (v: number) => Math.max(0, Math.floor(v / unitStep + 1e-9) * unitStep);
  const scale = kind === 'market' ? 1 : price / (refPrice || price);
  const maxLongUnits = floorUnits(((a?.max_buy ?? 0) * scale) / lot);
  const maxShortUnits = floorUnits(((a?.max_sell ?? 0) * scale) / lot);
  const posUnits = a ? Math.abs(a.qty) / lot : 0;

  const setPct = (pct: number) => {
    const base = reduceOnly ? posUnits : Math.max(maxLongUnits, shortOk ? maxShortUnits : 0);
    const v = floorUnits(base * pct);
    setQty(v > 0 ? String(+v.toFixed(8)) : '');
  };

  const submit = (s: 'buy' | 'sell') => {
    if (!units) return;
    const msg: Record<string, any> = { type: 'order', side: s, kind, qty: shares };
    if (kind === 'limit' || kind === 'stop_limit') msg.price = Number(px);
    if (kind === 'stop') msg.price = Number(stopPx);
    if (kind === 'stop_limit') msg.stop = Number(stopPx);
    if (reduceOnly) msg.reduce_only = true;
    if (postOnly && kind === 'limit') msg.post_only = true;
    if (bracket && !reduceOnly) {
      if (sl) msg.sl = Number(sl);
      if (tp) msg.tp = Number(tp);
    }
    send(msg);
    setQty('');
  };

  const pctPrice = (base: number, pct: number) => (base * (1 + pct / 100)).toFixed(dec);
  const liq = a?.liq_price;
  const ratio = a?.margin_ratio ?? 0;
  const ratioCls = ratio >= 80 ? 'down' : ratio >= 50 ? 'warn' : 'up';
  const levMax = perp ? Math.max(1, Math.min(p.max_lev, a?.max_lev ?? p.max_lev)) : p.max_lev;
  const presets = LEV_PRESETS.filter((x) => x <= p.max_lev);
  const shortLabel = shortOk ? (perp ? 'Short' : 'Jual / Short') : 'Jual';
  const longLabel = perp ? 'Long' : 'Beli';
  const costPaid = (a?.funding_paid ?? 0) + (a?.interest_paid ?? 0) + (a?.borrow_paid ?? 0);

  return (
    <div className="trade-panel deriv">
      <div className="dp-head">
        <span className="badge">{p.nama}</span>
        <div className="dp-ctl">
          {perp && (
            <div className="seg2 mini" role="group" aria-label="Mode margin">
              {(['cross', 'isolated'] as const).map((m) => (
                <button key={m} type="button" className={a?.mode === m ? 'on neutral' : ''} disabled={disabled || a?.mode === m}
                  title={m === 'cross' ? 'Seluruh saldo jadi jaminan posisi' : 'Hanya margin posisi yang bisa hilang'}
                  onClick={() => send({ type: 'margin_mode', mode: m })}>{m === 'cross' ? 'Cross' : 'Isolated'}</button>
              ))}
            </div>
          )}
          <button type="button" className="btn small lev-btn" onClick={() => setLevOpen((v) => !v)} aria-expanded={levOpen}
            title={perp ? 'Leverage' : 'Daya beli (Reg T / BEI: maks 2×)'}>{fmtNum(lev, 0)}×</button>
        </div>
      </div>

      {levOpen && (
        <div className="lev-box">
          <div className="lev-row">
            <input type="range" min={1} max={p.max_lev} step={1} value={levDraft} aria-label="Leverage"
              onChange={(e) => setLevDraft(Number(e.target.value))} />
            <b>{levDraft}×</b>
          </div>
          <div className="pct-row">
            {presets.map((x) => <button key={x} type="button" className="btn small" onClick={() => setLevDraft(x)}>{x}×</button>)}
          </div>
          {perp && a?.notional ? (
            <p className="hint">Posisimu sekarang ({fmtMoney(a.notional, cur)}) boleh sampai {fmtNum(levMax, 0)}×. Makin besar posisi, makin kecil leverage maksimal.</p>
          ) : (
            <p className="hint">{perp ? `Maks ${p.max_lev}× untuk posisi kecil; batasnya turun untuk posisi besar (lihat tabel tier).` : 'Initial margin 50%: daya beli paling besar 2× ekuitas.'}</p>
          )}
          <div className="row">
            <button type="button" className="btn primary small" disabled={disabled} onClick={() => { send({ type: 'leverage', lev: levDraft }); setLevOpen(false); }}>Terapkan</button>
            <button type="button" className="btn small" onClick={() => setLevOpen(false)}>Batal</button>
          </div>
        </div>
      )}

      <div className="tp-stats">
        <div><span>Ekuitas</span><b>{fmtMoney(a?.equity, cur)}</b><em className={(a?.return_pct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(a?.return_pct)}</em></div>
        <div><span>Tersedia</span><b>{fmtMoney(a?.free_cash, cur)}</b>{a && a.reserved_cash > 0 && <em>di order {fmtMoney(a.reserved_cash, cur)}</em>}</div>
        <div>
          <span>{perp ? 'Margin ratio' : 'Kas'}</span>
          {perp ? <b className={side ? ratioCls : ''}>{side ? fmtPct(ratio, 1, false) : '–'}</b> : <b className={(a?.cash ?? 0) < 0 ? 'down' : ''}>{fmtMoney(a?.cash, cur)}</b>}
          <em>{perp ? '100% = likuidasi' : (a?.cash ?? 0) < 0 ? 'dana pinjaman broker' : 'tidak meminjam'}</em>
        </div>
        <div>
          <span>Biaya</span><b>{fmtMoney((a?.fees_paid ?? 0) + costPaid, cur)}</b>
          <em>{perp ? `funding ${fmtMoney(a?.funding_paid ?? 0, cur)}` : `bunga ${fmtMoney((a?.interest_paid ?? 0) + (a?.borrow_paid ?? 0), cur)}`}</em>
        </div>
      </div>

      {side && a && (
        <div className={`pos-card ${side}`}>
          <div className="pos-top">
            <b className={side === 'long' ? 'up' : 'down'}>{side === 'long' ? 'LONG' : 'SHORT'} {fmtNum(lev, 0)}×</b>
            <span>{fmtQty(posUnits, qstep)} {unit}{perp ? ` · ${a.mode === 'isolated' ? 'Isolated' : 'Cross'}` : ''}</span>
            <span className={(a.unrealized ?? 0) >= 0 ? 'up' : 'down'}>{fmtMoney(a.unrealized, cur)}{a.roe_pct != null ? ` (${fmtPct(a.roe_pct)})` : ''}</span>
          </div>
          <dl className="pos-grid">
            <dt>Harga masuk</dt><dd>{fmtNum(a.entry, dec)}</dd>
            <dt>Harga sekarang</dt><dd>{fmtNum(price, dec)}</dd>
            <dt>{perp ? 'Harga likuidasi' : 'Likuidasi paksa'}</dt><dd className="down">{liq ? fmtNum(liq, dec) : '–'}</dd>
            {!perp && <><dt>Margin call</dt><dd className="warn">{a.call_price ? fmtNum(a.call_price, dec) : '–'}</dd></>}
            <dt>Nilai posisi</dt><dd>{fmtMoney(a.notional, cur)}</dd>
            <dt>Margin</dt><dd>{fmtMoney(a.margin, cur)}</dd>
            <dt>Maintenance</dt><dd>{fmtMoney(a.maint, cur)}</dd>
            {perp && a.next_funding && (
              <><dt>Funding berikut</dt><dd className={a.next_funding.rate * (side === 'long' ? 1 : -1) > 0 ? 'down' : 'up'}>{fmtPct(a.next_funding.rate * 100, 4)} · {fmt.full(a.next_funding.time)}</dd></>
            )}
          </dl>
          {a.margin_call && <p className="pos-warn">Margin call: jaminan di bawah batas. Kurangi posisi atau bersiap ditutup paksa.</p>}
          <div className="row">
            <button type="button" className="btn small" disabled={disabled} onClick={() => send({ type: 'close' })}>Tutup market</button>
            <input className="input mini-in" inputMode="decimal" placeholder="harga" value={closePx} onChange={(e) => setClosePx(e.target.value)} aria-label="Harga limit untuk menutup" />
            <button type="button" className="btn small" disabled={disabled || !closePx} onClick={() => { send({ type: 'close', kind: 'limit', price: Number(closePx) }); setClosePx(''); }}>Tutup limit</button>
          </div>
          <details className="protect">
            <summary>TP/SL untuk posisi ini</summary>
            <div className="fields">
              <label className="field" htmlFor="dp-psl">Stop loss<input id="dp-psl" inputMode="decimal" value={psl} placeholder={pctPrice(price, side === 'long' ? -3 : 3)} onChange={(e) => setPsl(e.target.value)} /></label>
              <label className="field" htmlFor="dp-ptp">Take profit<input id="dp-ptp" inputMode="decimal" value={ptp} placeholder={pctPrice(price, side === 'long' ? 6 : -6)} onChange={(e) => setPtp(e.target.value)} /></label>
            </div>
            <button className="btn small" type="button" disabled={disabled || (!psl && !ptp)}
              onClick={() => { send({ type: 'protect', sl: psl ? Number(psl) : null, tp: ptp ? Number(ptp) : null }); setPsl(''); setPtp(''); }}>Pasang (seluruh posisi)</button>
          </details>
          {perp && a.mode === 'isolated' && (
            <div className="row">
              <input className="input mini-in" inputMode="decimal" placeholder={`margin (${cur})`} value={adj} onChange={(e) => setAdj(e.target.value)} aria-label="Jumlah margin" />
              <button type="button" className="btn small" disabled={disabled || !adj} onClick={() => { send({ type: 'margin_adjust', amount: Number(adj) }); setAdj(''); }}>+ Margin</button>
              <button type="button" className="btn small" disabled={disabled || !adj} onClick={() => { send({ type: 'margin_adjust', amount: -Number(adj) }); setAdj(''); }}>− Margin</button>
            </div>
          )}
        </div>
      )}

      <div className="seg4" role="group" aria-label="Jenis order">
        {(['limit', 'market', 'stop', 'stop_limit'] as Kind[]).map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}
            title={k === 'limit' ? 'Menunggu di harga tertentu (maker)' : k === 'market' ? 'Langsung di harga sekarang (taker)' : k === 'stop' ? 'Jadi order market saat harga picu tersentuh' : 'Jadi order limit saat harga picu tersentuh'}>
            {KIND_LABEL[k]}
          </button>
        ))}
      </div>

      {(kind === 'stop' || kind === 'stop_limit') && (
        <label className="field" htmlFor="dp-stop">
          Harga picu
          <div className="inrow">
            <input id="dp-stop" inputMode="decimal" value={stopPx} onChange={(e) => setStopPx(e.target.value)} />
            <button type="button" className="btn small" onClick={() => setStopPx(price.toFixed(dec))}>Sekarang</button>
          </div>
        </label>
      )}
      {(kind === 'limit' || kind === 'stop_limit') && (
        <label className="field" htmlFor="dp-price">
          Harga limit
          <div className="inrow">
            <input id="dp-price" inputMode="decimal" value={px} onChange={(e) => setPx(e.target.value)} />
            <button type="button" className="btn small" onClick={() => setPx(price.toFixed(dec))}>Sekarang</button>
          </div>
        </label>
      )}
      <label className="field" htmlFor="dp-qty">
        Jumlah ({unit}{lot > 1 ? ` · 1 lot = ${lot} lembar` : ''})
        <input id="dp-qty" inputMode="decimal" value={qty} placeholder="0" onChange={(e) => setQty(e.target.value)} />
      </label>
      <div className="pct-row">
        {[0.1, 0.25, 0.5, 0.75, 1].map((x) => (
          <button key={x} type="button" className="btn small" onClick={() => setPct(x)}>{x * 100}%</button>
        ))}
      </div>
      <div className="tp-est">
        <span>Maks long {fmtQty(maxLongUnits, Math.max(qstep, 1e-4))}{shortOk ? ` · short ${fmtQty(maxShortUnits, Math.max(qstep, 1e-4))}` : ''}</span>
        <span>Nilai ≈ {fmtMoney(notional, cur)}</span>
        <span>Margin ≈ {fmtMoney(notional / lev, cur)}</span>
        <span>Fee ≈ {fmtMoney(notional * feeRate, cur)}{perp ? ` (${kind === 'limit' || kind === 'stop_limit' ? 'maker/taker' : 'taker'})` : ''}</span>
      </div>

      <div className="dp-flags">
        <label className="toggle" htmlFor="dp-ro"><input id="dp-ro" type="checkbox" checked={reduceOnly} onChange={(e) => setReduceOnly(e.target.checked)} /> Reduce-only</label>
        {kind === 'limit' && perp && <label className="toggle" htmlFor="dp-po"><input id="dp-po" type="checkbox" checked={postOnly} onChange={(e) => setPostOnly(e.target.checked)} /> Post-only</label>}
        {!reduceOnly && <label className="toggle" htmlFor="dp-br"><input id="dp-br" type="checkbox" checked={bracket} onChange={(e) => setBracket(e.target.checked)} /> TP/SL</label>}
      </div>
      {bracket && !reduceOnly && (
        <div className="fields">
          <label className="field" htmlFor="dp-tp">Take profit<input id="dp-tp" inputMode="decimal" value={tp} placeholder="long: di atas · short: di bawah" onChange={(e) => setTp(e.target.value)} /></label>
          <label className="field" htmlFor="dp-sl">Stop loss<input id="dp-sl" inputMode="decimal" value={sl} placeholder="long: di bawah · short: di atas" onChange={(e) => setSl(e.target.value)} /></label>
        </div>
      )}

      <div className="dp-buttons">
        <button className="btn big good" type="button" disabled={disabled || !units} onClick={() => submit('buy')}>{longLabel}</button>
        <button className="btn big danger-fill" type="button" disabled={disabled || !units || (!shortOk && !side && !reduceOnly)} onClick={() => submit('sell')}>{shortLabel}</button>
      </div>
      {!shortOk && <p className="hint">Short tidak tersedia untuk aset ini{p.short_list ? ` (BEI: hanya ${p.short_list.join(', ')})` : ''}. Tombol jual hanya menutup posisi long.</p>}
      {shortOk && p.uptick && <p className="hint">Aturan uptick BEI: buka short dengan order Limit di harga ≥ harga terakhir.</p>}

      <div className="orders">
        <h3>Order aktif ({a?.orders.length ?? 0})</h3>
        {!a?.orders.length && <p className="hint">Belum ada order yang menunggu.</p>}
        {a?.orders.map((o) => (
          <div key={o.id} className={`order-row ${o.side}`}>
            <span className="ol">{orderLabel(o)}{o.reduce_only && o.label !== 'SL' && o.label !== 'TP' ? ' · RO' : ''}{o.post_only ? ' · PO' : ''}</span>
            <span className="op">{fmtNum(o.price, dec)}</span>
            <span className="oq">{fmtQty(o.qty / lot, qstep)} {unit}</span>
            {(o.kind === 'stop_limit' && !o.triggered) || o.sl || o.tp ? (
              <span className="ob">{o.kind === 'stop_limit' && !o.triggered && o.stop ? `picu ${fmtNum(o.stop, dec)} ` : ''}{o.sl ? `SL ${fmtNum(o.sl, dec)} ` : ''}{o.tp ? `TP ${fmtNum(o.tp, dec)}` : ''}</span>
            ) : null}
            <button className="btn small" type="button" disabled={disabled} onClick={() => send({ type: 'cancel', id: o.id })} aria-label="Batalkan order">✕</button>
          </div>
        ))}
      </div>

      <details className="rules">
        <summary>Aturan & biaya {p.nama}</summary>
        <ul>{p.catatan.map((c, i) => <li key={i}>{c}</li>)}</ul>
        <p className="hint">
          {perp
            ? `Fee: maker ${fmtNum((p.maker ?? 0) * 100, 3)}% · taker ${fmtNum(p.fee_beli * 100, 3)}%. Funding default ${fmtNum(p.funding * 100, 4)}% per ${p.funding_hours} jam.`
            : `Fee beli ${fmtNum(p.fee_beli * 100, 3)}% · jual ${fmtNum(p.fee_jual * 100, 3)}%. Bunga ${fmtNum(p.interest_apr * 100, 2)}%/thn · pinjam saham ${fmtNum(p.borrow_apr * 100, 2)}%/thn.`}
          {' '}Slippage {fmtNum(session.fees.slippage * 100, 2)}% untuk market & stop.
        </p>
        {perp && p.tiers && (
          <table className="tier-tbl">
            <thead><tr><th>Nilai posisi s/d</th><th>Leverage maks</th><th>MMR</th></tr></thead>
            <tbody>
              {p.tiers.slice(0, 6).map((t, i) => (
                <tr key={i}><td>{t.cap == null ? 'lebih' : fmtMoney(t.cap, cur)}</td><td>{t.max_lev}×</td><td>{fmtNum(t.mmr * 100, 2)}%</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </div>
  );
}
