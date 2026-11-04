import { RoomSocket, type ConnStatus } from '../socket';
import { getToken } from './api';

type Msg = Record<string, any>;

/** Koneksi WebSocket Kilas Pasar dengan banyak pendengar dan pesan pembuka yang bisa diganti. */
export class PasarConn {
  private sock: RoomSocket;
  private listeners = new Set<(m: Msg) => void>();
  private statusListeners = new Set<(s: ConnStatus) => void>();
  status: ConnStatus = 'connecting';
  hello: () => Msg | null;
  /** pesan terakhir per jenis, supaya komponen yang baru dipasang tidak ketinggalan keadaan */
  last = new Map<string, Msg>();

  constructor(hello: () => Msg | null) {
    this.hello = hello;
    this.sock = new RoomSocket(
      () => {
        const h = this.hello();
        if (!h) return null;
        const token = getToken();
        return token ? { ...h, token } : h;
      },
      (m) => {
        if (typeof m.type === 'string') this.last.set(m.type, m);
        this.listeners.forEach((f) => f(m));
      },
      (s) => {
        this.status = s;
        this.statusListeners.forEach((f) => f(s));
      },
      'ws/pasar',
    );
    this.sock.connect();
  }

  send(m: Msg): boolean {
    return this.sock.send(m);
  }

  on(fn: (m: Msg) => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  onStatus(fn: (s: ConnStatus) => void): () => void {
    this.statusListeners.add(fn);
    return () => this.statusListeners.delete(fn);
  }

  close(): void {
    this.listeners.clear();
    this.statusListeners.clear();
    this.sock.close();
  }
}
