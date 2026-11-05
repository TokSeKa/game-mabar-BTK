import { apiUrl } from '../api';
import { load, remove, save } from '../storage';

export type Candle = [number, number, number, number, number, number]; // t (detik), o, h, l, c, v

export interface MarketAsset {
  id: string;
  symbol: string;
  name: string;
  tfs: string[];
  candles: number;
  range: Record<string, [number, number]>;
}
export interface MarketSummary {
  id: string;
  nama: string;
  currency: string;
  assets: MarketAsset[];
}
export interface MarketSpec {
  id: string;
  nama: string;
  currency: string;
  modal: number;
  fee_beli: number;
  fee_jual: number;
  slippage: number;
  lot: number;
  satuan: string;
  catatan_fee: string;
  tfs: string[];
}
export interface ProductSpec {
  id: 'futures' | 'margin';
  nama: string;
  kind: 'perp' | 'margin';
  fee_beli: number;
  fee_jual: number;
  maker: number | null;
  max_lev: number;
  default_lev: number;
  tiers: { cap: number | null; mmr: number; max_lev: number }[] | null;
  mmr_long: number;
  mmr_short: number;
  call_long: number;
  call_short: number;
  short: boolean;
  short_list: string[] | null;
  short_ok: boolean | null;
  funding: number;
  funding_hours: number;
  interest_apr: number;
  borrow_apr: number;
  day_count: number;
  insurance: boolean;
  min_short_equity: number;
  uptick: boolean;
  per_share: [number, number, number] | null;
  sec_fee: number;
  taf: [number, number] | null;
  modes: string[];
  catatan: string[];
}
export type Aturan = 'nyata' | 'bebas';
export interface Katalog {
  pasar: Record<string, MarketSummary>;
  spec: Record<string, MarketSpec>;
  tf_label: Record<string, string>;
  produk?: Record<Aturan, Record<string, Record<string, ProductSpec>>>;
}

export interface Order {
  id: number;
  side: 'buy' | 'sell';
  kind: 'limit' | 'stop' | 'stop_limit';
  price: number;
  stop?: number | null;
  reduce_only?: boolean;
  post_only?: boolean;
  triggered?: boolean;
  qty: number;
  created: number;
  label: string;
  group: number | null;
  sl: number | null;
  tp: number | null;
  status: string;
}
export interface Fill {
  id: number;
  order_id: number | null;
  time: number;
  side: 'buy' | 'sell';
  qty: number;
  price: number;
  fee: number;
  label: string;
  pnl: number | null;
  note: string;
}
export interface AccountSnap {
  cash: number;
  free_cash: number;
  reserved_cash: number;
  qty: number;
  free_qty: number;
  avg_cost: number;
  equity: number;
  return_pct: number;
  realized: number;
  unrealized: number;
  fees_paid: number;
  max_dd_pct: number;
  max_buy: number;
  orders: Order[];
  n_trades: number;
  // futures / margin
  product?: string;
  kind?: 'perp' | 'margin';
  mode?: 'cross' | 'isolated';
  lev?: number;
  wallet?: number;
  entry?: number;
  side?: 'long' | 'short' | null;
  notional?: number;
  roe_pct?: number | null;
  margin?: number;
  maint?: number;
  margin_balance?: number;
  margin_ratio?: number;
  liq_price?: number | null;
  call_price?: number | null;
  margin_call?: boolean;
  max_lev?: number;
  short_ok?: boolean;
  funding_paid?: number;
  interest_paid?: number;
  borrow_paid?: number;
  liq_loss?: number;
  n_liq?: number;
  next_funding?: { time: number; rate: number } | null;
  max_sell?: number;
}
export interface SessionInfo {
  type: 'session';
  produk?: 'spot' | 'futures' | 'margin';
  product?: ProductSpec | null;
  mode: 'solo' | 'harian' | 'harian-latihan' | 'balapan';
  market: string;
  market_nama: string;
  currency: string;
  label: string;
  blind: { nama: boolean; tanggal: boolean; harga: boolean };
  tfs: string[];
  tf_label: Record<string, string>;
  base_tf: string;
  chart_tf: string;
  decimals: number;
  lot: number;
  qty_step: number;
  satuan: string;
  min_notional: number;
  fees: { beli: number; jual: number; slippage: number; catatan: string };
  capital: number;
  start_time: number;
  now: number;
  price: number;
  progress: number;
  fixed_end: boolean;
  id?: string;
  secret?: string;
  resumed?: boolean;
  room?: string;
  player_id?: string;
}
export interface Stats {
  capital: number;
  equity: number;
  return_pct: number;
  buy_hold_pct: number;
  n_trades: number;
  n_fills: number;
  win_rate: number | null;
  profit_factor: number | null;
  avg_win_pct: number | null;
  avg_loss_pct: number | null;
  best_pct: number | null;
  worst_pct: number | null;
  max_dd_pct: number;
  fees_paid: number;
  realized: number;
  exposure_pct: number;
  open_qty: number;
  open_value: number;
  produk?: string;
  funding_paid?: number;
  interest_paid?: number;
  borrow_paid?: number;
  liq_loss?: number;
  n_liq?: number;
  n_long?: number;
  n_short?: number;
  max_lev_used?: number;
}
export interface TradeRow {
  entry_time: number;
  exit_time: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  fees: number;
  max_qty: number;
  side?: 'long' | 'short';
  roe_pct?: number;
  lev?: number;
  funding?: number;
  interest?: number;
  liquidated?: boolean;
}
export interface SummaryMsg {
  type: 'summary';
  mode: string;
  stats: Stats;
  curve: [number, number][];
  trades: TradeRow[];
  fills: Fill[];
  reveal: {
    symbol: string;
    name: string;
    market: string;
    mulai: string;
    selesai: string;
    zona: string;
    faktor_harga: number;
    harga_awal_asli: number;
    harga_akhir_asli: number;
  };
  currency: string;
  rank?: number | null;
  board?: BoardRow[];
}
export interface BoardRow {
  id: string;
  name: string;
  return_pct: number;
  n_trades: number;
  in_market: boolean;
  online: boolean;
  side?: 'long' | 'short' | null;
  n_liq?: number;
}

// ---------------------------------------------------------------- akun
export interface User {
  id: number;
  username: string;
}
const TOKEN_KEY = 'kilas-token';
const USER_KEY = 'kilas-user';

export function getToken(): string | null {
  return load<string | null>(TOKEN_KEY, null);
}
export function getUser(): User | null {
  return load<User | null>(USER_KEY, null);
}
export function setAuth(token: string | null, user: User | null): void {
  if (token && user) {
    save(TOKEN_KEY, token);
    save(USER_KEY, user);
  } else {
    remove(TOKEN_KEY);
    remove(USER_KEY);
  }
  window.dispatchEvent(new Event('kilas-auth'));
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(apiUrl(path), { ...opts, headers: { ...headers, ...(opts.headers as Record<string, string>) } });
  let body: any = null;
  try {
    body = await r.json();
  } catch {
    /* bukan JSON */
  }
  if (!r.ok) {
    if (r.status === 401 && token) setAuth(null, null);
    throw new Error(body?.detail || `Gagal (${r.status})`);
  }
  return body as T;
}

export const pasarApi = {
  katalog: () => req<Katalog>('api/pasar/katalog'),
  harian: () => req<any>('api/pasar/harian'),
  riwayat: () => req<any>('api/pasar/riwayat'),
  daftar: (username: string, password: string) =>
    req<{ user: User; token: string }>('api/akun/daftar', { method: 'POST', body: JSON.stringify({ username, password }) }),
  masuk: (username: string, password: string) =>
    req<{ user: User; token: string }>('api/akun/masuk', { method: 'POST', body: JSON.stringify({ username, password }) }),
  keluar: () => req<any>('api/akun/keluar', { method: 'POST' }),
  saya: () => req<any>('api/akun/saya'),
};

export interface LastSession {
  id: string;
  secret: string;
  label: string;
  mode: string;
}
export const LAST_KEY = 'kilas-last-session';
