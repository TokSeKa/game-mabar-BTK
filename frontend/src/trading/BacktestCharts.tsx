import { useEffect, useRef } from 'react';
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { AsetChart } from './backtestApi';
import { C } from './chart';
import { makeTimeFmt } from './format';

const T = (t: number) => t as UTCTimestamp as Time;
const PLOT_COLORS = [C.gold, C.blue, C.violet, C.pink, C.teal, C.orange];
const fmt = makeTimeFmt(false, 0);

function baseChart(el: HTMLElement, decimals = 2): IChartApi {
  return createChart(el, {
    autoSize: true,
    layout: { background: { type: ColorType.Solid, color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11 },
    grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
    crosshair: { mode: CrosshairMode.Normal },
    rightPriceScale: { borderColor: C.grid },
    timeScale: { borderColor: C.grid, timeVisible: true, tickMarkFormatter: (t: Time, type: number) => fmt.tick(t as number, type) },
    localization: {
      timeFormatter: (t: Time) => fmt.full(t as number),
      priceFormatter: (p: number) => p.toLocaleString('id-ID', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }),
    },
  });
}

function dedupe(points: [number, number][]): { time: Time; value: number }[] {
  const out: { time: Time; value: number }[] = [];
  let last = -Infinity;
  for (const [t, v] of points) {
    if (t <= last || v == null || !Number.isFinite(v)) continue;
    out.push({ time: T(t), value: v });
    last = t;
  }
  return out;
}

/** Kurva ekuitas strategi vs beli-lalu-tahan, plus drawdown di bawahnya (skala waktu sinkron). */
export function EquityCharts({ kurva, log }: { kurva: [number, number, number][]; log?: boolean }) {
  const top = useRef<HTMLDivElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!top.current || !bottom.current || kurva.length < 2) return;
    const a = baseChart(top.current, 0);
    const b = baseChart(bottom.current, 1);
    a.applyOptions({ rightPriceScale: { mode: log ? 1 : 0 } });
    const eq = a.addSeries(LineSeries, { color: C.gold, lineWidth: 2, priceLineVisible: false, title: 'Strategi' });
    const bh = a.addSeries(LineSeries, { color: C.text, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, title: 'Beli-tahan' });
    eq.setData(dedupe(kurva.map((k) => [k[0], k[1]])));
    bh.setData(dedupe(kurva.map((k) => [k[0], k[2]])));
    let peak = -Infinity;
    const dd = kurva.map((k) => {
      peak = Math.max(peak, k[1]);
      return [k[0], peak > 0 ? (k[1] / peak - 1) * 100 : 0] as [number, number];
    });
    const area = b.addSeries(AreaSeries, { lineColor: C.down, topColor: 'rgba(255,106,106,0.05)', bottomColor: 'rgba(255,106,106,0.35)', lineWidth: 1, priceLineVisible: false, invertFilledArea: true });
    area.setData(dedupe(dd));
    a.timeScale().fitContent();
    b.timeScale().fitContent();
    let syncing = false;
    const sync = (from: IChartApi, to: IChartApi) => (r: any) => {
      if (syncing || !r) return;
      syncing = true;
      to.timeScale().setVisibleLogicalRange(r);
      syncing = false;
    };
    a.timeScale().subscribeVisibleLogicalRangeChange(sync(a, b));
    b.timeScale().subscribeVisibleLogicalRangeChange(sync(b, a));
    return () => {
      a.remove();
      b.remove();
    };
  }, [kurva, log]);
  return (
    <div className="bt-eq">
      <div className="bt-eq-top" ref={top} />
      <div className="bt-eq-dd" ref={bottom} />
    </div>
  );
}

function decimalsFor(p: number): number {
  if (p >= 1000) return 2;
  if (p >= 10) return 3;
  if (p >= 1) return 4;
  return 6;
}

/** Candle satu aset + indikator dari PLOT + penanda setiap transaksi. */
export function AssetChart({ data }: { data: AsetChart }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || !data.t.length) return;
    const lastC = data.c.filter((x) => x != null).slice(-1)[0] ?? 1;
    const dec = decimalsFor(lastC as number);
    const ch = baseChart(ref.current, dec);
    const candle = ch.addSeries(CandlestickSeries, {
      upColor: C.up, downColor: C.down, borderUpColor: C.up, borderDownColor: C.down, wickUpColor: C.up, wickDownColor: C.down,
      priceFormat: { type: 'price', precision: dec, minMove: Math.pow(10, -dec) },
    });
    const rows = [];
    for (let i = 0; i < data.t.length; i++) {
      const o = data.o[i], h = data.h[i], l = data.l[i], c = data.c[i];
      if (o == null || h == null || l == null || c == null) continue;
      rows.push({ time: T(data.t[i]), open: o, high: h, low: l, close: c });
    }
    candle.setData(rows);
    Object.entries(data.plot).forEach(([name, vals], k) => {
      const s = ch.addSeries(LineSeries, { color: PLOT_COLORS[k % PLOT_COLORS.length], lineWidth: 1, priceLineVisible: false, lastValueVisible: false, title: name });
      s.setData(data.t.map((t, i) => (vals[i] == null ? { time: T(t) } : { time: T(t), value: vals[i] as number })) as any);
    });
    const markers: SeriesMarker<Time>[] = data.fills.map((f) => {
      const buy = f.side === 'buy';
      const liq = f.label === 'Likuidasi' || f.label.startsWith('Forced');
      const text = liq ? 'LIQ' : f.label === 'SL' || f.label === 'TP' ? f.label : buy ? 'B' : 'J';
      return {
        time: T(f.time), position: buy ? 'belowBar' : 'aboveBar', shape: liq ? 'circle' : buy ? 'arrowUp' : 'arrowDown',
        color: liq ? C.orange : f.label === 'TP' ? C.blue : buy ? C.up : C.down, text,
      };
    });
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    createSeriesMarkers(candle, markers);
    const i0 = Math.max(0, data.t.findIndex((t) => t >= data.mulai));
    const span = Math.min(400, data.t.length - i0);
    ch.timeScale().setVisibleLogicalRange({ from: data.t.length - span, to: data.t.length + 3 });
    return () => ch.remove();
  }, [data]);
  return <div className="bt-asset-chart" ref={ref} />;
}
