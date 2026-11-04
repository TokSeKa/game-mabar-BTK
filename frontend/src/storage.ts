/** localStorage yang aman: tidak pernah melempar error (mode privat, storage diblokir, dll.). */
export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* abaikan */
  }
}

export function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* abaikan */
  }
}

export interface SavedBot {
  mode: 'blocks' | 'code';
  code: string;
  blocks: unknown | null;
}

export interface Session {
  code: string;
  player_id: string;
  token: string;
}

export const KEYS = {
  name: 'sba-name',
  bot: 'sba-bot',
  session: 'sba-session',
  practice: 'sba-practice',
};
