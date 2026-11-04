import type { BotErrorInfo, LibDoc, LogEntry, MatchData, MatchSettings, Template } from './types';

/** URL relatif terhadap halaman, supaya app bisa dipasang di subdomain atau sub-path. */
export function apiUrl(path: string): string {
  return new URL(path.replace(/^\//, ''), document.baseURI).toString();
}

export function wsUrl(): string {
  const u = new URL('ws', document.baseURI);
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
