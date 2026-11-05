import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { load, save } from '../storage';
import type { AccountSnap, BoardRow, Candle, Fill, SessionInfo, SummaryMsg } from './api';
import { ChartPanel, tfSec, type PanelHandle } from './ChartPanel';
import type { PasarConn } from './conn';
import { DrawingStore, TOOL_INFO, type Tool } from './drawings';
import { fmtMoney, fmtNum, fmtPct, fmtQty, makeTimeFmt } from './format';
import { IndicatorMenu } from './IndicatorMenu';
import { DEFAULT_INDICATORS, type IndicatorConfig } from './indicators';
import { Summary } from './Summary';
import { TradePanel } from './TradePanel';

export interface RaceInfo {
  board: BoardRow[];
  isHost: boolean;
  myId: string;
  status: string;
  speed: number;
  stepN: number;
  stepsTotal: number;
}

interface Props {
  conn: PasarConn;
  session: SessionInfo;
  toast: (m: string, err?: boolean) => void;
  onExit: () => void;
  onAgain?: () => void;
  race?: RaceInfo;
}

const SPEEDS = [1, 2, 4, 8, 16];
const MODE_LABEL: Record<string, string> = { solo: 'Latihan', harian: 'Tantangan harian', 'harian-latihan': 'Harian (tidak dinilai)', balapan: 'Balapan' };

function secondTf(tfs: string[], main: string): string {
  const i = tfs.indexOf(main);
  return tfs[Math.min(tfs.length - 1, i + 2)] ?? main;
}

export function TradeScreen({ conn, session: initial, toast, onExit, onAgain, race }: Props) {
  const [session, setSession] = useState(initial);
  const [account, setAccount] = useState<AccountSnap | null>(() => conn.last.get('account')?.account ?? null);
  const [fills, setFills] = useState<Fill[]>(() => (conn.last.get('account')?.full ? conn.last.get('account')?.fills ?? [] : []));
  const [price, setPrice] = useState(initial.price);
  const [now, setNow] = useState(initial.now);
  const [progress, setProgress] = useState(initial.progress);
  const [done, setDone] = useState(false);
  const [summary, setSummary] = useState<SummaryMsg | null>(() => (conn.last.get('summary') as SummaryMsg) ?? null);
  const [showSummary, setShowSummary] = useState(() => conn.last.has('summary'));
  const [layout, setLayout] = useState<1 | 2>(() => load<1 | 2>('kilas-layout', 1));
  const [tfs, setTfs] = useState<[string, string]>([initial.chart_tf, secondTf(initial.tfs, initial.chart_tf)]);
  const [ind, setInd] = useState<IndicatorConfig>(() => ({ ...DEFAULT_INDICATORS, ...load<Partial<IndicatorConfig>>('kilas-ind', {}) }));
  const [tool, setTool] = useState<Tool>('none');
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(() => load<number>('kilas-speed', 2));
  const [confirmFinish, setConfirmFinish] = useState(false);
  const store = useMemo(() => new DrawingStore(), []);
  const panels = useRef(new Map<number, PanelHandle>());
  const stepping = useRef(false);
  const playingRef = useRef(false);
  const timer = useRef<number | undefined>();
  const removeSel = useRef<Array<() => boolean>>([]);
  playingRef.current = playing;
  const mainTf = tfs[0];
  const isRace = session.mode === 'balapan';
  const fmt = makeTimeFmt(session.blind.tanggal, session.start_time);

  useEffect(() => save('kilas-ind', ind), [ind]);
  useEffect(() => save('kilas-layout', layout), [layout]);
  useEffect(() => save('kilas-speed', speed), [speed]);

  const request = useCallback((tf: string, before?: number) => {
    conn.send({ type: 'history', tf, before: before ?? null, limit: 1500 });
  }, [conn]);

  const register = useCallback((h: PanelHandle) => {
    panels.current.set(h.id, h);
    return () => {
      if (panels.current.get(h.id) === h) panels.current.delete(h.id);
    };
  }, []);

  const shownTfs = layout === 2 ? Array.from(new Set(tfs)) : [tfs[0]];
  useEffect(() => {
    conn.send({ type: 'subscribe', tfs: shownTfs });
  }, [conn, shownTfs.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const stopPlay = () => {
    setPlaying(false);
    window.clearTimeout(timer.current);
  };

  const step = useCallback((tf: string, n = 1) => {
    if (stepping.current || isRace) return;
    stepping.current = true;
    if (!conn.send({ type: 'step', tf, n })) stepping.current = false;
  }, [conn, isRace]);

  // pesan dari server
  useEffect(() => {
    const onMsg = (m: Record<string, any>) => {
      switch (m.type) {
        case 'session':
          setSession(m as SessionInfo);
          setPrice(m.price);
          setNow(m.now);
          for (const h of panels.current.values()) request(h.tf);
          break;
        case 'candles':
          for (const h of panels.current.values()) if (h.tf === m.tf) h.onCandles(m.candles as Candle[], m.before ?? null, !!m.more);
          break;
        case 'tick': {
          stepping.current = false;
          for (const h of panels.current.values()) {
            const u = m.updates?.[h.tf];
            if (u?.length) h.onUpdates(u as Candle[]);
          }
          setAccount(m.account);
          if (m.fills?.length) setFills((f) => [...f, ...m.fills]);
          setPrice(m.price);
          setNow(m.now);
          setProgress(m.progress);
          if (m.done) {
            setDone(true);
            stopPlay();
          } else if (playingRef.current) {
            timer.current = window.setTimeout(() => step(mainTfRef.current, 1), 1000 / speedRef.current);
          }
          break;
        }
        case 'account':
          setAccount(m.account);
          if (m.full) setFills(m.fills ?? []);
          else if (m.fills?.length) setFills((f) => [...f, ...m.fills]);
          break;
        case 'summary':
          setSummary(m as SummaryMsg);
          setShowSummary(true);
          setDone(true);
          stopPlay();
          break;
        case 'error':
          if (m.for === 'step') {
            stepping.current = false;
            stopPlay();
          }
          toast(m.message, true);
          break;
      }
    };
    const off = conn.on(onMsg);
    // pesan yang datang sebelum listener terpasang
    const la = conn.last.get('account');
    if (la) {
      setAccount(la.account);
      if (la.full) setFills(la.fills ?? []);
    }
    const ls = conn.last.get('summary');
    if (ls) {
      setSummary(ls as SummaryMsg);
      setDone(true);
    }
    return off;
  }, [conn, request, step, toast]);

  const mainTfRef = useRef(mainTf);
  mainTfRef.current = mainTf;
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const togglePlay = () => {
    if (isRace || done) return;
    if (playing) stopPlay();
    else {
      setPlaying(true);
      playingRef.current = true;
      step(mainTf, 1);
    }
  };

  // pintasan keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || isRace) return;
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        step(mainTf, e.shiftKey ? 10 : 1);
      } else if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const send = (m: Record<string, any>) => {
    if (!conn.send(m)) toast('Koneksi terputus. Menyambung ulang…', true);
  };

  const setPanelTf = (i: 0 | 1, tf: string) => setTfs((t) => (i === 0 ? [tf, t[1]] : [t[0], tf]));
  const lot = session.lot > 1 ? session.lot : 1;
  const recentFills = fills.slice(-60).reverse();

  return (
    <div className="ts">
      <div className="ts-head">
        <div className="ts-title">
          <span className="badge">{MODE_LABEL[session.mode] ?? session.mode}</span>
          <h2>{session.label}</h2>
          {session.product && <span className="badge alt">{session.product.kind === 'perp' ? 'Futures' : 'Margin'}</span>}
          <span className="hint">{session.market_nama} · data dasar {session.tf_label[session.base_tf] ?? session.base_tf} · {fmt.full(now)}</span>
        </div>
        <div className="ts-price">
          <b>{fmtNum(price, session.decimals)}</b>
          <span className={(account?.return_pct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(account?.return_pct ?? 0)}</span>
        </div>
        <div className="row">
          {!isRace && !summary && (
            confirmFinish ? (
              <>
                <span className="hint">Akhiri sesi sekarang?</span>
                <button className="btn small primary" type="button" onClick={() => { setConfirmFinish(false); stopPlay(); send({ type: 'finish' }); }}>Ya, akhiri</button>
                <button className="btn small" type="button" onClick={() => setConfirmFinish(false)}>Batal</button>
              </>
            ) : (
              <button className="btn small" type="button" onClick={() => setConfirmFinish(true)}>Selesai & lihat hasil</button>
            )
          )}
          {summary && <button className="btn small primary" type="button" onClick={() => setShowSummary(true)}>Lihat hasil</button>}
          <button className="btn small" type="button" onClick={onExit}>Keluar</button>
        </div>
      </div>
      {(session.fixed_end || isRace) && (
        <div className="ts-progress" title="Progres sesi"><div style={{ width: `${Math.min(100, progress * 100)}%` }} /></div>
      )}

      <div className="ts-grid">
        <div className="ts-main">
          <div className="ts-toolbar">
            <div className="seg" role="group" aria-label="Tata letak">
              <button type="button" aria-pressed={layout === 1} onClick={() => setLayout(1)}>1 chart</button>
              <button type="button" aria-pressed={layout === 2} onClick={() => setLayout(2)}>2 chart</button>
            </div>
            <IndicatorMenu cfg={ind} onChange={setInd} />
            <div className="tools" role="group" aria-label="Alat gambar">
              {TOOL_INFO.map((t) => (
                <button key={t.id} type="button" title={t.title} aria-pressed={tool === t.id} onClick={() => setTool(tool === t.id ? 'none' : t.id)}>{t.label}</button>
              ))}
              <button type="button" title="Hapus gambar yang dipilih (atau tekan Delete)" onClick={() => removeSel.current.some((f) => f())}>⌫</button>
              <button type="button" title="Hapus semua gambar" onClick={() => store.clear()}>Hapus semua</button>
            </div>
            {tool !== 'none' && <span className="hint">Klik di chart untuk menaruh titik. Esc untuk batal.</span>}
          </div>
          <div className={`charts l${layout}`}>
            <ChartPanel id={1} session={session} tf={tfs[0]} onTf={(tf) => setPanelTf(0, tf)} indicators={ind} store={store} tool={tool}
              onToolDone={() => setTool('none')} fills={fills} account={account} register={register} request={request}
              removeRef={(f) => (removeSel.current[0] = f)} />
            {layout === 2 && (
              <ChartPanel id={2} session={session} tf={tfs[1]} onTf={(tf) => setPanelTf(1, tf)} indicators={ind} store={store} tool={tool}
                onToolDone={() => setTool('none')} fills={fills} account={account} register={register} request={request} compact
                removeRef={(f) => (removeSel.current[1] = f)} />
            )}
          </div>
          {!isRace ? (
            <div className="replay-bar">
              <button className="btn primary" type="button" disabled={done} onClick={togglePlay}>{playing ? '⏸ Jeda' : '▶ Putar'}</button>
              <button className="btn" type="button" disabled={done || playing} onClick={() => step(mainTf, 1)} title="Pintasan: panah kanan">+1 candle {session.tf_label[mainTf]}</button>
              <button className="btn" type="button" disabled={done || playing} onClick={() => step(mainTf, 10)} title="Pintasan: Shift + panah kanan">+10</button>
              {session.base_tf !== mainTf && (
                <button className="btn" type="button" disabled={done || playing} onClick={() => step(session.base_tf, 1)}>+1 {session.tf_label[session.base_tf]}</button>
              )}
              <label className="speed" htmlFor="spd">
                Kecepatan
                <select id="spd" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                  {SPEEDS.map((s) => <option key={s} value={s}>{s} candle/detik</option>)}
                </select>
              </label>
              {session.fixed_end && <span className="hint">{Math.round(progress * 100)}% sesi</span>}
              {done && !summary && <span className="hint">Data habis.</span>}
            </div>
          ) : (
            <RaceBar race={race} send={send} />
          )}
        </div>
        <aside className="ts-side">
          {race && <RaceBoard race={race} />}
          <TradePanel session={session} account={account} price={price} send={send} disabled={done} />
        </aside>
      </div>

      <div className="panel fills">
        <h3>Riwayat transaksi</h3>
        {!recentFills.length && <p className="hint">Belum ada transaksi.</p>}
        {recentFills.length > 0 && (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Waktu</th><th>Aksi</th><th>Jenis</th><th>Jumlah</th><th>Harga</th><th>Fee</th><th>Laba/rugi</th></tr></thead>
              <tbody>
                {recentFills.map((f) => (
                  <tr key={f.id}>
                    <td>{fmt.full(f.time)}</td>
                    <td className={f.side === 'buy' ? 'up' : 'down'}>{session.product?.kind === 'perp' ? (f.side === 'buy' ? 'Buy' : 'Sell') : f.side === 'buy' ? 'Beli' : 'Jual'}</td>
                    <td>{f.label}{f.note ? ` (${f.note})` : ''}</td>
                    <td>{fmtQty(f.qty / lot, lot > 1 ? 1 : session.qty_step)} {lot > 1 ? 'lot' : session.satuan}</td>
                    <td>{fmtNum(f.price, session.decimals)}</td>
                    <td>{fmtMoney(f.fee, session.currency)}</td>
                    <td className={(f.pnl ?? 0) >= 0 ? 'up' : 'down'}>{f.pnl == null ? '–' : fmtMoney(f.pnl, session.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {summary && showSummary && (
        <Summary summary={summary} session={session} onClose={() => setShowSummary(false)} onAgain={onAgain} myId={race?.myId} />
      )}
      <p className="hint kbd-hint">Pintasan: → maju 1 candle, Shift+→ maju 10, Spasi putar/jeda, Delete hapus gambar terpilih. Tampilan: {tfSec(mainTf) >= 86400 ? 'harian/lebih' : 'intraday'}.</p>
    </div>
  );
}

function RaceBar({ race, send }: { race?: RaceInfo; send: (m: Record<string, any>) => void }) {
  if (!race) return null;
  return (
    <div className="replay-bar">
      <span className="badge">{race.status === 'paused' ? 'Dijeda' : race.status === 'done' ? 'Selesai' : 'Berjalan'}</span>
      <span className="hint">Candle {race.stepN} / {race.stepsTotal} · maju otomatis tiap {fmtNum(race.speed, 1)} detik</span>
      {race.isHost && race.status !== 'done' && (
        <>
          {race.status === 'paused' ? (
            <button className="btn primary" type="button" onClick={() => send({ type: 'race_resume' })}>▶ Lanjut</button>
          ) : (
            <button className="btn" type="button" onClick={() => send({ type: 'race_pause' })}>⏸ Jeda</button>
          )}
          <label className="speed" htmlFor="rspd">
            Detik/candle
            <select id="rspd" value={race.speed} onChange={(e) => send({ type: 'race_speed', speed: Number(e.target.value) })}>
              {[0.5, 1, 2, 3, 5, 8, 12].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
        </>
      )}
    </div>
  );
}

function RaceBoard({ race }: { race: RaceInfo }) {
  return (
    <div className="panel race-board">
      <h3>Klasemen langsung</h3>
      <ol>
        {race.board.map((b, i) => (
          <li key={b.id} className={`${b.id === race.myId ? 'me' : ''} ${b.online ? '' : 'off'}`}>
            <span className="rk">{i + 1}</span>
            <span className="nm">{b.name}{b.in_market ? (b.side === 'short' ? ' ▼' : b.side === 'long' ? ' ▲' : ' ●') : ''}{b.n_liq ? ' 💥' : ''}</span>
            <b className={b.return_pct >= 0 ? 'up' : 'down'}>{fmtPct(b.return_pct)}</b>
          </li>
        ))}
      </ol>
      <p className="hint">● / ▲ = sedang memegang aset (long), ▼ = short, 💥 = pernah terlikuidasi. Posisi dan order lawan tidak terlihat.</p>
    </div>
  );
}
