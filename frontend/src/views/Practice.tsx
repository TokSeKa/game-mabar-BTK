import { useEffect, useState } from 'react';
import { getTemplates, runPractice } from '../api';
import { BotEditor } from '../editor/BotEditor';
import { Replay } from '../replay/Replay';
import { KEYS, load, save, type SavedBot } from '../storage';
import type { BotErrorInfo, LogEntry, MatchData, MatchSettings, Template } from '../types';
import { BotLog } from './BotLog';
import { DebugPanel, EventSelect } from './SuitExtras';

interface Props {
  bot: SavedBot;
  setBot: (b: SavedBot) => void;
}

interface PracticePrefs {
  lawan: string[];
  settings: MatchSettings;
}

const DEFAULT_PREFS: PracticePrefs = {
  lawan: ['anti_mayoritas', 'pemutar', 'minoritas', 'pembalas'],
  settings: { hp_awal: 1000, hp_kalah: 100, ronde_maks: 100, ingatan: 10, event: 'normal' },
};

export function Practice({ bot, setBot }: Props) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [prefs, setPrefs] = useState<PracticePrefs>(() => load(KEYS.practice, DEFAULT_PREFS));
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<{ match: MatchData; log: LogEntry[]; key: number } | null>(null);
  const [err, setErr] = useState<BotErrorInfo | string | null>(null);
  const [ronde, setRonde] = useState(1);

  useEffect(() => {
    getTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, []);
  useEffect(() => save(KEYS.practice, prefs), [prefs]);

  const toggle = (id: string) => {
    const has = prefs.lawan.includes(id);
    if (!has && prefs.lawan.length >= 7) return;
    setPrefs({ ...prefs, lawan: has ? prefs.lawan.filter((x) => x !== id) : [...prefs.lawan, id] });
  };

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await runPractice({ code: bot.code, nama: load<string>(KEYS.name, '') || 'Botku', lawan: prefs.lawan, settings: prefs.settings });
      if (r.ok) {
        setRes({ match: r.match, log: r.my_log, key: Date.now() });
        setTimeout(() => document.getElementById('practice-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
      } else setErr(r.error);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const setNum = (k: keyof MatchSettings, v: number) => setPrefs({ ...prefs, settings: { ...prefs.settings, [k]: v } });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="room-grid">
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 14, minWidth: 0 }}>
          <div className="panel">
            <h3>Lawan latihan ({prefs.lawan.length}/7)</h3>
            <p className="hint">Pilih bot contoh yang jadi lawanmu. Satu bot boleh dipilih sekali.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {templates.map((t) => (
                <label key={t.id} className="row" style={{ gap: 8, fontSize: 14 }} htmlFor={`opp-${t.id}`}>
                  <input id={`opp-${t.id}`} type="checkbox" checked={prefs.lawan.includes(t.id)} onChange={() => toggle(t.id)} />
                  <span><b>{t.nama}</b> <span className="hint">· {t.level}</span></span>
                </label>
              ))}
            </div>
          </div>
          <div className="panel">
            <h3>Aturan latihan</h3>
            <div className="fields">
              <label className="field" htmlFor="pr-hp">HP awal<input id="pr-hp" type="number" min={100} max={100000} step={100} value={prefs.settings.hp_awal} onChange={(e) => setNum('hp_awal', +e.target.value)} /></label>
              <label className="field" htmlFor="pr-loss">HP hilang saat kalah<input id="pr-loss" type="number" min={1} max={100000} step={10} value={prefs.settings.hp_kalah} onChange={(e) => setNum('hp_kalah', +e.target.value)} /></label>
              <label className="field" htmlFor="pr-max">Batas ronde<input id="pr-max" type="number" min={1} max={300} value={prefs.settings.ronde_maks} onChange={(e) => setNum('ronde_maks', +e.target.value)} /></label>
              <label className="field" htmlFor="pr-mem">Ingatan bot (ronde)<input id="pr-mem" type="number" min={1} max={50} value={prefs.settings.ingatan} onChange={(e) => setNum('ingatan', +e.target.value)} /></label>
              <EventSelect id="pr-event" value={prefs.settings.event ?? 'normal'} onChange={(v) => setPrefs({ ...prefs, settings: { ...prefs.settings, event: v } })} />
            </div>
          </div>
        </aside>
        <section style={{ minWidth: 0 }}>
          <BotEditor bot={bot} onChange={setBot}>
            <button className="btn primary big" type="button" disabled={busy || !prefs.lawan.length} onClick={run}>
              {busy ? 'Menjalankan…' : 'Uji botku'}
            </button>
          </BotEditor>
          {err && (
            <div className="err-box" style={{ marginTop: 10 }}>
              {typeof err === 'string' ? err : `${err.baris ? `Baris ${err.baris}: ` : ''}${err.pesan}`}
            </div>
          )}
        </section>
      </div>
      {res && (
        <div id="practice-result" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Replay key={res.key} match={res.match} myIndex={0} onRound={setRonde} />
          <DebugPanel match={res.match} myIndex={0} code={bot.code} ronde={ronde} />
          <BotLog log={res.log} />
        </div>
      )}
    </div>
  );
}
