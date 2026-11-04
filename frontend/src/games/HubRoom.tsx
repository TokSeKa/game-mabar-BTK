import { useEffect, useMemo, useRef, useState } from 'react';
import { RoomSocket, type ConnStatus } from '../socket';
import { getToken } from '../trading/api';
import { copyText } from '../util';
import { FrameReplay } from './FrameReplay';
import { HubBotLog, HubBotPanel, loadBotCode } from './HubBotPanel';
import {
  clearSession, fmt, saveSession, seatColor,
  type FinalMsg, type GameMeta, type HubSession, type LobbyMsg, type SeatInfo, type UpdateMsg,
} from './hubApi';
import { describeEvent, rendererFor } from './renderers';
import { Reveal } from './Reveal';
import { SettingsForm, SettingsSummary } from './SettingsForm';

export type HubEntry =
  | { action: 'buat'; game: string; nama: string; settings: Record<string, any>; waktu: number; jeda: number }
  | { action: 'gabung'; kode: string; nama: string; tonton: boolean }
  | { action: 'kembali'; session: HubSession };

const EMOJI = ['👏', '😂', '😮', '🔥', '😭', '🤝', '💀', '🎉'];

interface StartInfo {
  instan: boolean;
  names: string[];
  seat?: number | null;
  main_sendiri?: boolean;
}

interface Props {
  entry: HubEntry;
  games: Record<string, GameMeta>;
  toast: (m: string, err?: boolean) => void;
  onExit: (message?: string) => void;
}

export function HubRoom({ entry, games, toast, onExit }: Props) {
  const [status, setStatus] = useState<ConnStatus>('connecting');
  const [lobby, setLobby] = useState<LobbyMsg | null>(null);
  const [me, setMe] = useState<string | null>(entry.action === 'kembali' ? entry.session.member_id : null);
  const [start, setStart] = useState<StartInfo | null>(null);
  const [upd, setUpd] = useState<UpdateMsg | null>(null);
  const [actedStep, setActedStep] = useState(-1);
  const [done, setDone] = useState<{ step: number; seats: number[] }>({ step: -1, seats: [] });
  const [log, setLog] = useState<string[]>([]);
  const [final, setFinal] = useState<FinalMsg | null>(null);
  const [showFinal, setShowFinal] = useState(false);
  const [reacts, setReacts] = useState<{ id: number; nama: string; emoji: string; x: number }[]>([]);
  const sock = useRef<RoomSocket | null>(null);
  const sess = useRef<HubSession | null>(entry.action === 'kembali' ? entry.session : null);
  const offset = useRef(0);
  const exitRef = useRef(onExit);
  exitRef.current = onExit;
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const mandiriRef = useRef(false);

  useEffect(() => {
    const hello = () => {
      const token = getToken();
      const s = sess.current;
      if (s) return { type: 'kembali', kode: s.kode, member_id: s.member_id, token_anggota: s.token, token };
      if (entry.action === 'buat') {
        return { type: 'buat', game: entry.game, nama: entry.nama, settings: entry.settings, waktu: entry.waktu, jeda: entry.jeda, token };
      }
      if (entry.action === 'gabung') return { type: 'gabung', kode: entry.kode, nama: entry.nama, tonton: entry.tonton, token };
      return null;
    };
    const leave = (msg?: string) => {
      sock.current?.close();
      exitRef.current(msg);
    };
    const onMsg = (m: Record<string, any>) => {
      switch (m.type) {
        case 'masuk': {
          const s = { kode: m.kode, member_id: m.member_id, token: m.token };
          sess.current = s;
          saveSession(s);
          setMe(m.member_id);
          try {
            history.replaceState(null, '', `#main-room-${m.kode}`);
          } catch {
            /* abaikan */
          }
          break;
        }
        case 'room':
          setLobby(m as LobbyMsg);
          break;
        case 'mulai':
          setStart(m as StartInfo);
          setUpd(null);
          setLog([]);
          setShowFinal(false);
          setActedStep(-1);
          break;
        case 'update': {
          const u = m as UpdateMsg;
          offset.current = Date.now() / 1000 - u.now;
          setUpd(u);
          if (mandiriRef.current) setActedStep(-1);
          const lines = (u.events ?? []).map(describeEvent).filter(Boolean) as string[];
          if (lines.length) setLog((prev) => [...lines.reverse(), ...prev].slice(0, 80));
          break;
        }
        case 'aksi_ok':
          setActedStep(m.step);
          break;
        case 'sudah':
          setDone((d) => (d.step === m.step ? { step: d.step, seats: [...d.seats, m.kursi] } : { step: m.step, seats: [m.kursi] }));
          break;
        case 'reaksi': {
          const id = Date.now() + Math.random();
          setReacts((r) => [...r.slice(-14), { id, nama: m.nama, emoji: m.emoji, x: 8 + Math.random() * 84 }]);
          window.setTimeout(() => setReacts((r) => r.filter((x) => x.id !== id)), 3200);
          break;
        }
        case 'selesai':
          setFinal(m as FinalMsg);
          setShowFinal(true);
          setStart(null);
          break;
        case 'error':
          if (m.for === 'kembali') {
            clearSession();
            sess.current = null;
            leave(m.message);
            return;
          }
          if ((m.for === 'buat' || m.for === 'gabung') && !sess.current) {
            leave(m.message);
            return;
          }
          if (m.for === 'aksi') setActedStep(-1);
          toastRef.current(m.message, true);
          break;
        case 'keluar_ok':
          clearSession();
          sess.current = null;
          leave();
          break;
        default:
          break;
      }
    };
    const s = new RoomSocket(hello, onMsg, setStatus, 'ws/main');
    sock.current = s;
    s.connect();
    return () => s.close();
    // entry tetap selama komponen hidup
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = (msg: object) => {
    if (!sock.current?.send({ ...msg, token: getToken() })) toast('Koneksi terputus, mencoba menyambung lagi…', true);
  };

  const meta = lobby ? games[lobby.game] : undefined;
  mandiriRef.current = !!meta?.mandiri;
  if (!lobby || !meta) {
    return (
      <div className="panel">
        <div className="row"><div className="spinner" /> <span>{status === 'reconnecting' ? 'Menyambung ulang…' : 'Masuk ke room…'}</span></div>
        <div className="row"><button type="button" className="btn small" onClick={() => { sock.current?.close(); onExit(); }}>Batal</button></div>
      </div>
    );
  }

  const phase = showFinal && final ? 'hasil' : lobby.status === 'main' ? 'main' : 'lobby';
  const invite = `${location.origin}${location.pathname}#main-room-${lobby.kode}`;
  return (
    <div className="hub-room">
      <div className="hub-head panel">
        <div className="row">
          <b className="rh-game">{meta.nama}</b>
          <span className="room-code" aria-label="Kode room">{lobby.kode}</span>
          <button type="button" className="btn small" onClick={async () => toast((await copyText(invite)) ? 'Link undangan tersalin.' : invite)}>Salin link undangan</button>
          <span className={`status-pill ${status === 'open' ? 'ok' : 'warn'}`}>{status === 'open' ? 'tersambung' : 'menyambung…'}</span>
          <span className="spacer" />
          <div className="react-bar" role="group" aria-label="Kirim reaksi">
            {EMOJI.map((e) => <button key={e} type="button" onClick={() => send({ type: 'reaksi', emoji: e })} aria-label={`Reaksi ${e}`}>{e}</button>)}
          </div>
          <button type="button" className="btn small danger" onClick={() => {
            if (lobby.status === 'main' && !window.confirm('Match sedang berjalan. Keluar sekarang? Kursimu akan memakai aksi bawaan.')) return;
            if (!sock.current?.send({ type: 'keluar' })) {
              clearSession();
              onExit();
            }
          }}>Keluar</button>
        </div>
      </div>

      {phase === 'lobby' && <Lobby lobby={lobby} meta={meta} me={me} send={send} />}
      {phase === 'main' && (
        <Live lobby={lobby} meta={meta} start={start} upd={upd} log={log} actedStep={actedStep} done={done} offset={offset.current}
          act={(a) => {
            if (!upd) return;
            setActedStep(upd.step);
            send({ type: 'aksi', aksi: a });
          }} />
      )}
      {phase === 'hasil' && final && <Results final={final} meta={meta} lobby={lobby} me={me} onBack={() => setShowFinal(false)} />}

      <div className="react-layer" aria-live="polite">
        {reacts.map((r) => <div key={r.id} className="react-float" style={{ left: `${r.x}%` }}><span>{r.emoji}</span><small>{r.nama}</small></div>)}
      </div>
    </div>
  );
}

/* ================================================================== lobby */
function SeatRow({ s, i, lobby, me, onRemove }: { s: SeatInfo; i: number; lobby: LobbyMsg; me: string | null; onRemove?: () => void }) {
  return (
    <li className={`${s.online ? '' : 'offline'} ${s.owner === me ? 'me' : ''}`}>
      <span className="seat-dot" style={{ background: seatColor(i) }}>{s.kind === 'bot' ? '🤖' : '🙂'}</span>
      <span className="pn">
        {s.name}
        <small>{s.kind === 'bot' ? `Bot · ${s.label}${s.self ? '' : ` · milik ${s.owner_name}`}` : 'Manusia'}{!s.online ? ' · offline' : ''}</small>
      </span>
      <span className="tags">
        {s.owner === lobby.host_id && s.self && <span className="tag-mini host">host</span>}
        {onRemove && <button type="button" className="btn small" onClick={onRemove} aria-label={`Hapus ${s.name}`}>✕</button>}
      </span>
    </li>
  );
}

function Lobby({ lobby, meta, me, send }: { lobby: LobbyMsg; meta: GameMeta; me: string | null; send: (m: object) => void }) {
  const isHost = lobby.host_id === me;
  const mySeat = lobby.kursi.find((k) => k.owner === me && k.self) ?? null;
  const [code, setCode] = useState(() => loadBotCode(meta));
  const [cfg, setCfg] = useState<Record<string, any>>(lobby.settings);
  const [waktu, setWaktu] = useState(lobby.waktu);
  const [jeda, setJeda] = useState(lobby.jeda);
  const [botName, setBotName] = useState('');
  const [tpl, setTpl] = useState<string>('__kode__');
  const [editor, setEditor] = useState(false);
  const dirty = JSON.stringify(cfg) !== JSON.stringify(lobby.settings) || waktu !== lobby.waktu || jeda !== lobby.jeda;

  useEffect(() => {
    if (!dirty) {
      setCfg(lobby.settings);
      setWaktu(lobby.waktu);
      setJeda(lobby.jeda);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lobby.settings, lobby.waktu, lobby.jeda]);

  const full = lobby.kursi.length >= lobby.max;
  const allBots = lobby.kursi.length > 0 && lobby.kursi.every((k) => k.kind === 'bot');
  const nextBotName = () => {
    const used = new Set(lobby.kursi.map((k) => k.name.toLowerCase()));
    for (let n = 1; n < 99; n++) if (!used.has(`bot ${n}`)) return `Bot ${n}`;
    return 'Bot';
  };
  const addBot = () => {
    const t = meta.templates.find((x) => x.id === tpl);
    send({ type: 'tambah_bot', nama: botName.trim() || (t ? t.nama.slice(0, 16) : nextBotName()), kode: t ? t.kode : code, label: t ? t.nama : 'Kode sendiri' });
    setBotName('');
  };

  return (
    <div className="room-grid">
      <div className="lobby-side">
        <div className="panel">
          <h3>Kursi ({lobby.kursi.length}/{lobby.max})</h3>
          <ul className="players">
            {lobby.kursi.map((s, i) => (
              <SeatRow key={s.id} s={s} i={i} lobby={lobby} me={me}
                onRemove={s.owner === me || isHost ? () => send({ type: 'hapus_kursi', seat_id: s.id }) : undefined} />
            ))}
          </ul>
          {lobby.penonton.length > 0 && <p className="hint">Penonton: {lobby.penonton.join(', ')}</p>}
          {!mySeat && !full && <button type="button" className="btn" onClick={() => send({ type: 'duduk' })}>Ikut main (ambil kursi)</button>}
          {lobby.match_no > 0 && <p className="hint">Sudah {lobby.match_no} match di room ini.</p>}
        </div>

        {mySeat && (
          <div className="panel">
            <h3>Kursimu: {mySeat.name}</h3>
            <div className="tabs" role="tablist">
              <button type="button" role="tab" aria-selected={mySeat.kind === 'manusia'} onClick={() => send({ type: 'jadi_manusia' })}>🙂 Main sendiri</button>
              <button type="button" role="tab" aria-selected={mySeat.kind === 'bot'} onClick={() => setEditor(true)}>🤖 Pakai bot</button>
            </div>
            <p className="hint">
              {mySeat.kind === 'manusia'
                ? `Kamu yang memutuskan setiap langkah (waktu ${lobby.waktu} detik; kalau habis, aksi bawaan dipakai).`
                : `Kursimu dimainkan bot "${mySeat.label}". Kamu tinggal menonton.`}
            </p>
          </div>
        )}

        <div className="panel">
          <h3>Tambah bot</h3>
          <label className="field">Kode bot
            <select className="input" value={tpl} onChange={(e) => setTpl(e.target.value)}>
              <option value="__kode__">Kode di editorku</option>
              {meta.templates.map((t) => <option key={t.id} value={t.id}>Template: {t.nama}</option>)}
            </select>
          </label>
          <label className="field">Nama bot
            <input className="input" value={botName} maxLength={16} placeholder={nextBotName()} onChange={(e) => setBotName(e.target.value)} />
          </label>
          <div className="row">
            <button type="button" className="btn" disabled={full} onClick={addBot}>+ Tambah ke kursi kosong</button>
            {tpl === '__kode__' && <button type="button" className="btn small" onClick={() => setEditor(!editor)}>{editor ? 'Tutup editor' : 'Buka editor'}</button>}
          </div>
          {full && <p className="hint">Kursi penuh.</p>}
        </div>

        <div className="panel">
          <h3>Aturan room</h3>
          {isHost ? (
            <>
              <SettingsForm meta={meta} values={cfg} onChange={setCfg} />
              <div className="fields">
                <label className="field">Waktu manusia (detik)
                  <input type="number" min={3} max={300} value={waktu} onChange={(e) => setWaktu(Number(e.target.value))} />
                </label>
                <label className="field">Jeda langkah bot (detik)
                  <input type="number" min={0} max={5} step={0.1} value={jeda} onChange={(e) => setJeda(Number(e.target.value))} />
                </label>
              </div>
              <p className="hint">Jeda 0 + semua kursi bot = match langsung dihitung server dan hasilnya diputar sebagai replay.</p>
              <button type="button" className="btn small" disabled={!dirty} onClick={() => send({ type: 'atur', settings: cfg, waktu, jeda })}>Simpan aturan</button>
            </>
          ) : (
            <>
              <SettingsSummary meta={meta} values={lobby.settings} />
              <p className="hint">Waktu manusia {lobby.waktu} detik · jeda bot {lobby.jeda} detik. Hanya host yang bisa mengubah.</p>
            </>
          )}
        </div>
      </div>

      <div className="lobby-main">
        <div className="panel start-box">
          {isHost ? (
            <>
              <button type="button" className="btn primary big" disabled={lobby.kursi.length < lobby.min || dirty} onClick={() => send({ type: 'mulai' })}>
                ▶ Mulai {allBots && lobby.jeda === 0 ? '(instan)' : ''}
              </button>
              <span className="hint">
                {lobby.kursi.length < lobby.min ? `Butuh minimal ${lobby.min} kursi (manusia atau bot).` : dirty ? 'Simpan aturan dulu.' : 'Siap dimulai.'}
              </span>
            </>
          ) : (
            <span className="hint">Menunggu host memulai match…</span>
          )}
        </div>
        {editor && (
          <div className="panel">
            <h3>Editor bot · {meta.nama}</h3>
            <HubBotPanel meta={meta} code={code} setCode={setCode} compact>
              <div className="row">
                {mySeat && (
                  <button type="button" className="btn primary" onClick={() => send({ type: 'jadi_bot', kode: code, label: 'Kode sendiri' })}>
                    Pakai kode ini untuk kursiku
                  </button>
                )}
                <button type="button" className="btn" disabled={full} onClick={() => send({ type: 'tambah_bot', nama: botName.trim() || nextBotName(), kode: code, label: 'Kode sendiri' })}>
                  Tambah sebagai bot baru
                </button>
              </div>
            </HubBotPanel>
          </div>
        )}
        <article className="panel guide-body rules-box">
          <h3>Cara main</h3>
          <RulesText meta={meta} />
        </article>
      </div>
    </div>
  );
}

export function RulesText({ meta }: { meta: GameMeta }) {
  const [html, setHtml] = useState<string>('');
  useEffect(() => {
    let alive = true;
    import('marked').then(({ marked }) => {
      if (alive) setHtml(marked.parse(`${meta.aturan}\n\n**Bentuk aksi bot:**\n\n${meta.format_aksi}`, { async: false }) as string);
    });
    return () => {
      alive = false;
    };
  }, [meta]);
  // teks aturan berasal dari server sendiri (definisi game), bukan dari pemain
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

/* ================================================================== main */
function Live({ lobby, meta, start, upd, log, actedStep, done, offset, act }: {
  lobby: LobbyMsg; meta: GameMeta; start: StartInfo | null; upd: UpdateMsg | null; log: string[]; actedStep: number;
  done: { step: number; seats: number[] }; offset: number; act: (a: unknown) => void;
}) {
  const [, tick] = useState(0);
  const humanTimer = !!upd && upd.deadline > 0 && upd.pending.some((p) => lobby.kursi[p]?.kind === 'manusia');
  useEffect(() => {
    if (!humanTimer) return;
    const t = window.setInterval(() => tick((x) => x + 1), 250);
    return () => window.clearInterval(t);
  }, [humanTimer]);

  const names = start?.names ?? lobby.kursi.map((k) => k.name);
  if (start?.instan) {
    return <div className="panel running-banner"><div className="spinner" /> Semua kursi bot: match sedang dihitung server, sebentar lagi replay muncul…</div>;
  }
  if (!upd) return <div className="panel running-banner"><div className="spinner" /> Menunggu langkah pertama…</div>;

  const R = rendererFor(meta.id);
  const mine = start?.main_sendiri ?? false;
  const canAct = upd.my_turn && mine && actedStep !== upd.step;
  const acted = !meta.mandiri && mine && actedStep === upd.step && upd.pending.includes(upd.seat ?? -1);
  const remaining = humanTimer ? Math.max(0, upd.deadline - (Date.now() / 1000 - offset)) : 0;
  const total = lobby.waktu;
  const doneSeats = new Set([...(upd.acted ?? []), ...(done.step === upd.step ? done.seats : [])]);
  const waiting = meta.mandiri ? [] : upd.pending.filter((p) => !doneSeats.has(p)).map((p) => names[p]);

  return (
    <div className="live">
      {humanTimer && (
        <div className={`timer ${remaining < 5 ? 'low' : ''}`} aria-label={`Sisa waktu ${Math.ceil(remaining)} detik`}>
          <i style={{ width: `${Math.min(100, (remaining / Math.max(total, 1)) * 100)}%` }} />
          <span>{Math.ceil(remaining)} dtk</span>
        </div>
      )}
      <R view={upd.view} meta={meta} names={names} me={upd.seat} canAct={canAct} acted={acted} replay={false} events={upd.events}
        settings={lobby.settings} pending={upd.pending} act={act} />
      <div className="live-foot">
        {waiting.length > 0 && <span className="hint">Menunggu: {waiting.join(', ')}</span>}
        <details className="event-log" open>
          <summary>Kejadian</summary>
          <ol className="hist small">{log.map((l, k) => <li key={k}>{l}</li>)}</ol>
        </details>
      </div>
    </div>
  );
}

/* ================================================================== hasil */
function Results({ final, meta, lobby, me, onBack }: { final: FinalMsg; meta: GameMeta; lobby: LobbyMsg; me: string | null; onBack: () => void }) {
  const r = final.result;
  const rows = useMemo(() => r.ranking.map((i, k) => ({
    rank: k + 1, i, name: final.names[i], kind: final.kinds[i], skor: r.skor[i], rating: final.ratings?.[final.names[i]],
  })), [final, r]);
  const mySeats = new Set(lobby.kursi.filter((k) => k.owner === me).map((k) => k.name));
  return (
    <div className="results">
      <div className="panel">
        <div className="row">
          <h2>🏆 {final.names[r.pemenang]} menang!</h2>
          <span className="spacer" />
          <button type="button" className="btn primary" onClick={onBack}>Kembali ke lobby</button>
        </div>
        <div className="table-wrap">
          <table className="tbl results-tbl">
            <thead><tr><th>#</th><th>Pemain</th><th>{r.label_skor}</th><th>Rating</th></tr></thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.i} className={mySeats.has(x.name) ? 'me' : ''}>
                  <td>{x.rank}</td>
                  <td><span className="chip" style={{ ['--c' as string]: seatColor(x.i) }}>{x.kind === 'bot' ? '🤖' : '🙂'} {x.name}</span></td>
                  <td className="num">{fmt(x.skor, 2)}</td>
                  <td className="num">{x.rating ? <>{Math.round(x.rating.baru)} <b className={x.rating.delta >= 0 ? 'good' : 'bad'}>({x.rating.delta >= 0 ? '+' : ''}{x.rating.delta.toFixed(1)})</b></> : <span className="hint">–</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!final.ratings && <p className="hint">Masuk akun (menu Kilas Pasar → Akun) supaya hasil match masuk liga rating.</p>}
      </div>
      <Reveal gid={meta.id} reveal={final.reveal} names={final.names} />
      {final.frames.length > 1 && (
        <div className="panel">
          <h3>Replay</h3>
          <FrameReplay frames={final.frames} meta={meta} names={final.names} settings={lobby.settings} />
        </div>
      )}
      {Object.entries(final.logs ?? {}).map(([n, lg]) => <HubBotLog key={n} name={n} log={lg} />)}
    </div>
  );
}
