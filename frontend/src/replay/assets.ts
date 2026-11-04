import type { Senjata } from '../types';

export const SENJATA: Senjata[] = ['batu', 'gunting', 'kertas'];
export const BEATS: Record<Senjata, Senjata> = { batu: 'gunting', gunting: 'kertas', kertas: 'batu' };
export const LABEL: Record<Senjata, string> = { batu: 'Batu', gunting: 'Gunting', kertas: 'Kertas' };

export const ICON: Record<Senjata, string> = {
  batu: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M9 31 L13 17 L24 9 L37 14 L41 28 L34 39 L16 40 Z" fill="var(--batu)"/><path d="M13 17 L22 22 L24 9 M22 22 L34 26 L37 14 M34 26 L34 39 M22 22 L16 40" stroke="var(--batu-d)" stroke-width="2" fill="none" stroke-linejoin="round"/></svg>',
  gunting: '<svg viewBox="0 0 48 48" aria-hidden="true"><g stroke="var(--gunting)" stroke-width="4" stroke-linecap="round" fill="none"><path d="M20 30 L33 7"/><path d="M28 30 L15 7"/><circle cx="16" cy="36" r="6"/><circle cx="32" cy="36" r="6"/></g><circle cx="24" cy="23" r="2.6" fill="var(--gunting-d)"/></svg>',
  kertas: '<svg viewBox="0 0 48 48" aria-hidden="true"><g transform="rotate(-6 24 24)"><path d="M13 7 H30 L37 14 V41 H13 Z" fill="var(--kertas)"/><path d="M30 7 V14 H37 Z" fill="var(--kertas-d)"/><path d="M18 21 H32 M18 27 H32 M18 33 H27" stroke="var(--kertas-d)" stroke-width="2.4" stroke-linecap="round"/></g></svg>',
};

/** Versi ikon dengan warna literal, untuk dipakai sebagai gambar (data URI) di Blockly. */
const RAW_COLORS: Record<string, string> = {
  'var(--batu)': '#f0a24a', 'var(--batu-d)': '#a8641f',
  'var(--gunting)': '#3fd0c9', 'var(--gunting-d)': '#1d8a85',
  'var(--kertas)': '#f37aa5', 'var(--kertas-d)': '#b03f6a',
};
export function iconDataUri(s: Senjata): string {
  let svg = ICON[s].replace(/<svg [^>]*>/, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect x="1" y="1" width="46" height="46" rx="12" fill="#f3efff"/>');
  for (const [k, v] of Object.entries(RAW_COLORS)) svg = svg.split(k).join(v);
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

export const ROBOT =
  '<svg viewBox="0 0 64 64" class="robot" aria-hidden="true"><line class="ant" x1="32" y1="5" x2="32" y2="14" stroke-width="3"/><circle class="light" cx="32" cy="5" r="4"/><rect class="head" x="4" y="28" width="6" height="13" rx="3"/><rect class="head" x="54" y="28" width="6" height="13" rx="3"/><rect class="head" x="8" y="13" width="48" height="43" rx="14"/><rect class="scr" x="15" y="22" width="34" height="22" rx="8"/><g class="eyes"><rect x="21" y="28" width="7" height="10" rx="3.5"/><rect x="36" y="28" width="7" height="10" rx="3.5"/></g><g class="xeyes"><path d="M21 28 l7 9 M28 28 l-7 9 M36 28 l7 9 M43 28 l-7 9"/></g></svg>';

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}
