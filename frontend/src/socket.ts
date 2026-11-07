import { wsUrl } from './api';

export type ConnStatus = 'connecting' | 'open' | 'reconnecting' | 'closed';

const PING_MS = 5_000;        // kirim ping sesering ini
const DIAM_MS = 15_000;       // tidak ada pesan selama ini = koneksi dianggap macet
const CEK_MS = 3_500;         // setelah kembali ke tab: tunggu pong selama ini

/**
 * WebSocket dengan sambung ulang otomatis. ``hello`` menentukan pesan pertama setiap kali tersambung.
 *
 * Di HP, koneksi sering "mati diam-diam" (layar mati, pindah aplikasi, sinyal hilang): browser masih menganggapnya
 * terbuka padahal tidak ada pesan yang lewat. Karena itu ada ping berkala + pengawas: kalau server diam terlalu lama,
 * atau tidak membalas ping saat tab kembali dibuka, koneksi diputus dan disambung ulang.
 */
export class RoomSocket {
  private ws: WebSocket | null = null;
  private stopped = false;
  private retry = 0;
  private reconnectTimer: number | undefined;
  private pingTimer: number | undefined;
  private lastRecv = 0;
  private listening = false;
  private readonly onWake = () => this.wake();

  constructor(
    private hello: () => object | null,
    private onMessage: (msg: Record<string, any>) => void,
    private onStatus: (s: ConnStatus) => void,
    private path = 'ws',
  ) {}

  connect(): void {
    this.stopped = false;
    window.clearTimeout(this.reconnectTimer);
    this.listen(true);
    this.onStatus(this.retry ? 'reconnecting' : 'connecting');
    const ws = new WebSocket(wsUrl(this.path));
    this.ws = ws;
    ws.onopen = () => {
      if (this.ws !== ws) return;
      this.retry = 0;
      this.lastRecv = Date.now();
      const first = this.hello();
      if (first) ws.send(JSON.stringify(first));
      ws.send(JSON.stringify({ type: 'ping', t: Date.now() }));
      this.onStatus('open');
      window.clearInterval(this.pingTimer);
      this.pingTimer = window.setInterval(() => {
        if (this.ws !== ws) return;
        if (Date.now() - this.lastRecv > DIAM_MS) {
          this.drop();
          return;
        }
        this.send({ type: 'ping', t: Date.now() });
      }, PING_MS);
    };
    ws.onmessage = (ev) => {
      if (this.ws !== ws) return;
      this.lastRecv = Date.now();
      try {
        this.onMessage(JSON.parse(ev.data));
      } catch {
        /* abaikan pesan rusak */
      }
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      window.clearInterval(this.pingTimer);
      this.ws = null;
      if (this.stopped) {
        this.onStatus('closed');
        return;
      }
      this.retry += 1;
      this.onStatus('reconnecting');
      const delay = Math.min(500 * 2 ** Math.min(this.retry - 1, 3), 4_000);
      this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
    };
  }

  /** True kalau pesan bisa dikirim sekarang. */
  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  send(msg: object): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(msg));
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }

  /** Putuskan koneksi yang tampak terbuka tapi macet, lalu langsung sambung ulang. */
  drop(): void {
    if (this.stopped) return;
    const ws = this.ws;
    this.ws = null;
    window.clearInterval(this.pingTimer);
    if (ws) {
      ws.onopen = ws.onmessage = ws.onclose = null;
      try {
        ws.close();
      } catch {
        /* abaikan */
      }
    }
    this.retry = Math.max(this.retry, 1);
    this.connect();
  }

  /** Dipanggil saat tab kembali terlihat / jaringan kembali: pastikan koneksi benar-benar hidup. */
  wake(): void {
    if (this.stopped || document.visibilityState === 'hidden') return;
    const ws = this.ws;
    if (!ws) {
      this.connect();
      return;
    }
    if (ws.readyState !== WebSocket.OPEN) return;
    const sent = Date.now();
    this.send({ type: 'ping', t: sent });
    window.setTimeout(() => {
      if (this.ws === ws && this.lastRecv < sent) this.drop();
    }, CEK_MS);
  }

  close(): void {
    this.stopped = true;
    this.listen(false);
    window.clearTimeout(this.reconnectTimer);
    window.clearInterval(this.pingTimer);
    this.ws?.close();
    this.ws = null;
  }

  private listen(on: boolean): void {
    if (on === this.listening) return;
    this.listening = on;
    const f = on ? window.addEventListener : window.removeEventListener;
    f.call(window, 'online', this.onWake);
    f.call(window, 'focus', this.onWake);
    f.call(window, 'pageshow', this.onWake);
    (on ? document.addEventListener : document.removeEventListener).call(document, 'visibilitychange', this.onWake);
  }
}
