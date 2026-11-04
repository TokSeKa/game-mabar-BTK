/** Indikator teknikal. Semua fungsi mengembalikan array sepanjang data (null = belum cukup data). */
import type { Candle } from './api';

export type Series = (number | null)[];

export function sma(v: number[], n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  let s = 0;
  for (let i = 0; i < v.length; i++) {
    s += v[i];
    if (i >= n) s -= v[i - n];
    if (i >= n - 1) out[i] = s / n;
  }
  return out;
}

export function ema(v: number[], n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  const k = 2 / (n + 1);
  let prev: number | null = null;
  let s = 0;
  for (let i = 0; i < v.length; i++) {
    if (prev == null) {
      s += v[i];
      if (i === n - 1) prev = s / n;
      else continue;
    } else prev = v[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

function emaSeries(v: Series, n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  const k = 2 / (n + 1);
  let prev: number | null = null;
  let s = 0;
  let cnt = 0;
  for (let i = 0; i < v.length; i++) {
    const x = v[i];
    if (x == null) continue;
    if (prev == null) {
      s += x;
      cnt++;
      if (cnt === n) prev = s / n;
      else continue;
    } else prev = x * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function bollinger(v: number[], n: number, mult: number): { mid: Series; up: Series; lo: Series } {
  const mid = sma(v, n);
  const up: Series = new Array(v.length).fill(null);
  const lo: Series = new Array(v.length).fill(null);
  for (let i = n - 1; i < v.length; i++) {
    const m = mid[i]!;
    let ss = 0;
    for (let j = i - n + 1; j <= i; j++) ss += (v[j] - m) ** 2;
    const sd = Math.sqrt(ss / n);
    up[i] = m + mult * sd;
    lo[i] = m - mult * sd;
  }
  return { mid, up, lo };
}

export function rsi(v: number[], n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  let g = 0;
  let l = 0;
  for (let i = 1; i < v.length; i++) {
    const d = v[i] - v[i - 1];
    const up = Math.max(d, 0);
    const dn = Math.max(-d, 0);
    if (i <= n) {
      g += up;
      l += dn;
      if (i === n) {
        g /= n;
        l /= n;
        out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
      }
    } else {
      g = (g * (n - 1) + up) / n;
      l = (l * (n - 1) + dn) / n;
      out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
    }
  }
  return out;
}

export function macd(v: number[], fast: number, slow: number, signal: number): { macd: Series; signal: Series; hist: Series } {
  const f = ema(v, fast);
  const s = ema(v, slow);
  const m: Series = v.map((_, i) => (f[i] != null && s[i] != null ? f[i]! - s[i]! : null));
  const sig = emaSeries(m, signal);
  const hist: Series = m.map((x, i) => (x != null && sig[i] != null ? x - sig[i]! : null));
  return { macd: m, signal: sig, hist };
}

export function stochastic(c: Candle[], n: number, smoothK: number, d: number): { k: Series; d: Series } {
  const raw: Series = c.map((_, i) => {
    if (i < n - 1) return null;
    let hh = -Infinity;
    let ll = Infinity;
    for (let j = i - n + 1; j <= i; j++) {
      hh = Math.max(hh, c[j][2]);
      ll = Math.min(ll, c[j][3]);
    }
    return hh === ll ? 50 : ((c[i][4] - ll) / (hh - ll)) * 100;
  });
  const smooth = (s: Series, m: number): Series =>
    s.map((_, i) => {
      if (i < m - 1) return null;
      let sum = 0;
      for (let j = i - m + 1; j <= i; j++) {
        if (s[j] == null) return null;
        sum += s[j]!;
      }
      return sum / m;
    });
  const k = smooth(raw, smoothK);
  return { k, d: smooth(k, d) };
}

export function atr(c: Candle[], n: number): Series {
  const out: Series = new Array(c.length).fill(null);
  let prev: number | null = null;
  let s = 0;
  for (let i = 0; i < c.length; i++) {
    const tr = i === 0 ? c[i][2] - c[i][3] : Math.max(c[i][2] - c[i][3], Math.abs(c[i][2] - c[i - 1][4]), Math.abs(c[i][3] - c[i - 1][4]));
    if (prev == null) {
      s += tr;
      if (i === n - 1) prev = s / n;
      else continue;
    } else prev = (prev * (n - 1) + tr) / n;
    out[i] = prev;
  }
  return out;
}

/** VWAP yang di-reset setiap hari (untuk timeframe intraday). */
export function vwapDaily(c: Candle[]): Series {
  let day = -1;
  let pv = 0;
  let vol = 0;
  return c.map((x) => {
    const d = Math.floor(x[0] / 86400);
    if (d !== day) {
      day = d;
      pv = 0;
      vol = 0;
    }
    const tp = (x[2] + x[3] + x[4]) / 3;
    pv += tp * x[5];
    vol += x[5];
    return vol > 0 ? pv / vol : tp;
  });
}

export interface IndicatorConfig {
  ma: { on: boolean; type: 'sma' | 'ema'; periods: number[] };
  bb: { on: boolean; n: number; mult: number };
  vwap: { on: boolean };
  volume: { on: boolean };
  rsi: { on: boolean; n: number };
  macd: { on: boolean; fast: number; slow: number; signal: number };
  stoch: { on: boolean; n: number; k: number; d: number };
  atr: { on: boolean; n: number };
}

export const DEFAULT_INDICATORS: IndicatorConfig = {
  ma: { on: true, type: 'ema', periods: [20, 50, 200] },
  bb: { on: false, n: 20, mult: 2 },
  vwap: { on: false },
  volume: { on: true },
  rsi: { on: true, n: 14 },
  macd: { on: false, fast: 12, slow: 26, signal: 9 },
  stoch: { on: false, n: 14, k: 3, d: 3 },
  atr: { on: false, n: 14 },
};
