import { wsUrl } from './api';

export type ConnStatus = 'connecting' | 'open' | 'reconnecting' | 'closed';

/** WebSocket dengan sambung ulang otomatis. ``hello`` menentukan pesan pertama setiap kali tersambung. */
export class RoomSocket {
  private ws: WebSocket | null = null;
  private stopped = false;
  private retry = 0;
  private reconnectTimer: number | undefined;
  private pingTimer: number | undefined;

  constructor(
    private hello: () => object | null,
    private onMessage: (msg: Record<string, any>) => void,
    private onStatus: (s: ConnStatus) => void,
    private path = 'ws',
  ) {}

  connect(): void {
    this.stopped = false;
    this.onStatus(this.retry ? 'reconnecting' : 'connecting');
    const ws = new WebSocket(wsUrl(this.path));
    this.ws = ws;
    ws.onopen = () => {
      this.retry = 0;
      const first = this.hello();
      if (first) ws.send(JSON.stringify(first));
      this.onStatus('open');
      window.clearInterval(this.pingTimer);
      this.pingTimer = window.setInterval(() => this.send({ type: 'ping' }), 25_000);
    };
    ws.onmessage = (ev) => {
      try {
        this.onMessage(JSON.parse(ev.data));
      } catch {
        /* abaikan pesan rusak */
      }
    };
    ws.onclose = () => {
      window.clearInterval(this.pingTimer);
      if (this.ws !== ws) return;
      this.ws = null;
      if (this.stopped) {
        this.onStatus('closed');
        return;
      }
      this.retry += 1;
      this.onStatus('reconnecting');
      const delay = Math.min(1000 * 2 ** Math.min(this.retry - 1, 4), 15_000);
      this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
    };
  }

  send(msg: object): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
      return true;
    }
    return false;
  }

  close(): void {
    this.stopped = true;
    window.clearTimeout(this.reconnectTimer);
    window.clearInterval(this.pingTimer);
    this.ws?.close();
    this.ws = null;
  }
}
