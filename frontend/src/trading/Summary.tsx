import { useEffect, useRef } from 'react';
import { ColorType, LineSeries, createChart, type Time, type UTCTimestamp } from 'lightweight-charts';
import type { SessionInfo, SummaryMsg } from './api';
import { C } from './chart';
import { durText, fmtMoney, fmtNum, fmtPct, makeTimeFmt } from './format';

interface Props {
  summary: SummaryMsg;
  session: SessionInfo;
  onClose: () => void;
  onAgain?: () => void;
  myId?: string;
}

function Curve({ points, startTime, blind }: { points: [number, number][]; startTime: number; blind: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || points.length < 2) return;
    const fmt = makeTimeFmt(blind, startTime);
    const ch = createChart(ref.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 10 },
      grid: { vertLines: { visible: false }, horzLines: { color: C.grid } },
      timeScale: { borderColor: C.grid, tickMarkFormatter: (t: Time, type: number) => fmt.tick(t as number, type) },
      rightPriceScale: { borderColor: C.grid },
      handleScroll: false,
      handleScale: false,
      localization: { timeFormatter: (t: Time) => fmt.full(t as number) },
    });
    const s = ch.addSeries(LineSeries, { color: C.gold, lineWidth: 2, priceLineVisible: false });
    const seen = new Set<number>();
    const data = points.filter(([t]) => (seen.has(t) ? false : (seen.add(t), true))).map(([t, v]) => ({ time: t as UTCTimestamp as Time, value: v }));
    s.setData(data);
    ch.timeScale().fitContent();
    return () => ch.remove();
  }, [points, startTime, blind]);
  return <div className="sum-curve" ref={ref} />;
}

export function Summary({ summary, session, onClose, onAgain, myId }: Props) {
  const st = summary.stats;
  const r = summary.reveal;
  const cur = summary.currency;
  const dec = session.decimals;
  const fmt = makeTimeFmt(session.blind.tanggal, session.start_time);
  const beat = st.return_pct > st.buy_hold_pct;
  const deriv = !!st.produk && st.produk !== 'spot';
  const perpMode = st.produk === 'futures';
  return (
    <div className="sum-overlay" role="dialog" aria-label="Hasil sesi">
      <div className="sum-card">
        <div className="sum-head">
          <div>
            <h2 className={st.return_pct >= 0 ? 'up' : 'down'}>{fmtPct(st.return_pct)}</h2>
            <p>
              Ekuitas akhir {fmtMoney(st.equity, cur)} dari modal {fmtMoney(st.capital, cur)}.{' '}
              {beat ? 'Kamu mengalahkan' : 'Kamu kalah dari'} strategi beli-lalu-tahan ({fmtPct(st.buy_hold_pct)}).
              {summary.rank ? ` Peringkat harianmu: #${summary.rank}.` : ''}
            </p>
          </div>
          <button className="btn" type="button" onClick={onClose}>Tutup</button>
        </div>

        <div className="reveal">
          <span className="lbl">Buka identitas</span>
          <b>{r.symbol} · {r.name}</b>
          <span>{r.market} · {r.mulai} → {r.selesai} ({r.zona})</span>
          {session.blind.harga && (
            <span>Harga asli: {fmtNum(r.harga_awal_asli, 4)} → {fmtNum(r.harga_akhir_asli, 4)} (harga di chart = asli × {fmtNum(r.faktor_harga, 6)})</span>
          )}
        </div>

        {summary.board && (
          <div className="race-final">
            <h3>Hasil balapan</h3>
            <ol>
              {summary.board.map((b, i) => (
                <li key={b.id} className={b.id === myId ? 'me' : ''}>
                  <span className="rk">{i + 1}</span><span className="nm">{b.name}</span>
                  <b className={b.return_pct >= 0 ? 'up' : 'down'}>{fmtPct(b.return_pct)}</b>
                </li>
              ))}
            </ol>
          </div>
        )}

        <div className="sum-grid">
          <div><span>Transaksi selesai</span><b>{st.n_trades}</b></div>
          <div><span>Win rate</span><b>{st.win_rate == null ? '–' : fmtPct(st.win_rate, 0, false)}</b></div>
          <div><span>Profit factor</span><b>{st.profit_factor == null ? '–' : fmtNum(st.profit_factor, 2)}</b></div>
          <div><span>Max drawdown</span><b className="down">{fmtPct(-st.max_dd_pct)}</b></div>
          <div><span>Rata-rata untung</span><b className="up">{fmtPct(st.avg_win_pct)}</b></div>
          <div><span>Rata-rata rugi</span><b className="down">{fmtPct(st.avg_loss_pct)}</b></div>
          <div><span>Fee dibayar</span><b>{fmtMoney(st.fees_paid, cur)}</b></div>
          <div><span>Waktu di pasar</span><b>{fmtPct(st.exposure_pct, 0, false)}</b></div>
        </div>
        {deriv && (
          <div className="sum-grid">
            <div><span>Long / short</span><b>{st.n_long ?? 0} / {st.n_short ?? 0}</b></div>
            <div><span>{perpMode ? 'Funding dibayar' : 'Bunga & pinjam saham'}</span><b className={(perpMode ? st.funding_paid ?? 0 : (st.interest_paid ?? 0) + (st.borrow_paid ?? 0)) > 0 ? 'down' : 'up'}>{fmtMoney(perpMode ? st.funding_paid : (st.interest_paid ?? 0) + (st.borrow_paid ?? 0), cur)}</b></div>
            <div><span>Likuidasi</span><b className={(st.n_liq ?? 0) > 0 ? 'down' : ''}>{st.n_liq ?? 0}×{st.liq_loss ? ` (${fmtMoney(st.liq_loss, cur)})` : ''}</b></div>
            <div><span>Leverage terbesar</span><b>{fmtNum(st.max_lev_used ?? 0, 2)}×</b></div>
          </div>
        )}
        {st.open_qty !== 0 && <p className="hint">Masih ada posisi {st.open_qty < 0 ? 'short' : 'terbuka'} senilai {fmtMoney(Math.abs(st.open_value), cur)}, dihitung dengan harga terakhir.</p>}

        <h3>Kurva ekuitas</h3>
        <Curve points={summary.curve} startTime={session.start_time} blind={session.blind.tanggal} />

        {summary.trades.length > 0 && (
          <>
            <h3>Daftar transaksi</h3>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr>{deriv && <th>Arah</th>}<th>Masuk</th><th>Keluar</th><th>Harga masuk</th><th>Harga keluar</th><th>Durasi</th><th>Hasil</th>{deriv && <th>ROE</th>}</tr></thead>
                <tbody>
                  {summary.trades.map((t, i) => (
                    <tr key={i}>
                      {deriv && <td className={t.side === 'short' ? 'down' : 'up'}>{t.side === 'short' ? 'Short' : 'Long'} {fmtNum(t.lev ?? 1, 0)}×{t.liquidated ? ' 💥' : ''}</td>}
                      <td>{fmt.full(t.entry_time)}</td><td>{fmt.full(t.exit_time)}</td>
                      <td>{fmtNum(t.entry_price, dec)}</td><td>{fmtNum(t.exit_price, dec)}</td>
                      <td>{durText(t.exit_time - t.entry_time)}</td>
                      <td className={t.pnl >= 0 ? 'up' : 'down'}>{fmtPct(t.pnl_pct)} ({fmtMoney(t.pnl, cur)})</td>
                      {deriv && <td className={(t.roe_pct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(t.roe_pct)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <div className="row" style={{ marginTop: 12 }}>
          {onAgain && <button className="btn primary" type="button" onClick={onAgain}>Main lagi</button>}
          <button className="btn" type="button" onClick={onClose}>Lihat chart lagi</button>
        </div>
      </div>
    </div>
  );
}
