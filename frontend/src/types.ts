export type Senjata = 'batu' | 'gunting' | 'kertas';

export interface MatchSettings {
  hp_awal: number;
  hp_kalah: number;
  ronde_maks: number;
  ingatan: number;
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
}

export interface RoomState {
  code: string;
  host_id: string;
  status: 'lobby' | 'running';
  settings: MatchSettings;
  match_count: number;
  players: PlayerPublic[];
  last_match_id: string | null;
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
