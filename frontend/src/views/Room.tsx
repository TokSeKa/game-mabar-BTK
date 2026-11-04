import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BotEditor, type CheckState } from '../editor/BotEditor';
import { copyText } from '../util';
import { Replay } from '../replay/Replay';
import { ROBOT } from '../replay/assets';
import { RoomSocket, type ConnStatus } from '../socket';
import { KEYS, remove, save, type SavedBot, type Session } from '../storage';
import { getToken } from '../trading/api';
import type { BotErrorInfo, MatchResultMsg, MatchSettings, RoomState, TournamentResult } from '../types';
import { BotLog } from './BotLog';
import { DebugPanel, EventName, EventSelect, RatingList, ReactionBar, ReactionLayer, TournamentView, useReactions } from './SuitExtras';

export type RoomEntry =
  | { action: 'create'; name: string }
  | { action: 'join'; name: string; code: string; spectator?: boolean }
  | { action: 'rejoin'; session: Session };

interface Props {
  entry: RoomEntry;
  bot: SavedBot;
  setBot: (b: SavedBot) => void;
  onExit: (message?: string) => void;
  toast: (msg: string, err?: boolean) => void;
}

interface ServerBot {
  ok: boolean;
  error: BotErrorInfo | null;
  code: string | null;
}

const SETTING_FIELDS: { key: keyof MatchSettings; label: string; min: number; max: number; step?: number }[] = [
  { key: 'hp_awal', label: 'HP awal', min: 100, max: 100000, step: 100 },
  { key: 'hp_kalah', label: 'HP hilang saat kalah', min: 1, max: 100000, step: 10 },
  { key: 'ronde_maks', label: 'Batas ronde', min: 1, max: 300 },
  { key: 'ingatan', label: 'Ingatan bot (ronde)', min: 1, max: 50 },
];

function MiniBot({ color }: { color: string }) {
  return <span className="mini-bot" style={{ ['--c' as string]: color }} dangerouslySetInnerHTML={{ __html: ROBOT }} />;
}

export function Room({ entry, bot, setBot, onExit, toast }: Props) {
  const [room, setRoom] = useState<RoomState | null>(null);
  const [me, setMe] = useState<string | null>(entry.action === 'rejoin' ? entry.session.player_id : null);
  const [conn, setConn] = useState<ConnStatus>('connecting');
  const [serverBot, setServerBot] = useState<ServerBot | null>(null);
  const [result, setResult] = useState<MatchResultMsg | null>(null);
  const [replayKey, setReplayKey] = useState(0);
  const [autoplay, setAutoplay] = useState(true);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<'bot' | 'replay' | 'turnamen'>('bot');
  const [tour, setTour] = useState<TournamentResult | null>(null);
  const [ronde, setRonde] = useState(1);
  const [reacts, addReact] = useReactions();
  const addReactRef = useRef(addReact);
  addReactRef.current = addReact;
  const [draft, setDraft] = useState<MatchSettings | null>(null);
  const [check, setCheck] = useState<CheckState>({ state: 'checking' });
  const sessionRef = useRef<Session | null>(entry.action === 'rejoin' ? entry.session : null);
  const pendingReady = useRef(false);
  const sockRef = useRef<RoomSocket | null>(null);
  const exitRef = useRef(onExit);
  exitRef.current = onExit;
  const toastRef = useRef(toast);
  toastRef.current = toast;

  useEffect(() => {
    const hello = () => {
      const s = sessionRef.current;
      const akun_token = getToken();
      if (s) return { type: 'rejoin', code: s.code, player_id: s.player_id, token: s.token, akun_token };
      if (entry.action === 'create') return { type: 'create_room', name: entry.name, akun_token };
      if (entry.action === 'join') return { type: 'join_room', code: entry.code, name: entry.name, spectator: !!entry.spectator, akun_token };
      return null;
    };
    const onMessage = (msg: Record<string, any>) => {
      switch (msg.type) {
        case 'joined': {
          const s: Session = { code: msg.room_code, player_id: msg.player_id, token: msg.token };
          sessionRef.current = s;
          save(KEYS.session, s);
          setMe(msg.player_id);
          try {
            history.replaceState(null, '', `#room-${msg.room_code}`);
          } catch {
            /* abaikan */
          }
          break;
        }
        case 'room_state':
          setRoom(msg.room);
          break;
        case 'bot_status':
          setServerBot({ ok: msg.ok, error: msg.error, code: msg.code });
          if (msg.ok && pendingReady.current) {
            pendingReady.current = false;
            sockRef.current?.send({ type: 'set_ready', ready: true });
          } else if (!msg.ok && pendingReady.current) {
            pendingReady.current = false;
            toastRef.current('Bot belum valid, jadi belum bisa siap.', true);
          }
          break;
        case 'match_result':
          setResult(msg as MatchResultMsg);
          setRevealed(msg.revealed ?? {});
          setAutoplay(!!msg.replay);
          setReplayKey((k) => k + 1);
          if (msg.replay) setTab('replay');
          break;
        case 'code_revealed':
          setRevealed((r) => ({ ...r, [msg.player_id]: msg.code }));
          break;
        case 'reaction':
          addReactRef.current(msg.name, msg.emoji);
          break;
        case 'tournament_result':
          setTour(msg as TournamentResult);
          if (msg.baru) setTab('turnamen');
          break;
        case 'error':
          if (!sessionRef.current || /Sesi lama/.test(msg.message)) {
            remove(KEYS.session);
            sockRef.current?.close();
            exitRef.current(msg.message);
          } else {
            toastRef.current(msg.message, true);
          }
          break;
        case 'kicked':
          remove(KEYS.session);
          sockRef.current?.close();
          exitRef.current('Kamu dikeluarkan dari room oleh host.');
          break;
        case 'left':
          break;
      }
    };
    const sock = new RoomSocket(hello, onMessage, setConn);
    sockRef.current = sock;
    sock.connect();
    return () => sock.close();
    // entry tetap selama komponen hidup
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // draft aturan mengikuti server kecuali sedang diedit host
  const settingsKey = room ? JSON.stringify(room.settings) : '';
  useEffect(() => {
    if (room) setDraft(room.settings);
  }, [settingsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const send = useCallback((msg: object) => {
    if (!sockRef.current?.send(msg)) toastRef.current('Koneksi terputus. Menyambung ulang…', true);
  }, []);

  const mePlayer = room?.players.find((p) => p.id === me) ?? null;
  const iSpectate = !!room && !mePlayer && !!room.penonton?.some((p) => p.id === me);
  const isHost = !!room && room.host_id === me;
  const dirty = serverBot?.code !== bot.code;
  const readyCount = room ? room.players.filter((p) => p.ready && p.bot_ok && p.online).length : 0;
  const running = room?.status === 'running';

  const submitBot = () => send({ type: 'submit_bot', code: bot.code });
  const toggleReady = () => {
    if (!mePlayer) return;
    if (mePlayer.ready) {
      send({ type: 'set_ready', ready: false });
      return;
    }
    if (check.state === 'err') {
      toast('Perbaiki error di kode bot dulu.', true);
      return;
    }
    if (dirty || !serverBot?.ok) {
      pendingReady.current = true;
      submitBot();
    } else send({ type: 'set_ready', ready: true });
  };

  const leave = () => {
    send({ type: 'leave_room' });
    remove(KEYS.session);
    sockRef.current?.close();
    try {
      history.replaceState(null, '', location.pathname + location.search);
    } catch {
      /* abaikan */
    }
    onExit();
  };

  const shareLink = useMemo(() => (room ? `${location.origin}${location.pathname}#room-${room.code}` : ''), [room]);
  const myIndex = result?.my_index;
  const iPlayed = myIndex != null;

  if (!room || !draft) {
    return (
      <div className="panel" style={{ alignItems: 'center', padding: 40 }}>
        <div className="spinner" />
        <p className="hint">{conn === 'reconnecting' ? 'Menyambung ulang ke server…' : 'Masuk ke room…'}</p>
        <button className="btn" type="button" onClick={() => { remove(KEYS.session); sockRef.current?.close(); onExit(); }}>Batal</button>
      </div>
    );
  }

  return (
    <div className="col" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="room-head">
        <span className="hint">Kode room</span>
        <span className="room-code">{room.code}</span>
        <button
          className="btn small"
          type="button"
          onClick={async () => toast((await copyText(shareLink)) ? 'Link room tersalin. Kirim ke temanmu!' : `Salin link ini: ${shareLink}`)}
        >
          Salin link undangan
        </button>
        <span className={`status-pill ${conn === 'open' ? 'ok' : 'warn'}`}>{conn === 'open' ? 'Tersambung' : 'Menyambung ulang…'}</span>
        <EventName id={room.settings.event} />
        <span className="spacer" />
        <ReactionBar onSend={(e) => send({ type: 'react', emoji: e })} />
        <button className="btn small danger" type="button" onClick={leave}>Keluar room</button>
      </div>

      <div className="room-grid">
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
          <div className="panel">
            <h3>Pemain ({room.players.length}/8)</h3>
            <ul className="players">
              {room.players.map((p) => (
                <li key={p.id} className={`${p.online ? '' : 'offline'} ${p.id === me ? 'me' : ''}`}>
                  <MiniBot color={p.color} />
                  <span className="pn">
                    {p.name}
                    {p.id === me ? ' (kamu)' : ''}
                    <small>{p.online ? `${p.wins} menang dari ${p.matches} match` : 'offline'}{p.akun ? ` · akun ${p.akun}` : ''}</small>
                  </span>
                  <span className="tags">
                    {p.is_host && <span className="tag-mini host">host</span>}
                    {!p.bot_ok ? <span className="tag-mini nobot">belum ada bot</span> : p.ready ? <span className="tag-mini ready">siap</span> : <span className="tag-mini">bot ok</span>}
                    {isHost && p.id !== me && (
                      <button className="btn small" type="button" title={`Keluarkan ${p.name}`} onClick={() => send({ type: 'kick', player_id: p.id })}>✕</button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            {!!room.penonton?.length && <p className="hint">Penonton: {room.penonton.map((x) => x.name + (x.id === me ? ' (kamu)' : '')).join(', ')}</p>}
            {iSpectate && (
              <button className="btn" type="button" disabled={running || room.players.length >= 8} onClick={() => send({ type: 'play' })}>Ambil kursi pemain</button>
            )}
            {mePlayer && !running && (
              <button className="btn small" type="button" onClick={() => send({ type: 'spectate' })}>Jadi penonton saja</button>
            )}
          </div>

          <div className="panel">
            <h3>Aturan room</h3>
            <div className="fields">
              {SETTING_FIELDS.map((f) => (
                <label className="field" key={f.key} htmlFor={`set-${f.key}`}>
                  {f.label}
                  <input
                    id={`set-${f.key}`}
                    type="number"
                    min={f.min}
                    max={f.max}
                    step={f.step ?? 1}
                    disabled={!isHost || running}
                    value={draft[f.key]}
                    onChange={(e) => setDraft({ ...draft, [f.key]: Number(e.target.value) })}
                  />
                </label>
              ))}
              <EventSelect value={draft.event ?? 'normal'} disabled={!isHost || running} onChange={(v) => setDraft({ ...draft, event: v })} />
            </div>
            {isHost ? (
              <button
                className="btn"
                type="button"
                disabled={running || JSON.stringify(draft) === JSON.stringify(room.settings)}
                onClick={() => send({ type: 'update_settings', settings: draft })}
              >
                Simpan aturan
              </button>
            ) : (
              <p className="hint">Hanya host yang bisa mengubah aturan.</p>
            )}
          </div>

          <div className="panel">
            <h3>Mulai match</h3>
            {isHost ? (
              <>
                <button className="btn primary big" type="button" disabled={running || readyCount < 2} onClick={() => send({ type: 'start_match' })}>
                  Mulai match ({readyCount} siap)
                </button>
                <button className="btn" type="button" disabled={running || readyCount < 3} onClick={() => send({ type: 'start_tournament' })}>
                  🏆 Mulai turnamen 1 lawan 1
                </button>
                <p className="hint">
                  Yang ikut hanya pemain online dengan bot valid yang sudah menekan "Siap". Match biasa minimal 2;
                  turnamen minimal 3 (setiap pasangan bertanding 1 lawan 1).
                </p>
              </>
            ) : (
              <p className="hint">Menunggu host memulai. {readyCount} pemain sudah siap.</p>
            )}
          </div>
        </aside>

        <section style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
          {running && (
            <div className="running-banner">
              <div className="spinner" /> Match sedang dihitung di server… replay akan langsung diputar.
            </div>
          )}
          <div className="tabs" role="tablist">
            <button type="button" role="tab" aria-selected={tab === 'bot'} onClick={() => setTab('bot')}>Botku</button>
            <button type="button" role="tab" aria-selected={tab === 'replay'} onClick={() => setTab('replay')} disabled={!result}>
              Replay match terakhir
            </button>
            {tour && <button type="button" role="tab" aria-selected={tab === 'turnamen'} onClick={() => setTab('turnamen')}>Turnamen</button>}
          </div>
          {iSpectate && tab === 'bot' && (
            <div className="panel"><p className="hint">Kamu masuk sebagai penonton: replay match dan turnamen tetap bisa ditonton, dan kamu bisa mengirim reaksi.
              Tekan "Ambil kursi pemain" untuk ikut bertanding.</p></div>
          )}

          {tab === 'turnamen' && tour && <TournamentView t={tour} me={me} />}
          <div hidden={tab !== 'bot' || iSpectate}>
            <BotEditor bot={bot} onChange={setBot} onCheck={setCheck}>
              <button className="btn" type="button" onClick={submitBot} disabled={running && !!mePlayer?.ready}>
                {dirty ? 'Kirim bot ke room' : 'Bot sudah terkirim ✓'}
              </button>
              <button
                className={`btn ${mePlayer?.ready ? 'good' : 'primary'}`}
                type="button"
                onClick={toggleReady}
                disabled={running}
              >
                {mePlayer?.ready ? 'Siap ✓ (klik untuk batal)' : 'Siap!'}
              </button>
              {mePlayer?.ready && dirty && <span className="status-pill warn">Bot berubah sejak kamu siap. Klik "Kirim bot ke room".</span>}
              {serverBot && !serverBot.ok && serverBot.error && !dirty && (
                <span className="status-pill err">Bot di room tidak valid</span>
              )}
            </BotEditor>
          </div>

          {tab === 'replay' && result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Replay key={replayKey} match={result.match} myIndex={myIndex} autoplay={autoplay} startAtEnd={!autoplay} onRound={setRonde} />
              <RatingList ratings={result.match.ratings} players={result.match.players} />
              {iPlayed && myIndex != null && <DebugPanel match={result.match} myIndex={myIndex} code={bot.code} ronde={ronde} />}
              <div className="two-col">
                {iPlayed && result.my_log ? <BotLog log={result.my_log} /> : <div className="panel"><p className="hint">Kamu tidak ikut match ini.</p></div>}
                <div className="panel">
                  <h3>Buka kartu (opsional)</h3>
                  <p className="hint">Setelah match, setiap pemain boleh memilih untuk memperlihatkan kode botnya ke semua orang di room.</p>
                  {iPlayed && !revealed[me ?? ''] && (
                    <button className="btn" type="button" onClick={() => send({ type: 'reveal_code' })}>Tunjukkan kode botku</button>
                  )}
                  <div className="reveal-list">
                    {Object.entries(revealed).map(([pid, code]) => {
                      const p = result.match.players.find((x) => x.id === pid);
                      return (
                        <details key={pid} open>
                          <summary><b style={{ color: p?.color }}>{p?.name ?? pid}</b></summary>
                          <pre className="code-preview">{code}</pre>
                        </details>
                      );
                    })}
                    {!Object.keys(revealed).length && <p className="hint">Belum ada yang membuka kode.</p>}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
      <ReactionLayer items={reacts} />
    </div>
  );
}
