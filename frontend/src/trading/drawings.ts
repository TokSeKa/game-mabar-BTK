/**
 * Alat gambar di atas chart (SVG overlay). Titik disimpan sebagai (waktu, harga), jadi gambar
 * yang sama tampil di semua chart dan semua timeframe.
 */
import type { Logical } from 'lightweight-charts';
import type { TradingChart } from './chart';
import { fmtNum } from './format';

export type Tool = 'none' | 'trend' | 'ray' | 'hline' | 'rect' | 'fib' | 'measure';
export interface Pt {
  t: number;
  p: number;
}
export interface Drawing {
  id: number;
  type: Exclude<Tool, 'none'>;
  pts: Pt[];
}

export const TOOL_INFO: { id: Tool; label: string; title: string }[] = [
  { id: 'trend', label: '╱', title: 'Garis tren (2 titik)' },
  { id: 'ray', label: '↗', title: 'Sinar: garis tren yang diperpanjang ke kanan' },
  { id: 'hline', label: '─', title: 'Garis horizontal (support/resistance)' },
  { id: 'rect', label: '▭', title: 'Kotak zona' },
  { id: 'fib', label: 'Fib', title: 'Fibonacci retracement' },
  { id: 'measure', label: '↕%', title: 'Ukur: persentase, jumlah candle, dan durasi' },
];
const FIB = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
const NEED: Record<Exclude<Tool, 'none'>, number> = { trend: 2, ray: 2, hline: 1, rect: 2, fib: 2, measure: 2 };

export class DrawingStore {
  items: Drawing[] = [];
  version = 0;
  private next = 1;
  private subs = new Set<() => void>();
  add(type: Drawing['type'], pts: Pt[]): Drawing {
    const d = { id: this.next++, type, pts };
    this.items.push(d);
    this.bump();
    return d;
  }
  update(id: number, pts: Pt[]): void {
    const d = this.items.find((x) => x.id === id);
    if (d) {
      d.pts = pts;
      this.bump();
    }
  }
  remove(id: number): void {
    this.items = this.items.filter((x) => x.id !== id);
    this.bump();
  }
  clear(): void {
    this.items = [];
    this.bump();
  }
  subscribe(fn: () => void): () => void {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }
  private bump(): void {
    this.version++;
    this.subs.forEach((f) => f());
  }
}

interface LayerOpts {
  decimals: number;
  tfSec: () => number;
  onToolDone: () => void;
}

export class DrawingLayer {
  private svg: SVGSVGElement;
  private tool: Tool = 'none';
  private pending: Pt[] = [];
  private hover: Pt | null = null;
  private selected: number | null = null;
  private drag: { id: number; handle: number | 'body'; start: Pt; orig: Pt[] } | null = null;
  private raf = 0;
  private sig = '';
  private unsub: () => void;

  constructor(private host: HTMLElement, private ch: TradingChart, private store: DrawingStore, private opts: LayerOpts) {
    this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.svg.setAttribute('class', 'draw-layer');
    host.appendChild(this.svg);
    this.svg.addEventListener('pointerdown', this.onDown);
    this.svg.addEventListener('pointermove', this.onMove);
    this.svg.addEventListener('pointerup', this.onUp);
    window.addEventListener('keydown', this.onKey);
    this.unsub = store.subscribe(() => (this.sig = ''));
    const loop = () => {
      this.render();
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  setTool(t: Tool): void {
    this.tool = t;
    this.pending = [];
    this.selected = null;
    this.sig = '';
    // langsung aktif, jangan tunggu frame berikutnya (klik pertama bisa lolos ke chart)
    this.svg.style.pointerEvents = t !== 'none' ? 'all' : 'none';
    this.svg.style.cursor = t !== 'none' ? 'crosshair' : '';
  }

  destroy(): void {
    cancelAnimationFrame(this.raf);
    window.removeEventListener('keydown', this.onKey);
    this.unsub();
    this.svg.remove();
  }

  // ------------------------------------------------------------ koordinat
  private area() {
    const w = this.host.clientWidth - this.ch.chart.priceScale('right').width();
    const h = this.ch.chart.panes()[0]?.getHeight() ?? this.host.clientHeight;
    return { w: Math.max(0, w), h };
  }

  private x(t: number): number | null {
    const d = this.ch.data;
    if (!d.length) return null;
    const tf = this.opts.tfSec();
    let lo = 0;
    let hi = d.length - 1;
    let logical: number;
    if (t <= d[0][0]) logical = (t - d[0][0]) / tf;
    else if (t >= d[hi][0]) logical = hi + (t - d[hi][0]) / tf;
    else {
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (d[mid][0] <= t) lo = mid;
        else hi = mid - 1;
      }
      const span = d[lo + 1][0] - d[lo][0] || tf;
      logical = lo + (t - d[lo][0]) / span;
    }
    return this.ch.chart.timeScale().logicalToCoordinate(logical as Logical);
  }

  private y(p: number): number | null {
    return this.ch.candle.priceToCoordinate(p);
  }

  private pt(e: PointerEvent): Pt | null {
    const r = this.svg.getBoundingClientRect();
    const px = e.clientX - r.left;
    const py = e.clientY - r.top;
    const logical = this.ch.chart.timeScale().coordinateToLogical(px);
    const p = this.ch.candle.coordinateToPrice(py);
    const d = this.ch.data;
    if (logical == null || p == null || !d.length) return null;
    const tf = this.opts.tfSec();
    const i = Math.floor(logical);
    let t: number;
    if (i < 0) t = d[0][0] + logical * tf;
    else if (i >= d.length - 1) t = d[d.length - 1][0] + (logical - (d.length - 1)) * tf;
    else t = d[i][0] + (logical - i) * (d[i + 1][0] - d[i][0]);
    return { t, p };
  }

  // ------------------------------------------------------------ interaksi
  private onDown = (e: PointerEvent): void => {
    const target = e.target as Element;
    const pt = this.pt(e);
    if (!pt) return;
    if (this.tool !== 'none') {
      e.preventDefault();
      this.pending.push(pt);
      if (this.pending.length >= NEED[this.tool]) {
        const d = this.store.add(this.tool, this.pending.slice(0, NEED[this.tool]));
        this.selected = d.id;
        this.tool = 'none';
        this.pending = [];
        this.opts.onToolDone();
      }
      this.sig = '';
      return;
    }
    const id = Number(target.getAttribute('data-id'));
    if (!id) {
      this.selected = null;
      this.sig = '';
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    const d = this.store.items.find((x) => x.id === id);
    if (!d) return;
    this.selected = id;
    const h = target.getAttribute('data-h');
    this.drag = { id, handle: h == null ? 'body' : Number(h), start: pt, orig: d.pts.map((p) => ({ ...p })) };
    this.svg.setPointerCapture(e.pointerId);
    this.sig = '';
  };

  private onMove = (e: PointerEvent): void => {
    const pt = this.pt(e);
    if (!pt) return;
    if (this.tool !== 'none') {
      this.hover = pt;
      this.sig = '';
      return;
    }
    if (!this.drag) return;
    const { id, handle, start, orig } = this.drag;
    const dt = pt.t - start.t;
    const dp = pt.p - start.p;
    const pts = handle === 'body' ? orig.map((p) => ({ t: p.t + dt, p: p.p + dp })) : orig.map((p, i) => (i === handle ? pt : p));
    this.store.update(id, pts);
  };

  private onUp = (e: PointerEvent): void => {
    if (this.drag) {
      this.drag = null;
      try {
        this.svg.releasePointerCapture(e.pointerId);
      } catch {
        /* abaikan */
      }
    }
  };

  private onKey = (e: KeyboardEvent): void => {
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if ((e.key === 'Delete' || e.key === 'Backspace') && this.selected) {
      this.store.remove(this.selected);
      this.selected = null;
    }
    if (e.key === 'Escape') {
      this.tool = 'none';
      this.pending = [];
      this.selected = null;
      this.opts.onToolDone();
      this.sig = '';
    }
  };

  removeSelected(): boolean {
    if (!this.selected) return false;
    this.store.remove(this.selected);
    this.selected = null;
    return true;
  }

  // ------------------------------------------------------------ gambar
  private render(): void {
    const { w, h } = this.area();
    const vr = this.ch.chart.timeScale().getVisibleLogicalRange();
    const ref = this.ch.lastClose() ?? 1;
    const sig = [w, h, vr?.from, vr?.to, this.ch.data.length, this.y(ref), this.y(ref * 1.1), this.store.version, this.tool,
      this.pending.length, this.hover?.t, this.hover?.p, this.selected].join('|');
    if (sig === this.sig) return;
    this.sig = sig;
    this.svg.style.pointerEvents = this.tool !== 'none' ? 'all' : 'none';
    this.svg.style.cursor = this.tool !== 'none' ? 'crosshair' : '';
    const dec = this.opts.decimals;
    const parts: string[] = [`<defs><clipPath id="dl-clip"><rect x="0" y="0" width="${w}" height="${h}"/></clipPath></defs><g clip-path="url(#dl-clip)">`];
    const items: Drawing[] = [...this.store.items];
    if (this.tool !== 'none' && this.pending.length && this.hover) items.push({ id: 0, type: this.tool, pts: [...this.pending, this.hover] });
    if (this.tool === 'hline' && this.hover) items.push({ id: 0, type: 'hline', pts: [this.hover] });
    for (const d of items) {
      const sel = d.id !== 0 && d.id === this.selected;
      const col = sel ? '#ffffff' : '#ffd166';
      const xy = d.pts.map((p) => [this.x(p.t), this.y(p.p)] as const);
      if (xy.some(([a, b]) => a == null || b == null)) continue;
      const P = xy as [number, number][];
      const hit = (body: string) => (d.id ? body.replace('<line ', `<line data-id="${d.id}" class="hit" `).replace('<rect ', `<rect data-id="${d.id}" class="hit" `) : '');
      if (d.type === 'trend' || d.type === 'ray') {
        let [x1, y1] = P[0];
        let [x2, y2] = P[1];
        if (d.type === 'ray' && x2 !== x1) {
          const k = (y2 - y1) / (x2 - x1);
          const xe = x2 > x1 ? w : 0;
          y2 = y1 + k * (xe - x1);
          x2 = xe;
        }
        parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${col}" stroke-width="1.6"/>`);
        parts.push(hit(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`));
        [x1, y1] = P[0];
      } else if (d.type === 'hline') {
        const y = P[0][1];
        parts.push(`<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke="${col}" stroke-width="1.4" stroke-dasharray="6 4"/>`);
        parts.push(hit(`<line x1="0" y1="${y}" x2="${w}" y2="${y}"/>`));
        parts.push(`<text x="6" y="${y - 4}" fill="${col}">${fmtNum(d.pts[0].p, dec)}</text>`);
      } else if (d.type === 'rect' || d.type === 'measure') {
        const [x1, y1] = P[0];
        const [x2, y2] = P[1];
        const up = d.pts[1].p >= d.pts[0].p;
        const fill = d.type === 'measure' ? (up ? 'rgba(63,208,160,.14)' : 'rgba(255,106,106,.14)') : 'rgba(255,209,102,.10)';
        const stroke = d.type === 'measure' ? (up ? '#3fd0a0' : '#ff6a6a') : col;
        const rx = Math.min(x1, x2);
        const ry = Math.min(y1, y2);
        parts.push(`<rect x="${rx}" y="${ry}" width="${Math.abs(x2 - x1)}" height="${Math.abs(y2 - y1)}" fill="${fill}" stroke="${stroke}" stroke-width="1.2"/>`);
        parts.push(hit(`<rect x="${rx}" y="${ry}" width="${Math.abs(x2 - x1)}" height="${Math.abs(y2 - y1)}" fill="transparent"/>`));
        if (d.type === 'measure') {
          const pct = (d.pts[1].p / d.pts[0].p - 1) * 100;
          const bars = Math.round(Math.abs(d.pts[1].t - d.pts[0].t) / this.opts.tfSec());
          const label = `${pct >= 0 ? '+' : ''}${fmtNum(pct, 2)}% · ${bars} candle`;
          parts.push(`<text x="${rx + 4}" y="${ry - 5}" fill="${stroke}">${label}</text>`);
        }
      } else if (d.type === 'fib') {
        const [x1] = P[0];
        const [x2] = P[1];
        const p0 = d.pts[0].p;
        const p1 = d.pts[1].p;
        const xa = Math.min(x1, x2);
        for (const lv of FIB) {
          const price = p1 + (p0 - p1) * lv;
          const y = this.y(price);
          if (y == null) continue;
          parts.push(`<line x1="${xa}" y1="${y}" x2="${w}" y2="${y}" stroke="${col}" stroke-opacity="${lv === 0 || lv === 1 ? 1 : 0.65}" stroke-width="1"/>`);
          parts.push(`<text x="${xa + 4}" y="${y - 3}" fill="${col}">${lv} · ${fmtNum(price, dec)}</text>`);
        }
        const yA = P[0][1];
        const yB = P[1][1];
        parts.push(hit(`<line x1="${x1}" y1="${yA}" x2="${x2}" y2="${yB}"/>`));
        parts.push(`<line x1="${x1}" y1="${yA}" x2="${x2}" y2="${yB}" stroke="${col}" stroke-dasharray="3 3" stroke-width="1"/>`);
      }
      if (sel || d.id === 0) {
        P.forEach(([x, y], i) => {
          parts.push(`<circle cx="${x}" cy="${y}" r="5" fill="#17142c" stroke="${col}" stroke-width="2" ${d.id ? `data-id="${d.id}" data-h="${i}" class="handle"` : ''}/>`);
        });
      }
    }
    for (const p of this.pending) {
      const x = this.x(p.t);
      const y = this.y(p.p);
      if (x != null && y != null) parts.push(`<circle cx="${x}" cy="${y}" r="4" fill="#ffd166"/>`);
    }
    parts.push('</g>');
    this.svg.innerHTML = parts.join('');
  }
}
