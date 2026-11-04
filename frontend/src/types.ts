export type Senjata = 'batu' | 'gunting' | 'kertas';

export interface MatchSettings {
  hp_awal: number;
  hp_kalah: number;
  ronde_maks: number;
  ingatan: number;
  /** mode event: normal | ganda | pikun | kilat | tipis | kabut | acak */
  event?: string;
}

export interface EventInfo {
  id: string;
  nama: string;
  ket: string;
  kejutan?: boolean;
}

export interface RatingChange {
  lama: number;
  baru: number;
  delta: number;
}

export interface PairData {
  win: Senjata;
  lose: Senjata;
  losers: { id: number; amt: number }[];
  pool: number;
  winners: number[];
  share: number;
  rem_ids: number[];
}

export interface RoundData {
  r: number;
  alive: number[];
  choices: (Senjata | null)[];
  groups: Record<Senjata, number[]>;
  counts: Record<Senjata, number>;
  pairs: PairData[];
  delta: number[];
  before: number[];
  after: number[];
  elim: number[];
}

export interface MatchPlayer {
  index: number;
  id: string;
  name: string;
  color: string;
}

export interface MatchData {
  id: string;
  settings: MatchSettings;
  players: MatchPlayer[];
  rounds: RoundData[];
  ranking: number[];
  winners: number[];
  reason: 'last_standing' | 'max_rounds';
  elim_round: Record<string, number>;
  final_hp: number[];
  event?: EventInfo | null;
  /** id pemain → perubahan rating liga (hanya pemain yang masuk akun) */
  ratings?: Record<string, RatingChange> | null;
}

export interface BotErrorInfo {
  baris: number | null;
  pesan: string;
}

export interface LogEntry {
  ronde: number;
  langkah?: number;
  pilihan?: Senjata;
  cetak?: string[];
  error?: BotErrorInfo;
  otomatis?: boolean;
  catatan?: string;
}

export interface PlayerPublic {
  id: string;
  name: string;
  color: string;
  ready: boolean;
  bot_ok: boolean;
  online: boolean;
  wins: number;
  matches: number;
  is_host: boolean;
  spectator?: boolean;
  akun?: string | null;
}

export interface RoomState {
  code: string;
  host_id: string;
  status: 'lobby' | 'running';
  settings: MatchSettings;
  match_count: number;
  players: PlayerPublic[];
  penonton?: { id: string; name: string; online: boolean }[];
  last_match_id: string | null;
  last_tournament_id?: string | null;
}

export interface TournamentRow {
  index: number;
  poin: number;
  menang: number;
  seri: number;
  kalah: number;
  selisih_hp: number;
}

export interface TournamentMatch {
  a: number;
  b: number;
  pemenang: number | null;
  hp: [number, number];
  ronde: number;
  alasan: string;
  match: MatchData;
}

export interface TournamentResult {
  type: 'tournament_result';
  id: string;
  players: MatchPlayer[];
  settings: MatchSettings;
  event: EventInfo | null;
  standings: TournamentRow[];
  matches: TournamentMatch[];
  ratings: Record<string, RatingChange> | null;
  baru?: boolean;
}

export interface TraceStep {
  baris: number;
  fungsi: string;
  vars: Record<string, string>;
  langkah: number;
  kembali?: string;
}

export interface DebugResult {
  ok: boolean;
  pilihan?: Senjata | null;
  error?: BotErrorInfo | null;
  cetak?: string[];
  langkah?: number;
  trace?: TraceStep[];
  jejak_penuh?: boolean;
  info?: { ronde: number; hp: Record<string, number>; riwayat: number; kabut: boolean };
}

export interface Template {
  id: string;
  nama: string;
  level: string;
  ket: string;
  kode: string;
}

export interface LibDoc {
  nama: string;
  jenis: string;
  tanda: string;
  ket: string;
}

export interface MatchResultMsg {
  match: MatchData;
  my_index?: number;
  my_log?: LogEntry[];
  revealed?: Record<string, string>;
  replay?: boolean;
}
