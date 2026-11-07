/** Pemberitahuan giliran untuk pemain di HP: getar, bunyi pendek, dan judul tab berkedip. */
import { load, save } from '../storage';

const KEY = 'mabar-notif';
let ctx: AudioContext | null = null;
let titleTimer: number | undefined;
let baseTitle = '';

export const alertsEnabled = () => load<boolean>(KEY, true);
export const setAlertsEnabled = (on: boolean) => save(KEY, on);

/** Browser hanya mengizinkan suara setelah ada sentuhan/klik: panggil dari handler interaksi. */
export function unlockAudio(): void {
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return;
    ctx ??= new AC();
    if (ctx.state === 'suspended') void ctx.resume();
  } catch {
    ctx = null;
  }
}

export function beep(freq = 880, ms = 140, times = 1): void {
  if (!ctx || ctx.state !== 'running') return;
  try {
    for (let k = 0; k < times; k++) {
      const t0 = ctx.currentTime + k * (ms / 1000 + 0.08);
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(0.18, t0 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + ms / 1000);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t0);
      osc.stop(t0 + ms / 1000 + 0.02);
    }
  } catch {
    /* abaikan */
  }
}

export function buzz(pattern: number | number[]): void {
  try {
    navigator.vibrate?.(pattern);
  } catch {
    /* abaikan */
  }
}

export function flashTitle(text: string): void {
  if (titleTimer !== undefined) return;
  baseTitle = document.title;
  let on = false;
  titleTimer = window.setInterval(() => {
    document.title = on ? baseTitle : text;
    on = !on;
  }, 800);
}

export function stopFlash(): void {
  if (titleTimer === undefined) return;
  window.clearInterval(titleTimer);
  titleTimer = undefined;
  document.title = baseTitle;
}
