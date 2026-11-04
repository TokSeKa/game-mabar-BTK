import { useEffect, useRef, useState } from 'react';
import type { AccountSnap, Candle, Fill, SessionInfo } from './api';
import { TradingChart } from './chart';
import { DrawingLayer, type DrawingStore, type Tool } from './drawings';
import { fmtNum, fmtPct, makeTimeFmt } from './format';
import type { IndicatorConfig } from './indicators';

const TF_SEC: Record<string, number> = {
  '1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400, '6h': 21600,
  '12h': 43200, '1d': 86400, '1w': 604800, '1M': 2592000,
};
export const tfSec = (tf: string) => TF_SEC[tf] ?? 60;
const INTRADAY = new Set(['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h']);

export interface PanelHandle {
  id: number;
  tf: string;
  onCandles: (candles: Candle[], before: number | null, more: boolean) => void;
  onUpdates: (updates: Candle[]) => void;
}

interface Props {
  id: number;
  session: SessionInfo;
  tf: string;
  onTf: (tf: string) => void;
  indicators: IndicatorConfig;
  store: DrawingStore;
  tool: Tool;
  onToolDone: () => void;
  fills: Fill[];
  account: AccountSnap | null;
  register: (h: PanelHandle) => () => void;
  request: (tf: string, before?: number) => void;
  compact?: boolean;
  removeRef?: (fn: () => boolean) => void;
}

export function ChartPanel(p: Props) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<TradingChart | null>(null);
  const layerRef = useRef<DrawingLayer | null>(null);
  const moreRef = useRef(true);
  const loadingRef = useRef(false);
  const [legend, setLegend] = useState<{ c: Candle | null; prev: Candle | null }>({ c: null, prev: null });
  const [loading, setLoading] = useState(true);
  const { session, tf } = p;
  const fmt = makeTimeFmt(session.blind.tanggal, session.start_time);

  // buat chart baru setiap kali timeframe berganti
  useEffect(() => {
    if (!host.current) return;
    const chart = new TradingChart(host.current, {
      decimals: session.decimals,
      blind: session.blind.tanggal,
      startTime: session.start_time,
      intraday: INTRADAY.has(tf),
      onNeedMore: () => {
        if (!moreRef.current || loadingRef.current || !chart.data.length) return;
        loadingRef.current = true;
        p.request(tf, chart.data[0][0]);
      },
      onCrosshair: (c, prev) => setLegend({ c, prev }),
    }, p.indicators);
    chartRef.current = chart;
    const layer = new DrawingLayer(host.current, chart, p.store, { decimals: session.decimals, tfSec: () => tfSec(tf), onToolDone: p.onToolDone });
    layerRef.current = layer;
    p.removeRef?.(() => layer.removeSelected());
    moreRef.current = true;
    setLoading(true);
    const unregister = p.register({
      id: p.id,
      tf,
      onCandles: (candles, before, more) => {
        moreRef.current = more;
        loadingRef.current = false;
        if (before == null) {
          chart.setData(candles);
          chart.scrollToEnd();
          setLoading(false);
        } else {
          const first = chart.data[0]?.[0] ?? Infinity;
          const older = candles.filter((c) => c[0] < first);
          if (older.length) chart.setData(older.concat(chart.data), older.length);
        }
        chart.setFills(fillsRef.current);
        if (accRef.current) chart.setOrderLines(accRef.current.orders, accRef.current.avg_cost, accRef.current.qty > 0);
        setLegend({ c: chart.data[chart.data.length - 1] ?? null, prev: chart.data[chart.data.length - 2] ?? null });
      },
      onUpdates: (u) => {
        chart.applyUpdates(u);
        setLegend({ c: chart.data[chart.data.length - 1] ?? null, prev: chart.data[chart.data.length - 2] ?? null });
      },
    });
    p.request(tf);
    return () => {
      unregister();
      layer.destroy();
      chart.destroy();
      chartRef.current = null;
      layerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tf, session.start_time]);

  const fillsRef = useRef(p.fills);
  fillsRef.current = p.fills;
  const accRef = useRef(p.account);
  accRef.current = p.account;

  useEffect(() => {
    chartRef.current?.setIndicators(p.indicators);
  }, [p.indicators]);
  useEffect(() => {
    chartRef.current?.setFills(p.fills);
  }, [p.fills]);
  useEffect(() => {
    const a = p.account;
    if (a) chartRef.current?.setOrderLines(a.orders, a.avg_cost, a.qty > 0);
  }, [p.account]);
  useEffect(() => {
    layerRef.current?.setTool(p.tool);
  }, [p.tool]);

  const c = legend.c;
  const chg = c && legend.prev ? (c[4] / legend.prev[4] - 1) * 100 : null;
  const dec = session.decimals;
  return (
    <div className={`chart-panel ${p.compact ? 'compact' : ''}`}>
      <div className="cp-head">
        <div className="tf-row" role="group" aria-label="Timeframe">
          {session.tfs.map((t) => (
            <button key={t} type="button" aria-pressed={t === tf} onClick={() => p.onTf(t)}>
              {session.tf_label[t] ?? t}
            </button>
          ))}
        </div>
      </div>
      <div className="cp-body">
        <div className="cp-legend">
          {c ? (
            <>
              <span>{fmt.full(c[0])}</span>
              <span>O <b>{fmtNum(c[1], dec)}</b></span>
              <span>H <b>{fmtNum(c[2], dec)}</b></span>
              <span>L <b>{fmtNum(c[3], dec)}</b></span>
              <span>C <b className={c[4] >= c[1] ? 'up' : 'down'}>{fmtNum(c[4], dec)}</b></span>
              {chg != null && <span className={chg >= 0 ? 'up' : 'down'}>{fmtPct(chg)}</span>}
            </>
          ) : (
            <span>Memuat candle…</span>
          )}
        </div>
        <div className="cp-chart" ref={host} />
        {loading && <div className="cp-loading"><div className="spinner" /></div>}
      </div>
    </div>
  );
}
