import type { BotErrorInfo, DebugResult, EventInfo, LibDoc, LogEntry, MatchData, MatchSettings, RoundData, Template } from './types';

/** URL relatif terhadap halaman, supaya app bisa dipasang di subdomain atau sub-path. */
export function apiUrl(path: string): string {
  return new URL(path.replace(/^\//, ''), document.baseURI).toString();
}

export function wsUrl(path = 'ws'): string {
  const u = new URL(path, document.baseURI);
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  return u.toString();
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(apiUrl(path));
  if (!r.ok) throw new Error(`Gagal memuat ${path} (${r.status})`);
  return r.json() as Promise<T>;
}

let templatesCache: Promise<Template[]> | null = null;
export function getTemplates(): Promise<Template[]> {
  templatesCache ??= getJson<Template[]>('api/templates').catch((e) => {
    templatesCache = null;
    throw e;
  });
  return templatesCache;
}

let libCache: Promise<{ fungsi: LibDoc[]; max_langkah: number }> | null = null;
export function getLibrary(): Promise<{ fungsi: LibDoc[]; max_langkah: number }> {
  libCache ??= getJson<{ fungsi: LibDoc[]; max_langkah: number }>('api/library').catch((e) => {
    libCache = null;
    throw e;
  });
  return libCache;
}

export async function getGuide(): Promise<string> {
  const r = await fetch(apiUrl('api/guide'));
  if (!r.ok) throw new Error('Panduan belum tersedia');
  return r.text();
}

export async function validateCode(code: string): Promise<{ ok: boolean; error: BotErrorInfo | null }> {
  const r = await fetch(apiUrl('api/validate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (!r.ok) throw new Error('Gagal mengecek kode');
  return r.json();
}

export type PracticeResult =
  | { ok: true; match: MatchData; my_index: number; my_log: LogEntry[] }
  | { ok: false; error: BotErrorInfo };

export async function runPractice(body: {
  code: string;
  nama: string;
  lawan: string[];
  settings: Partial<MatchSettings>;
}): Promise<PracticeResult> {
  const r = await fetch(apiUrl('api/practice'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (r.status === 429) throw new Error('Server sedang sibuk. Coba lagi sebentar lagi.');
  if (!r.ok) throw new Error('Gagal menjalankan latihan');
  return r.json();
}

let eventsCache: Promise<EventInfo[]> | null = null;
export function getEvents(): Promise<EventInfo[]> {
  eventsCache ??= getJson<EventInfo[]>('api/events').catch((e) => {
    eventsCache = null;
    throw e;
  });
  return eventsCache;
}

/** Jalankan ulang satu ronde dari replay dengan pencatat jejak (debugger langkah demi langkah). */
export async function runDebug(body: {
  code: string;
  settings: MatchSettings;
  names: string[];
  my_index: number;
  ronde: number;
  rounds: RoundData[];
}): Promise<DebugResult> {
  const r = await fetch(apiUrl('api/debug'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (r.status === 400) {
    const j = await r.json().catch(() => ({}));
    throw new Error(j.detail ?? 'Ronde itu tidak bisa di-debug');
  }
  if (!r.ok) throw new Error('Debugger gagal dijalankan');
  return r.json();
}
