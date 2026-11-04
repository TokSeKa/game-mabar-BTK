import { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { KEYS, load, save, type SavedBot, type Session } from './storage';
import { Home } from './views/Home';
import type { RoomEntry } from './views/Room';
import type { KilasTab } from './trading/KilasApp';
import type { GameTab, MabarRoute } from './games/HubApp';
import { ROBOT } from './replay/assets';

// game dimuat terpisah supaya halaman pertama ringan
const Practice = lazy(() => import('./views/Practice').then((m) => ({ default: m.Practice })));
const Guide = lazy(() => import('./views/Guide').then((m) => ({ default: m.Guide })));
const Room = lazy(() => import('./views/Room').then((m) => ({ default: m.Room })));
const KilasApp = lazy(() => import('./trading/KilasApp'));
const HubApp = lazy(() => import('./games/HubApp'));
const SuitLiga = lazy(() => import('./views/SuitExtras').then((m) => ({ default: m.SuitLiga })));

type View =
  | { name: 'portal' }
  | { name: 'home' | 'practice' | 'guide' | 'liga' }
  | { name: 'room'; entry: RoomEntry; key: number }
  | { name: 'pasar'; tab: KilasTab; raceCode?: string }
  | { name: 'mabar'; route: MabarRoute };

const DEFAULT_BOT: SavedBot = { mode: 'blocks', code: '', blocks: null };
const PASAR_TABS: KilasTab[] = ['main', 'harian', 'balapan', 'riwayat', 'akun', 'panduan'];

function mabarFromHash(h: string): MabarRoute | null {
  if (h === '#main') return { page: 'home' };
  const room = /^#main-room-([A-Za-z0-9]{5})$/.exec(h);
  if (room) {
    const kode = room[1].toUpperCase();
    const s = load<{ kode: string; member_id: string; token: string } | null>('mabar-sesi', null);
    if (s && s.kode === kode) return { page: 'room', entry: { action: 'kembali', session: s }, key: 1 };
    return { page: 'home', kode };
  }
  const g = /^#main-([a-z0-9_]+?)(?:-(main|latihan|panduan|liga))?$/.exec(h);
  if (g) return { page: 'game', gid: g[1], tab: (g[2] as GameTab) ?? 'main' };
  return null;
}

function mabarHash(r: MabarRoute): string {
  if (r.page === 'home') return '#main';
  if (r.page === 'game') return r.tab === 'main' ? `#main-${r.gid}` : `#main-${r.gid}-${r.tab}`;
  if (r.entry.action === 'kembali') return `#main-room-${r.entry.session.kode}`;
  if (r.entry.action === 'gabung') return `#main-room-${r.entry.kode}`;
  return '#main';
}

function hashRoom(): string {
  const m = /^#room-([A-Za-z0-9]{5})$/.exec(location.hash);
  return m ? m[1].toUpperCase() : '';
}

function viewFromHash(): View {
  const h = location.hash;
  if (h === '#suit') return { name: 'home' };
  if (h === '#latihan') return { name: 'practice' };
  if (h === '#panduan') return { name: 'guide' };
  if (h === '#liga') return { name: 'liga' };
  const race = /^#pasar-balap-([A-Za-z0-9]{5})$/.exec(h);
  if (race) return { name: 'pasar', tab: 'balapan', raceCode: race[1].toUpperCase() };
  if (h === '#pasar') return { name: 'pasar', tab: 'main' };
  const tab = h.startsWith('#pasar-') ? (h.slice(7) as KilasTab) : null;
  if (tab && PASAR_TABS.includes(tab)) return { name: 'pasar', tab };
  if (h.startsWith('#main')) {
    const route = mabarFromHash(h);
    if (route) return { name: 'mabar', route };
  }
  const code = hashRoom();
  const session = load<Session | null>(KEYS.session, null);
  if (code && session && session.code === code) return { name: 'room', entry: { action: 'rejoin', session }, key: 1 };
  if (code) return { name: 'home' };
  return { name: 'portal' };
}

function hashFor(v: View): string {
  switch (v.name) {
    case 'home': return '#suit';
    case 'practice': return '#latihan';
    case 'guide': return '#panduan';
    case 'liga': return '#liga';
    case 'pasar': return v.tab === 'main' ? '#pasar' : `#pasar-${v.tab}`;
    case 'mabar': return mabarHash(v.route);
    default: return '';
  }
}

function Portal({ go }: { go: (v: View) => void }) {
  return (
    <div className="portal">
      <h1>Pilih permainan</h1>
      <div className="portal-grid">
        <button type="button" className="game-card suit" onClick={() => go({ name: 'home' })}>
          <span className="gc-art" aria-hidden="true">
            {['#f0a24a', '#3fd0c9', '#f37aa5'].map((c) => <span key={c} className="mini-bot" style={{ ['--c' as string]: c }} dangerouslySetInnerHTML={{ __html: ROBOT }} />)}
          </span>
          <b>Suit Bot Arena</b>
          <span>Program bot batu-gunting-kertas dengan blok atau Python, lalu adu dengan bot teman sampai HP habis. 2–8 pemain.</span>
        </button>
        <button type="button" className="game-card mabar" onClick={() => go({ name: 'mabar', route: { page: 'home' } })}>
          <span className="gc-art mabar-art" aria-hidden="true">🂡 🚢 🤖 🃏 🍢 🔨</span>
          <b>Arena Mabar</b>
          <span>11 game main bareng: poker, tenggelamkan kapal, robot arena, deck-builder, tycoon, lelang, dan lainnya. Setiap kursi boleh manusia atau bot, dicampur.</span>
        </button>
        <button type="button" className="game-card pasar" onClick={() => go({ name: 'pasar', tab: 'main' })}>
          <span className="gc-art candles" aria-hidden="true">
            {[38, 52, 30, 64, 46, 72, 58].map((h, i) => <i key={i} style={{ height: h, marginTop: 80 - h - (i % 2) * 6 }} className={i % 3 === 1 ? 'dn' : ''} />)}
          </span>
          <b>Kilas Pasar</b>
          <span>Simulasi trading dengan data candle asli kripto dan saham, mode buta, fee realistis. Main sendiri, tantangan harian, atau balapan bareng teman.</span>
        </button>
      </div>
    </div>
  );
}

export function App() {
  const [view, setViewState] = useState<View>(viewFromHash);
  const [bot, setBotState] = useState<SavedBot>(() => load<SavedBot>(KEYS.bot, DEFAULT_BOT));
  const [toastMsg, setToastMsg] = useState<{ text: string; err: boolean } | null>(null);

  const setBot = useCallback((b: SavedBot) => {
    setBotState(b);
    save(KEYS.bot, b);
  }, []);

  // tombol back/forward browser atau mengetik alamat #... sendiri
  useEffect(() => {
    const onHash = () => setViewState((v) => {
      const next = viewFromHash();
      if (v.name === 'room' && next.name === 'portal') return v; // jangan keluar room tanpa sengaja
      if (v.name === 'mabar' && v.route.page === 'room' && next.name === 'portal') return v;
      return next;
    });
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const toast = useCallback((text: string, err = false) => setToastMsg({ text, err }), []);
  useEffect(() => {
    if (!toastMsg) return;
    const t = setTimeout(() => setToastMsg(null), 3500);
    return () => clearTimeout(t);
  }, [toastMsg]);

  const go = useCallback((v: View) => {
    setViewState(v);
    try {
      const h = hashFor(v);
      history.replaceState(null, '', h || location.pathname + location.search);
    } catch {
      /* abaikan */
    }
    window.scrollTo(0, 0);
  }, []);

  const enterRoom = (entry: RoomEntry) => setViewState({ name: 'room', entry, key: Date.now() });
  const inSuit = view.name === 'home' || view.name === 'practice' || view.name === 'guide' || view.name === 'liga';
  const inPasar = view.name === 'pasar';
  const inMabar = view.name === 'mabar';
  const inMabarRoom = view.name === 'mabar' && view.route.page === 'room';
  const goMabar = useCallback((route: MabarRoute) => go({ name: 'mabar', route }), [go]);

  return (
    <div className={`app ${inPasar ? 'wide' : ''}`}>
      <header className="topbar">
        <button className="logo" type="button" onClick={() => view.name !== 'room' && !inMabarRoom && go({ name: 'portal' })} aria-label="Ke halaman pilih permainan">
          {inPasar ? (
            <><span className="w2">Kilas</span> <span className="w1">Pasar</span></>
          ) : inMabar ? (
            <><span className="w3">Arena</span> <span className="w2">Mabar</span></>
          ) : view.name === 'portal' ? (
            <><span className="w1">Game</span> <span className="w2">Mabar</span> <span className="w3">BTK</span></>
          ) : (
            <><span className="w1">Suit</span> <span className="w2">Bot</span> <span className="w3">Arena</span></>
          )}
        </button>
        {view.name !== 'room' && !inMabarRoom && (
          <nav className="nav" aria-label="Menu">
            <button type="button" aria-current={view.name === 'portal' ? 'page' : undefined} onClick={() => go({ name: 'portal' })}>Semua game</button>
            {inSuit && (
              <>
                <button type="button" aria-current={view.name === 'home' ? 'page' : undefined} onClick={() => go({ name: 'home' })}>Main bareng</button>
                <button type="button" aria-current={view.name === 'practice' ? 'page' : undefined} onClick={() => go({ name: 'practice' })}>Arena latihan</button>
                <button type="button" aria-current={view.name === 'guide' ? 'page' : undefined} onClick={() => go({ name: 'guide' })}>Panduan</button>
                <button type="button" aria-current={view.name === 'liga' ? 'page' : undefined} onClick={() => go({ name: 'liga' })}>Liga</button>
              </>
            )}
            {inMabar && (
              <button type="button" aria-current={view.route.page === 'home' ? 'page' : undefined} onClick={() => goMabar({ page: 'home' })}>Arena Mabar</button>
            )}
            {!inSuit && !inPasar && !inMabar && (
              <>
                <button type="button" onClick={() => go({ name: 'mabar', route: { page: 'home' } })}>Arena Mabar</button>
                <button type="button" onClick={() => go({ name: 'home' })}>Suit Bot Arena</button>
                <button type="button" onClick={() => go({ name: 'pasar', tab: 'main' })}>Kilas Pasar</button>
              </>
            )}
          </nav>
        )}
      </header>

      <Suspense fallback={<div className="spinner" />}>
        {view.name === 'portal' && <Portal go={go} />}
        {view.name === 'home' && (
          <Home
            initialCode={hashRoom()}
            session={load<Session | null>(KEYS.session, null)}
            onCreate={(name) => enterRoom({ action: 'create', name })}
            onJoin={(name, code, spectator) => enterRoom({ action: 'join', name, code, spectator })}
            onRejoin={(session) => enterRoom({ action: 'rejoin', session })}
            onPractice={() => go({ name: 'practice' })}
            onGuide={() => go({ name: 'guide' })}
          />
        )}
        {view.name === 'practice' && <Practice bot={bot} setBot={setBot} />}
        {view.name === 'guide' && <Guide />}
        {view.name === 'liga' && <SuitLiga />}
        {view.name === 'room' && (
          <Room
            key={view.key}
            entry={view.entry}
            bot={bot}
            setBot={setBot}
            toast={toast}
            onExit={(message) => {
              go({ name: 'home' });
              if (message) toast(message, true);
            }}
          />
        )}
        {view.name === 'pasar' && (
          <KilasApp tab={view.tab} raceCode={view.raceCode} toast={toast} setTab={(tab) => go({ name: 'pasar', tab })} />
        )}
        {view.name === 'mabar' && <HubApp route={view.route} go={goMabar} toast={toast} />}
      </Suspense>

      {toastMsg && (
        <div className={`toast ${toastMsg.err ? 'err' : ''}`} role="status">
          {toastMsg.text}
        </div>
      )}
    </div>
  );
}
