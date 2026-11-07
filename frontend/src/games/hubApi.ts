import { apiUrl } from '../api';
import { load, remove, save } from '../storage';
import type { BotErrorInfo, LibDoc } from '../types';

export interface SettingMeta {
  id: string;
  label: string;
  jenis: 'int' | 'float' | 'bool' | 'pilihan';
  default: number | boolean | string;
  min: number | null;
  max: number | null;
  pilihan: [string, string][] | null;
  ket: string;
  grup: 'dasar' | 'informasi' | 'aturan' | 'kejutan';
  /** tampil hanya kalau setting lain bernilai ini (nilai atau list nilai) */
  jika: Record<string, any> | null;
}

export interface PresetMeta {
  id: string;
  nama: string;
  ket: string;
  nilai: Record<string, any>;
}

export interface TemplateMeta {
  id: string;
  nama: string;
  ket: string;
  kode: string;
}

export interface GameMeta {
  id: string;
  nama: string;
  ringkas: string;
  kategori: 'simultan' | 'giliran' | 'tick' | 'mandiri';
  min_pemain: number;
  max_pemain: number;
  fungsi_bot: string;
  timer: number;
  mandiri: boolean;
  settings: SettingMeta[];
  templates: TemplateMeta[];
  lib_docs: LibDoc[];
  label_skor: string;
  aturan: string;
  format_aksi: string;
  /** jenis event akhir ronde; kosong = game ini tidak memakai jeda lihat hasil */
  jeda_pada: string[];
  /** detik bawaan jeda lihat hasil */
  jeda_hasil: number;
  presets: PresetMeta[];
}

export interface SeatInfo {
  id: string;
  name: string;
  kind: 'manusia' | 'bot';
  label: string;
  /** kursi milik pemain sendiri (bukan bot tambahan) */
  self: boolean;
  owner: string;
  owner_name: string;
  online: boolean;
}

export interface LobbyMsg {
  type: 'room';
  kode: string;
  game: string;
  nama_game: string;
  host_id: string;
  status: 'lobby' | 'main' | 'selesai';
  settings: Record<string, any>;
  waktu: number;
  jeda: number;
  jeda_hasil: number;
  penonton_semua: boolean;
  dijeda: boolean;
  sesi: SesiRow[];
  min: number;
  max: number;
  match_no: number;
  kursi: SeatInfo[];
  penonton: string[];
  anggota: { id: string; name: string; online: boolean }[];
}

export interface SesiRow {
  nama: string;
  main: number;
  juara: number;
  poin: number;
}

export interface ResultData {
  ranking: number[];
  skor: number[];
  label_skor: string;
  pemenang: number;
}

export interface Frame {
  step: number;
  view: any;
  events: any[];
}

export interface HubLogEntry {
  langkah: number;
  steps?: number;
  cetak?: string[];
  error?: BotErrorInfo;
  catatan?: string;
}

export interface FinalMsg {
  type: 'selesai';
  result: ResultData;
  reveal: any;
  names: string[];
  kinds: ('manusia' | 'bot')[];
  ratings: Record<string, { lama: number; baru: number; delta: number }> | null;
  frames: Frame[];
  logs: Record<string, HubLogEntry[]>;
  ulang?: boolean;
  /** untuk memutar ulang dari sudut pandang satu pemain (lihat fetchSudut) */
  replay_id?: string | null;
}

export interface UpdateMsg {
  type: 'update';
  view: any;
  seat: number | null;
  pending: number[];
  acted: number[];
  my_turn: boolean;
  deadline: number;
  now: number;
  step: number;
  events: any[];
  /** sedang jeda lihat hasil ronde (null = tidak) */
  jeda: { sampai: number; siap: number[]; lama: number } | null;
  /** waktu server saat host menjeda match (null = tidak dijeda) */
  dijeda_sejak: number | null;
  /** mode mandiri: nomor langkah kursiku (dikirim balik bersama aksi) */
  versi: number | null;
}

export interface HubSession {
  kode: string;
  member_id: string;
  token: string;
}

export const HUB_KEYS = {
  nama: 'mabar-nama',
  sesi: 'mabar-sesi',
  bot: (gid: string) => `mabar-bot-${gid}`,
};

export const loadSession = () => load<HubSession | null>(HUB_KEYS.sesi, null);
export const saveSession = (s: HubSession) => save(HUB_KEYS.sesi, s);
export const clearSession = () => remove(HUB_KEYS.sesi);

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(apiUrl(path));
  if (!r.ok) throw new Error(`Gagal memuat (${r.status})`);
  return r.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (r.status === 429) throw new Error('Server sedang sibuk. Coba lagi sebentar lagi.');
  if (!r.ok) throw new Error(`Permintaan gagal (${r.status})`);
  return r.json() as Promise<T>;
}

let gamesCache: Promise<GameMeta[]> | null = null;
export function getGames(): Promise<GameMeta[]> {
  gamesCache ??= getJson<GameMeta[]>('api/main/games').catch((e) => {
    gamesCache = null;
    throw e;
  });
  return gamesCache;
}

const guideCache = new Map<string, Promise<string>>();
export function getPanduan(gid: string): Promise<string> {
  let p = guideCache.get(gid);
  if (!p) {
    p = fetch(apiUrl(`api/main/panduan/${gid}`)).then((r) => {
      if (!r.ok) throw new Error('Panduan tidak ditemukan');
      return r.text();
    });
    p.catch(() => guideCache.delete(gid));
    guideCache.set(gid, p);
  }
  return p;
}

export function validasi(game: string, kode: string) {
  return postJson<{ ok: boolean; error: BotErrorInfo | null }>('api/main/validasi', { game, kode });
}

export type LatihanResult =
  | { ok: true; result: ResultData; frames: Frame[]; log: HubLogEntry[]; names: string[]; reveal: any; settings: Record<string, any>; replay_id?: string }
  | { ok: false; error: BotErrorInfo };

export function latihan(body: { game: string; kode: string; nama: string; lawan: string[]; settings: Record<string, any> }) {
  return postJson<LatihanResult>('api/main/latihan', body);
}

/** Replay match yang sudah selesai dari sudut pandang satu kursi (-1 = penonton). */
export function fetchSudut(rid: string, kursi: number) {
  return getJson<{ kursi: number; frames: Frame[] }>(`api/main/sudut/${encodeURIComponent(rid)}?kursi=${kursi}`);
}

export interface LigaRow {
  rank: number;
  username: string;
  rating: number;
  games: number;
  wins: number;
}

export function getLiga(gid: string) {
  return getJson<{ game: string; board: LigaRow[] }>(`api/main/liga/${gid}`);
}

export const KATEGORI_LABEL: Record<GameMeta['kategori'], string> = {
  simultan: 'Bersamaan',
  giliran: 'Bergiliran',
  tick: 'Real-time',
  mandiri: 'Balapan sendiri-sendiri',
};

/** Warna tetap untuk kursi ke-i (dipakai semua renderer). */
export const SEAT_COLORS = ['#f0a24a', '#3fd0c9', '#f37aa5', '#7aa2ff', '#6be38a', '#ffd166', '#c29bff', '#ff8a5c',
  '#5ee0f0', '#e0a0ff', '#a0e060', '#ff6a9a'];
export const seatColor = (i: number) => SEAT_COLORS[((i % SEAT_COLORS.length) + SEAT_COLORS.length) % SEAT_COLORS.length];

export function fmt(n: number, digits = 0): string {
  if (!Number.isFinite(n)) return '–';
  return n.toLocaleString('id-ID', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function rupiah(n: number): string {
  return `Rp${Math.round(n).toLocaleString('id-ID')}`;
}
