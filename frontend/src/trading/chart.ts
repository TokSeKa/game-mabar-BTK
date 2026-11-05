import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type Logical,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { Candle, Fill, Order } from './api';
import { makeTimeFmt } from './format';
import { atr, bollinger, ema, macd, rsi, sma, stochastic, vwapDaily, type IndicatorConfig, type Series } from './indicators';

export const C = {
  bg: '#17142c',
  grid: '#25204a',
  text: '#a69fd0',
  up: '#3fd0a0',
  down: '#ff6a6a',
  upVol: 'rgba(63,208,160,0.35)',
  downVol: 'rgba(255,106,106,0.35)',
  gold: '#ffd166',
  blue: '#7aa2ff',
  violet: '#c29bff',
  pink: '#f37aa5',
  teal: '#3fd0c9',
  orange: '#f0a24a',
};
const MA_COLORS = [C.gold, C.blue, C.pink, C.teal, C.orange];

export interface ChartOpts {
  decimals: number;
  blind: boolean;
  startTime: number;
  intraday: boolean;
  onNeedMore?: () => void;
  onCrosshair?: (c: Candle | null, prev: Candle | null) => void;
}

type AnySeries = ISeriesApi<'Line'> | ISeriesApi<'Histogram'>;
interface IndSeries {
  key: string;
  series: AnySeries;
  values: () => Series;
  color?: (v: number) => string;
}

const T = (t: number) => t as UTCTimestamp as Time;

export class TradingChart {
  chart: IChartApi;
  candle: ISeriesApi<'Candlestick'>;
  volume: ISeriesApi<'Histogram'>;
  data: Candle[] = [];
  private ind: IndSeries[] = [];
  private cache: Record<string, Series> = {};
  private cfg: IndicatorConfig;
  private markers: ISeriesMarkersPluginApi<Time>;
  private lines: IPriceLine[] = [];
  private fills: Fill[] = [];
  private needMoreArmed = true;
  private opts: ChartOpts;

  constructor(el: HTMLElement, opts: ChartOpts, cfg: IndicatorConfig) {
    this.opts = opts;
    this.cfg = cfg;
    const fmt = makeTimeFmt(opts.blind, opts.startTime);
    this.chart = createChart(el, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: C.bg }, textColor: C.text, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, panes: { separatorColor: C.grid } },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: C.grid },
      timeScale: {
        borderColor: C.grid, rightOffset: 8, timeVisible: opts.intraday, secondsVisible: false,
        tickMarkFormatter: (t: Time, type: number) => fmt.tick(t as number, type),
      },
      localization: { locale: 'id-ID', timeFormatter: (t: Time) => fmt.full(t as number) },
    });
    const pf = { type: 'price' as const, precision: opts.decimals, minMove: Math.pow(10, -opts.decimals) };
    this.candle = this.chart.addSeries(CandlestickSeries, {
      upColor: C.up, downColor: C.down, borderUpColor: C.up, borderDownColor: C.down, wickUpColor: C.up, wickDownColor: C.down,
      priceFormat: pf,
    });
    this.volume = this.chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'vol', lastValueVisible: false, priceLineVisible: false });
    this.chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    this.markers = createSeriesMarkers(this.candle, []);
    this.chart.timeScale().subscribeVisibleLogicalRangeChange((r) => {
      if (!r || !opts.onNeedMore) return;
      if (r.from < 15 && this.needMoreArmed && this.data.length) {
        this.needMoreArmed = false;
        opts.onNeedMore();
      }
    });
    this.chart.subscribeCrosshairMove((p) => {
      if (!opts.onCrosshair) return;
      const i = p.logical != null ? Math.round(p.logical) : -1;
      const c = i >= 0 && i < this.data.length ? this.data[i] : this.data[this.data.length - 1] ?? null;
      const prev = i > 0 && i < this.data.length ? this.data[i - 1] : this.data[this.data.length - 2] ?? null;
      opts.onCrosshair(c, prev);
    });
    this.buildIndicators();
  }

  // ------------------------------------------------------------ data
  setData(candles: Candle[], prepended = 0): void {
    const range = prepended ? this.chart.timeScale().getVisibleLogicalRange() : null;
    this.data = candles;
    this.candle.setData(candles.map((c) => ({ time: T(c[0]), open: c[1], high: c[2], low: c[3], close: c[4] })));
    this.volume.setData(candles.map((c) => ({ time: T(c[0]), value: c[5], color: c[4] >= c[1] ? C.upVol : C.downVol })));
    this.recompute();
    for (const s of this.ind) this.pushAll(s);
    this.renderMarkers();
    if (range) {
      this.chart.timeScale().setVisibleLogicalRange({ from: (range.from + prepended) as Logical, to: (range.to + prepended) as Logical });
    }
    this.needMoreArmed = true;
  }

  applyUpdates(updates: Candle[]): void {
    if (!updates.length) return;
    let first = -1;
    for (const u of updates) {
      const last = this.data[this.data.length - 1];
      if (last && u[0] < last[0]) continue;
      if (last && u[0] === last[0]) this.data[this.data.length - 1] = u;
      else this.data.push(u);
      if (first < 0) first = this.data.length - 1;
      this.candle.update({ time: T(u[0]), open: u[1], high: u[2], low: u[3], close: u[4] });
      this.volume.update({ time: T(u[0]), value: u[5], color: u[4] >= u[1] ? C.upVol : C.downVol });
    }
    if (first < 0) return;
    this.recompute();
    for (const s of this.ind) {
      const v = s.values();
      for (let i = first; i < this.data.length; i++) {
        const x = v[i];
        if (x == null) continue;
        s.series.update(s.color ? { time: T(this.data[i][0]), value: x, color: s.color(x) } : { time: T(this.data[i][0]), value: x });
      }
    }
    this.renderMarkers();
  }

  lastClose(): number | null {
    return this.data.length ? this.data[this.data.length - 1][4] : null;
  }

  scrollToEnd(): void {
    this.chart.timeScale().scrollToRealTime();
  }

  // ------------------------------------------------------------ indikator
  setIndicators(cfg: IndicatorConfig): void {
    this.cfg = cfg;
    for (const s of this.ind) this.chart.removeSeries(s.series);
    this.ind = [];
    while (this.chart.panes().length > 1) this.chart.removePane(this.chart.panes().length - 1);
    this.buildIndicators();
    this.recompute();
    for (const s of this.ind) this.pushAll(s);
  }

  private line(key: string, color: string, pane = 0, width: 1 | 2 = 1, style = LineStyle.Solid): ISeriesApi<'Line'> {
    return this.chart.addSeries(LineSeries, {
      color, lineWidth: width, lineStyle: style, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      priceFormat: { type: 'price', precision: key.startsWith('rsi') || key.startsWith('stoch') ? 1 : this.opts.decimals, minMove: Math.pow(10, -this.opts.decimals) },
    }, pane);
  }

  private buildIndicators(): void {
    const cfg = this.cfg;
    const add = (key: string, series: AnySeries, color?: (v: number) => string) => this.ind.push({ key, series, values: () => this.cache[key] ?? [], color });
    this.volume.applyOptions({ visible: cfg.volume.on });
    if (cfg.ma.on) cfg.ma.periods.slice(0, 5).forEach((p, i) => add(`ma${i}`, this.line(`ma${i}`, MA_COLORS[i % MA_COLORS.length], 0, 1)));
    if (cfg.bb.on) {
      add('bbu', this.line('bbu', C.violet, 0, 1, LineStyle.Dashed));
      add('bbm', this.line('bbm', C.violet, 0, 1, LineStyle.Dotted));
      add('bbl', this.line('bbl', C.violet, 0, 1, LineStyle.Dashed));
    }
    if (cfg.vwap.on && this.opts.intraday) add('vwap', this.line('vwap', C.orange, 0, 2));
    let pane = 1;
    if (cfg.rsi.on) {
      const s = this.line('rsi', C.violet, pane, 1);
      s.createPriceLine({ price: 70, color: C.grid, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' });
      s.createPriceLine({ price: 30, color: C.grid, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' });
      add('rsi', s);
      pane++;
    }
    if (cfg.macd.on) {
      const h = this.chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false, priceFormat: { type: 'price', precision: this.opts.decimals, minMove: Math.pow(10, -this.opts.decimals) } }, pane);
      add('macdh', h, (v) => (v >= 0 ? C.upVol : C.downVol));
      add('macd', this.line('macd', C.blue, pane, 1));
      add('macds', this.line('macds', C.orange, pane, 1));
      pane++;
    }
    if (cfg.stoch.on) {
      const s = this.line('stochk', C.teal, pane, 1);
      s.createPriceLine({ price: 80, color: C.grid, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' });
      s.createPriceLine({ price: 20, color: C.grid, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' });
      add('stochk', s);
      add('stochd', this.line('stochd', C.pink, pane, 1));
      pane++;
    }
    if (cfg.atr.on) {
      add('atr', this.line('atr', C.gold, pane, 1));
      pane++;
    }
    const panes = this.chart.panes();
    for (let i = 1; i < panes.length; i++) panes[i].setHeight(95);
  }

  private recompute(): void {
    const d = this.data;
    const close = d.map((c) => c[4]);
    const cfg = this.cfg;
    const cache: Record<string, Series> = {};
    if (cfg.ma.on) cfg.ma.periods.slice(0, 5).forEach((p, i) => (cache[`ma${i}`] = cfg.ma.type === 'ema' ? ema(close, p) : sma(close, p)));
    if (cfg.bb.on) {
      const b = bollinger(close, cfg.bb.n, cfg.bb.mult);
      cache.bbu = b.up;
      cache.bbm = b.mid;
      cache.bbl = b.lo;
    }
    if (cfg.vwap.on && this.opts.intraday) cache.vwap = vwapDaily(d);
    if (cfg.rsi.on) cache.rsi = rsi(close, cfg.rsi.n);
    if (cfg.macd.on) {
      const m = macd(close, cfg.macd.fast, cfg.macd.slow, cfg.macd.signal);
      cache.macd = m.macd;
      cache.macds = m.signal;
      cache.macdh = m.hist;
    }
    if (cfg.stoch.on) {
      const s = stochastic(d, cfg.stoch.n, cfg.stoch.k, cfg.stoch.d);
      cache.stochk = s.k;
      cache.stochd = s.d;
    }
    if (cfg.atr.on) cache.atr = atr(d, cfg.atr.n);
    this.cache = cache;
  }

  private pushAll(s: IndSeries): void {
    const v = s.values();
    const pts: any[] = [];
    for (let i = 0; i < this.data.length; i++) {
      const x = v[i];
      if (x == null) continue;
      pts.push(s.color ? { time: T(this.data[i][0]), value: x, color: s.color(x) } : { time: T(this.data[i][0]), value: x });
    }
    s.series.setData(pts);
  }

  latest(): Record<string, number | null> {
    const out: Record<string, number | null> = {};
    for (const [k, v] of Object.entries(this.cache)) out[k] = v[v.length - 1] ?? null;
    return out;
  }

  // ------------------------------------------------------------ order & transaksi
  setFills(fills: Fill[]): void {
    this.fills = fills;
    this.renderMarkers();
  }

  private renderMarkers(): void {
    const times = this.data.map((c) => c[0]);
    if (!times.length) {
      this.markers.setMarkers([]);
      return;
    }
    const at = (t: number) => {
      let lo = 0;
      let hi = times.length - 1;
      if (t < times[0]) return null;
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (times[mid] <= t) lo = mid;
        else hi = mid - 1;
      }
      return times[lo];
    };
    const ms: SeriesMarker<Time>[] = [];
    for (const f of this.fills.slice(-300)) {
      const t = at(f.time);
      if (t == null) continue;
      const buy = f.side === 'buy';
      const liq = f.label === 'Likuidasi' || f.label.startsWith('Forced');
      ms.push({
        time: T(t), position: buy ? 'belowBar' : 'aboveBar', shape: liq ? 'circle' : buy ? 'arrowUp' : 'arrowDown',
        color: liq ? C.orange : buy ? C.up : f.label === 'TP' ? C.blue : C.down,
        text: liq ? 'LIQ' : f.label === 'SL' || f.label === 'TP' ? f.label : buy ? 'B' : 'J',
      });
    }
    ms.sort((a, b) => (a.time as number) - (b.time as number));
    this.markers.setMarkers(ms);
  }

  setOrderLines(orders: Order[], avgCost: number, holding: boolean, pos?: { side: 'long' | 'short' | null; liq: number | null; call: number | null }): void {
    for (const l of this.lines) this.candle.removePriceLine(l);
    this.lines = [];
    for (const o of orders) {
      const color = o.label === 'TP' ? C.blue : o.label === 'SL' ? C.down : o.side === 'buy' ? C.up : C.down;
      const sisi = o.side === 'buy' ? 'beli' : 'jual';
      const title = o.label === 'TP' || o.label === 'SL' ? o.label : o.label === 'Tutup' ? 'Tutup' : o.kind === 'stop' ? `Stop ${sisi}` : o.kind === 'stop_limit' && !o.triggered ? `Limit ${sisi}` : `Limit ${sisi}`;
      this.lines.push(this.candle.createPriceLine({ price: o.price, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title }));
      if (o.kind === 'stop_limit' && !o.triggered && o.stop) {
        this.lines.push(this.candle.createPriceLine({ price: o.stop, color, lineWidth: 1, lineStyle: LineStyle.SparseDotted, axisLabelVisible: true, title: `Picu ${sisi}` }));
      }
    }
    if (holding && avgCost > 0) {
      const title = pos?.side === 'long' ? 'Entry long' : pos?.side === 'short' ? 'Entry short' : 'Rata-rata';
      this.lines.push(this.candle.createPriceLine({ price: avgCost, color: C.gold, lineWidth: 1, lineStyle: LineStyle.Solid, axisLabelVisible: true, title }));
    }
    if (pos?.liq && pos.liq > 0) {
      this.lines.push(this.candle.createPriceLine({ price: pos.liq, color: C.orange, lineWidth: 2, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: 'Likuidasi' }));
    }
    if (pos?.call && pos.call > 0) {
      this.lines.push(this.candle.createPriceLine({ price: pos.call, color: C.pink, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: 'Margin call' }));
    }
  }

  destroy(): void {
    this.chart.remove();
  }
}
