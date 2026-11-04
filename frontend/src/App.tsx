import { useCallback, useEffect, useState } from 'react';
import { KEYS, load, save, type SavedBot, type Session } from './storage';
import { Guide } from './views/Guide';
import { Home } from './views/Home';
import { Practice } from './views/Practice';
import { Room, type RoomEntry } from './views/Room';

type View = { name: 'home' | 'practice' | 'guide' } | { name: 'room'; entry: RoomEntry; key: number };

const DEFAULT_BOT: SavedBot = { mode: 'blocks', code: '', blocks: null };

function hashRoom(): string {
  const m = /^#room-([A-Za-z0-9]{5})$/.exec(location.hash);
  return m ? m[1].toUpperCase() : '';
}

function initialView(): View {
  const h = location.hash;
  if (h === '#latihan') return { name: 'practice' };
  if (h === '#panduan') return { name: 'guide' };
  const code = hashRoom();
  const session = load<Session | null>(KEYS.session, null);
  if (code && session && session.code === code) return { name: 'room', entry: { action: 'rejoin', session }, key: 1 };
  return { name: 'home' };
}

export function App() {
  const [view, setView] = useState<View>(initialView);
  const [bot, setBotState] = useState<SavedBot>(() => load<SavedBot>(KEYS.bot, DEFAULT_BOT));
  const [toastMsg, setToastMsg] = useState<{ text: string; err: boolean } | null>(null);

  const setBot = useCallback((b: SavedBot) => {
    setBotState(b);
    save(KEYS.bot, b);
  }, []);

  const toast = useCallback((text: string, err = false) => setToastMsg({ text, err }), []);
  useEffect(() => {
    if (!toastMsg) return;
    const t = setTimeout(() => setToastMsg(null), 3500);
    return () => clearTimeout(t);
  }, [toastMsg]);

  const go = (name: 'home' | 'practice' | 'guide') => {
    setView({ name });
    const hash = name === 'practice' ? '#latihan' : name === 'guide' ? '#panduan' : '';
    try {
      history.replaceState(null, '', hash || location.pathname + location.search);
    } catch {
      /* abaikan */
    }
    window.scrollTo(0, 0);
  };

  const enterRoom = (entry: RoomEntry) => setView({ name: 'room', entry, key: Date.now() });

  return (
    <div className="app">
      <header className="topbar">
        <button className="logo" type="button" onClick={() => view.name !== 'room' && go('home')} aria-label="Suit Bot Arena, ke beranda">
          <span className="w1">Suit</span> <span className="w2">Bot</span> <span className="w3">Arena</span>
        </button>
        {view.name !== 'room' && (
          <nav className="nav" aria-label="Menu">
            <button type="button" aria-current={view.name === 'home' ? 'page' : undefined} onClick={() => go('home')}>Main bareng</button>
            <button type="button" aria-current={view.name === 'practice' ? 'page' : undefined} onClick={() => go('practice')}>Arena latihan</button>
            <button type="button" aria-current={view.name === 'guide' ? 'page' : undefined} onClick={() => go('guide')}>Panduan</button>
          </nav>
        )}
      </header>

      {view.name === 'home' && (
        <Home
          initialCode={hashRoom()}
          session={load<Session | null>(KEYS.session, null)}
          onCreate={(name) => enterRoom({ action: 'create', name })}
          onJoin={(name, code) => enterRoom({ action: 'join', name, code })}
          onRejoin={(session) => enterRoom({ action: 'rejoin', session })}
          onPractice={() => go('practice')}
          onGuide={() => go('guide')}
        />
      )}
      {view.name === 'practice' && <Practice bot={bot} setBot={setBot} />}
      {view.name === 'guide' && <Guide />}
      {view.name === 'room' && (
        <Room
          key={view.key}
          entry={view.entry}
          bot={bot}
          setBot={setBot}
          toast={toast}
          onExit={(message) => {
            go('home');
            if (message) toast(message, true);
          }}
        />
      )}

      {toastMsg && (
        <div className={`toast ${toastMsg.err ? 'err' : ''}`} role="status">
          {toastMsg.text}
        </div>
      )}
    </div>
  );
}
