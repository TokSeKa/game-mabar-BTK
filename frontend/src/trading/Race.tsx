import { useEffect, useRef, useState } from 'react';
import { copyText } from '../util';
import { load, remove, save } from '../storage';
import { getUser, pasarApi, type BoardRow, type Katalog, type SessionInfo } from './api';
import { PasarConn } from './conn';
import { TradeScreen } from './TradeScreen';

interface Props {
  toast: (m: string, err?: boolean) => void;
  initialCode?: string;
}

interface Joined {
  code: string;
  player_id: string;
  token: string;
}
const RACE_KEY = 'kilas-race';

export function Race({ toast, initialCode = '' }: Props) {
  const [kat, setKat] = useState<Katalog | null>(null);
  const [name, setName] = useState(() => getUser()?.username ?? load<string>('sba-name', ''));
  const [code, setCode] = useState(initialCode);
  const [cfg, setCfg] = useState({ pasar: '', tf: '15m', langkah: 120, kecepatan: 2, buta: true, modal: 0, produk: 'spot', aturan: 'nyata' });
  const [state, setState] = useState<any>(null);
  const [board, setBoard] = useState<BoardRow[]>([]);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [joined, setJoined] = useState<Joined | null>(null);
  const [conn, setConn] = useState<PasarConn | null>(null);
  const connRef = useRef<PasarConn | null>(null);

  useEffect(() => {
    pasarApi.katalog().then(setKat).catch(() => setKat(null));
    const saved = load<Joined | null>(RACE_KEY, null);
    if (saved && (!initialCode || saved.code === initialCode)) open({ type: 'race_rejoin', ...saved }, true);
    return () => connRef.current?.close();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const open = (hello: Record<string, any>, quiet = false) => {
    connRef.current?.close();
    let j: Joined | null = null;
    const c = new PasarConn(() => (j ? { type: 'race_rejoin', ...j } : hello));
    c.on((m) => {
      switch (m.type) {
        case 'race_joined':
          j = { code: m.code, player_id: m.player_id, token: m.token };
          setJoined(j);
          save(RACE_KEY, j);
          try {
            history.replaceState(null, '', `#pasar-balap-${m.code}`);
          } catch {
            /* abaikan */
          }
          break;
        case 'race_state':
          setState(m);
          break;
        case 'race_board':
          setBoard(m.board);
          setState((s: any) => (s ? { ...s, step_n: m.step_n } : s));
          break;
        case 'session':
          setSession(m as SessionInfo);
          break;
        case 'race_left':
          leave();
          break;
        case 'error':
          if (!j) {
            if (!quiet) toast(m.message, true);
            remove(RACE_KEY);
            c.close();
            setConn(null);
          } else toast(m.message, true);
          break;
      }
    });
    connRef.current = c;
    setConn(c);
  };

  const leave = () => {
    connRef.current?.send({ type: 'race_leave' });
    connRef.current?.close();
    connRef.current = null;
    remove(RACE_KEY);
    setConn(null);
    setJoined(null);
    setState(null);
    setSession(null);
    setBoard([]);
  };

  const isHost = !!(state && joined && state.host_id === joined.player_id);

  if (session && conn && joined && state) {
    return (
      <TradeScreen key={session.start_time} conn={conn} session={session} toast={toast} onExit={leave}
        race={{ board, isHost, myId: joined.player_id, status: state.status, speed: state.speed, stepN: state.step_n, stepsTotal: state.steps_total }} />
    );
  }

  if (joined && state) {
    const link = `${location.origin}${location.pathname}#pasar-balap-${state.code}`;
    return (
      <div className="race-lobby">
        <div className="panel">
          <div className="row">
            <span className="hint">Kode room</span>
            <span className="room-code">{state.code}</span>
            <button className="btn small" type="button" onClick={async () => toast((await copyText(link)) ? 'Link tersalin.' : link)}>Salin link</button>
            <span className="spacer" />
            <button className="btn small danger" type="button" onClick={leave}>Keluar</button>
          </div>
          <p>
            Pasar <b>{state.pasar}</b> · {state.produk === 'futures' ? <b>Futures</b> : state.produk === 'margin' ? <b>Margin + short</b> : 'Spot'}{state.aturan === 'bebas' ? ' (aturan bebas)' : ''} · timeframe <b>{state.tf_label}</b> · {state.steps_total} candle · 1 candle tiap {state.speed} detik.
            Semua pemain melihat chart yang sama (aset rahasia) dan trading dengan modal masing-masing. Return tertinggi menang.
          </p>
          <ul className="players">
            {state.players.map((p: any) => (
              <li key={p.id} className={`${p.online ? '' : 'offline'} ${p.id === joined.player_id ? 'me' : ''}`}>
                <span className="pn">{p.name}{p.id === joined.player_id ? ' (kamu)' : ''}</span>
                <span className="tags">{p.is_host && <span className="tag-mini host">host</span>}</span>
              </li>
            ))}
          </ul>
          {isHost ? (
            <button className="btn primary big" type="button" disabled={state.status !== 'lobby'} onClick={() => conn?.send({ type: 'race_start' })}>
              Mulai balapan ({state.players.length} pemain)
            </button>
          ) : (
            <p className="hint">Menunggu host memulai…</p>
          )}
        </div>
      </div>
    );
  }

  const markets = kat ? Object.values(kat.pasar) : [];
  const spec = kat && cfg.pasar ? kat.spec[cfg.pasar] : null;
  const tfs = spec ? spec.tfs : ['1m', '5m', '15m', '1h', '4h', '1d'];
  return (
    <div className="setup-grid">
      <div className="panel">
        <h3>Buat room balapan</h3>
        <label className="field" htmlFor="r-name">Namamu<input id="r-name" className="input" maxLength={16} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field" htmlFor="r-pasar">
          Pasar
          <select id="r-pasar" value={cfg.pasar} onChange={(e) => setCfg({ ...cfg, pasar: e.target.value })}>
            <option value="">Acak</option>
            {markets.map((m) => <option key={m.id} value={m.id}>{m.nama}</option>)}
          </select>
        </label>
        <label className="field" htmlFor="r-prod">
          Produk
          <select id="r-prod" value={cfg.produk} onChange={(e) => setCfg({ ...cfg, produk: e.target.value })}>
            <option value="spot">Spot</option>
            <option value="futures">Futures (long/short + leverage)</option>
            <option value="margin">Margin + short (saham)</option>
          </select>
        </label>
        {cfg.produk !== 'spot' && (
          <>
            <label className="toggle" htmlFor="r-at"><input id="r-at" type="checkbox" checked={cfg.aturan === 'bebas'} onChange={(e) => setCfg({ ...cfg, aturan: e.target.checked ? 'bebas' : 'nyata' })} /> Aturan bebas (futures/short di semua saham)</label>
            <p className="hint">{cfg.produk === 'futures' ? 'Aturan asli: futures hanya kripto. Pasar acak akan memilih pasar yang mendukung.' : 'Margin hanya untuk saham. Di BEI short cuma untuk 5 saham daftar BEI kecuali aturan bebas.'}</p>
          </>
        )}
        <div className="fields">
          <label className="field" htmlFor="r-tf">Timeframe<select id="r-tf" value={cfg.tf} onChange={(e) => setCfg({ ...cfg, tf: e.target.value })}>{tfs.map((t) => <option key={t} value={t}>{kat?.tf_label[t] ?? t}</option>)}</select></label>
          <label className="field" htmlFor="r-n">Jumlah candle<input id="r-n" type="number" min={20} max={1000} value={cfg.langkah} onChange={(e) => setCfg({ ...cfg, langkah: Number(e.target.value) })} /></label>
          <label className="field" htmlFor="r-s">Detik per candle<input id="r-s" type="number" min={0.3} max={15} step={0.5} value={cfg.kecepatan} onChange={(e) => setCfg({ ...cfg, kecepatan: Number(e.target.value) })} /></label>
          <label className="field" htmlFor="r-m">Modal (kosong = default)<input id="r-m" type="number" min={0} value={cfg.modal || ''} onChange={(e) => setCfg({ ...cfg, modal: Number(e.target.value) })} /></label>
        </div>
        <label className="toggle" htmlFor="r-b"><input id="r-b" type="checkbox" checked={cfg.buta} onChange={(e) => setCfg({ ...cfg, buta: e.target.checked })} /> Mode buta (aset, tanggal, dan harga disamarkan)</label>
        <button className="btn primary big" type="button" disabled={!name.trim()}
          onClick={() => open({ type: 'race_create', name: name.trim(), config: { ...cfg, pasar: cfg.pasar || null, modal: cfg.modal || null } })}>
          Buat room
        </button>
      </div>
      <div className="panel">
        <h3>Gabung room</h3>
        <label className="field" htmlFor="r-name2">Namamu<input id="r-name2" className="input" maxLength={16} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field" htmlFor="r-code">Kode room<input id="r-code" className="input code-input" maxLength={5} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} /></label>
        <button className="btn big" type="button" disabled={!name.trim() || code.length !== 5} onClick={() => open({ type: 'race_join', code, name: name.trim() })}>Gabung</button>
        <p className="hint">Balapan: candle maju otomatis untuk semua pemain sekaligus. Tidak ada tombol maju, jadi kamu harus memutuskan dengan cepat.</p>
      </div>
    </div>
  );
}
