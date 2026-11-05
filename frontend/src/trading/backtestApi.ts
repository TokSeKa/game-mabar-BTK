import { apiUrl } from '../api';

export interface StrategiMeta {
  file: string;
  nama: string;
  judul?: string;
  nama_tampil?: string;
  deskripsi: string;
  pengaturan: Record<string, any>;
  parameter: Record<string, any>;
  plot: string[];
  error: string | null;
}
export interface PengumpulStatus {
  folder: string;
  ada: boolean;
  yahoo: Record<string, string[]>;
  idx_saham: number;
  idx_broker: number;
  tick: string[];
}
export interface JobStatus {
  id: string;
  strategi: string;
  status: 'jalan' | 'selesai' | 'gagal' | 'batal';
  progres: number;
  pesan: string;
  error: string | null;
  durasi: number;
}
export interface Ringkasan {
  return_pct: number | null;
  buy_hold_pct: number | null;
  cagr_pct: number | null;
  max_dd_pct: number | null;
  dd_terlama_hari: number | null;
  sharpe: number | null;
  sortino: number | null;
  calmar: number | null;
  volatilitas_pct: number | null;
  equity: number | null;
  modal: number;
  n_trades: number;
  n_long: number;
  n_short: number;
  win_rate: number | null;
  profit_factor: number | null;
  rata_pct: number | null;
  rata_untung_pct: number | null;
  rata_rugi_pct: number | null;
  terbaik_pct: number | null;
  terburuk_pct: number | null;
  ekspektasi: number | null;
  rata_tahan_jam: number | null;
  exposure_pct: number | null;
  fees: number;
  funding: number;
  bunga: number;
  biaya_pinjam: number;
  n_likuidasi: number;
  median_return_pct?: number | null;
  aset_untung_pct?: number | null;
}
export interface Trade {
  sym: string;
  side: 'long' | 'short';
  entry_time: number;
  exit_time: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  roe_pct: number;
  lev: number;
  fees: number;
  funding: number;
  liquidated: boolean;
}
export interface PerAset {
  simbol: string;
  nama: string;
  return_pct?: number | null;
  buy_hold_pct: number | null;
  max_dd_pct?: number | null;
  sharpe?: number | null;
  cagr_pct?: number | null;
  n_trades: number;
  win_rate: number | null;
  profit_factor: number | null;
  fees: number;
  laba?: number;
  n_likuidasi?: number;
}
export interface Hasil {
  id: string;
  strategi: string;
  judul: string;
  deskripsi: string;
  dibuat: string;
  durasi_detik: number;
  pengaturan: Record<string, any>;
  parameter: Record<string, any>;
  plot: string[];
  mode: 'per_aset' | 'portofolio';
  pasar: string;
  pasar_nama: string;
  currency: string;
  timeframe: string;
  aset: string[];
  peringatan: string[];
  ringkasan: Ringkasan;
  kurva: [number, number, number][];
  bulanan: { bulan: string; return_pct: number | null }[];
  per_aset: PerAset[];
  transaksi: Trade[];
  n_transaksi: number;
  log: string[];
}
export interface AsetChart {
  simbol: string;
  t: number[];
  o: (number | null)[];
  h: (number | null)[];
  l: (number | null)[];
  c: (number | null)[];
  v: (number | null)[];
  mulai: number;
  plot: Record<string, (number | null)[]>;
  fills: { id: number; time: number; side: 'buy' | 'sell'; qty: number; price: number; label: string; fee: number; pnl: number | null }[];
  trades: Trade[];
}
export interface RiwayatRow {
  id: string;
  strategi: string;
  judul: string;
  dibuat: string;
  mode: string;
  pasar_nama: string;
  timeframe: string;
  n_aset: number;
  produk: string;
  return_pct: number | null;
  buy_hold_pct: number | null;
  max_dd_pct: number | null;
  sharpe: number | null;
  n_trades: number;
  parameter: Record<string, any>;
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const r = await fetch(apiUrl(path), { ...opts, headers: { 'Content-Type': 'application/json' } });
  let body: any = null;
  try {
    body = await r.json();
  } catch {
    /* bukan JSON */
  }
  if (!r.ok) throw new Error(body?.detail || `Gagal (${r.status})`);
  return body as T;
}

export const btApi = {
  strategi: () => req<{ folder: string; strategi: StrategiMeta[]; pengumpul: PengumpulStatus }>('api/backtest/strategi'),
  jalankan: (strategi: string, pengaturan: Record<string, any>, parameter: Record<string, any>) =>
    req<JobStatus>('api/backtest/jalankan', { method: 'POST', body: JSON.stringify({ strategi, pengaturan, parameter }) }),
  job: (id: string) => req<JobStatus>(`api/backtest/job/${id}`),
  batal: (id: string) => req<JobStatus>(`api/backtest/job/${id}/batal`, { method: 'POST' }),
  riwayat: () => req<{ hasil: RiwayatRow[]; berjalan: JobStatus[] }>('api/backtest/hasil'),
  hasil: (id: string) => req<Hasil>(`api/backtest/hasil/${id}`),
  aset: (id: string, sym: string) => req<AsetChart>(`api/backtest/hasil/${id}/aset/${encodeURIComponent(sym)}`),
  hapus: (id: string) => req<{ ok: boolean }>(`api/backtest/hasil/${id}`, { method: 'DELETE' }),
};
