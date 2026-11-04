import { useEffect, useMemo, useState } from 'react';
import { load, save } from '../storage';
import { FrameReplay } from './FrameReplay';
import { CopyHubGuide, HubBotLog, HubBotPanel, loadBotCode } from './HubBotPanel';
import { HubRoom, RulesText, type HubEntry } from './HubRoom';
import {
  fmt, getGames, getLiga, getPanduan, HUB_KEYS, KATEGORI_LABEL, latihan, loadSession, seatColor,
  type GameMeta, type LatihanResult, type LigaRow,
} from './hubApi';
import { defaultSettings, SettingsForm } from './SettingsForm';
import './hub.css';

export type GameTab = 'main' | 'latihan' | 'panduan' | 'liga';
export type MabarRoute =
  | { page: 'home'; kode?: string }
  | { page: 'game'; gid: string; tab: GameTab }
  | { page: 'room'; entry: HubEntry; key: number };

export const GAME_ART: Record<string, string> = {
  suit: '✊✌️✋', poker: '🂡🃁', kapal: '🚢💥', robot: '🤖◆', kartu: '🃏🐉', tycoon: '🍢🧋',
  lelang: '🔨💎', blotto: '🚩⚔️', kasdesa: '🏦🤝', duapertiga: '🔢🎯', farol: '🎡🏠',
};

interface Props {
  route: MabarRoute;
  go: (r: MabarRoute) => void;
  toast: (m: string, err?: boolean) => void;
}

export default function HubApp({ route, go, toast }: Props) {
  const [games, setGames] = useState<GameMeta[] | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    getGames().then(setGames).catch((e) => setErr((e as Error).message));
  }, []);
  const byId = useMemo(() => Object.fromEntries((games ?? []).map((g) => [g.id, g])), [games]);

  if (err) return <div className="err-box">Gagal memuat daftar game: {err}</div>;
  if (!games) return <div className="spinner" />;

  if (route.page === 'room') {
    return <HubRoom key={route.key} entry={route.entry} games={byId} toast={toast} onExit={(m) => { go({ page: 'home' }); if (m) toast(m, true); }} />;
  }
  if (route.page === 'game' && byId[route.gid]) {
    return <GamePage key={route.gid} meta={byId[route.gid]} tab={route.tab} go={go} toast={toast} />;
  }
  return <HubHome games={games} go={go} initialCode={route.page === 'home' ? route.kode : undefined} />;
}

/* ================================================================== beranda hub */
function useName(): [string, (n: string) => void] {
  const [name, setName] = useState(() => load<string>(HUB_KEYS.nama, '') || load<string>('sba-name', ''));
  return [name, (n: string) => {
    setName(n);
    save(HUB_KEYS.nama, n);
  }];
}

function HubHome({ games, go, initialCode }: { games: GameMeta[]; go: (r: MabarRoute) => void; initialCode?: string }) {
  const [name, setName] = useName();
  const [code, setCode] = useState(initialCode ?? '');
  const session = loadSession();
  const join = (tonton: boolean) => {
    if (code.trim().length !== 5) return;
    go({ page: 'room', entry: { action: 'gabung', kode: code.trim().toUpperCase(), nama: name.trim() || 'Tamu', tonton }, key: Date.now() });
  };
  return (
    <div className="hub-home">
      <section className="hub-hero">
        <div>
          <h1>Arena <span className="w2">Mabar</span></h1>
          <p>
            {games.length} game untuk main bareng teman. Setiap kursi boleh diisi <b>manusia</b> (main langsung) atau <b>bot</b> buatanmu sendiri,
            dan boleh dicampur. Semua bot ditulis dengan Python sederhana tanpa keacakan, jadi strategi yang menang.
          </p>
        </div>
        <div className="panel join-card">
          <label className="field">Namamu
            <input className="input" value={name} maxLength={16} onChange={(e) => setName(e.target.value)} placeholder="Nama (1-16 huruf)" />
          </label>
          <label className="field">Kode room
            <input className="input code-input" value={code} maxLength={5} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="ABCDE" />
          </label>
          <div className="row">
            <button type="button" className="btn primary" disabled={code.trim().length !== 5} onClick={() => join(false)}>Gabung</button>
            <button type="button" className="btn" disabled={code.trim().length !== 5} onClick={() => join(true)}>Tonton saja</button>
          </div>
          {session && (
            <button type="button" className="btn small" onClick={() => go({ page: 'room', entry: { action: 'kembali', session }, key: Date.now() })}>
              ↩ Kembali ke room {session.kode}
            </button>
          )}
          <p className="hint">Untuk membuat room, pilih game di bawah.</p>
        </div>
      </section>
      <div className="hub-grid">
        {games.map((g) => (
          <button key={g.id} type="button" className={`hub-card hc-${g.id}`} onClick={() => go({ page: 'game', gid: g.id, tab: 'main' })}>
            <span className="hc-art" aria-hidden="true">{GAME_ART[g.id] ?? '🎲'}</span>
            <b>{g.nama}</b>
            <span className="hc-desc">{g.ringkas}</span>
            <span className="hc-tags">
              <span className="tag-mini">{g.min_pemain === g.max_pemain ? `${g.min_pemain} pemain` : `${g.min_pemain}–${g.max_pemain} pemain`}</span>
              <span className="tag-mini">{KATEGORI_LABEL[g.kategori]}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ================================================================== halaman satu game */
const TABS: [GameTab, string][] = [['main', 'Main bareng'], ['latihan', 'Latihan bot'], ['panduan', 'Panduan bot'], ['liga', 'Liga']];

function GamePage({ meta, tab, go, toast }: { meta: GameMeta; tab: GameTab; go: (r: MabarRoute) => void; toast: (m: string, err?: boolean) => void }) {
  return (
    <div className="game-page">
      <div className="row gp-head">
        <button type="button" className="btn small" onClick={() => go({ page: 'home' })}>← Semua game</button>
        <span className="gp-art" aria-hidden="true">{GAME_ART[meta.id]}</span>
        <h2>{meta.nama}</h2>
        <span className="tag-mini">{meta.min_pemain === meta.max_pemain ? `${meta.min_pemain} pemain` : `${meta.min_pemain}–${meta.max_pemain} pemain`}</span>
        <span className="tag-mini">{KATEGORI_LABEL[meta.kategori]}</span>
      </div>
      <p className="hint gp-desc">{meta.ringkas}</p>
      <div className="tabs" role="tablist">
        {TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => go({ page: 'game', gid: meta.id, tab: id })}>{label}</button>
        ))}
      </div>
      {tab === 'main' && <CreateRoom meta={meta} go={go} />}
      {tab === 'latihan' && <Practice meta={meta} toast={toast} />}
      {tab === 'panduan' && <GuidePage meta={meta} />}
      {tab === 'liga' && <Liga meta={meta} />}
    </div>
  );
}

function CreateRoom({ meta, go }: { meta: GameMeta; go: (r: MabarRoute) => void }) {
  const [name, setName] = useName();
  const [cfg, setCfg] = useState(() => defaultSettings(meta));
  const [waktu, setWaktu] = useState(meta.timer);
  const [jeda, setJeda] = useState(0.6);
  return (
    <div className="two-col">
      <div className="panel">
        <h3>Buat room baru</h3>
        <label className="field">Namamu
          <input className="input" value={name} maxLength={16} onChange={(e) => setName(e.target.value)} placeholder="Nama (1-16 huruf)" />
        </label>
        <SettingsForm meta={meta} values={cfg} onChange={setCfg} />
        <div className="fields">
          <label className="field">Waktu manusia per langkah (detik)
            <input type="number" min={3} max={300} value={waktu} onChange={(e) => setWaktu(Number(e.target.value))} />
          </label>
          <label className="field">Jeda langkah bot (detik)
            <input type="number" min={0} max={5} step={0.1} value={jeda} onChange={(e) => setJeda(Number(e.target.value))} />
          </label>
        </div>
        <button type="button" className="btn primary big" disabled={!name.trim()} onClick={() => go({
          page: 'room', key: Date.now(),
          entry: { action: 'buat', game: meta.id, nama: name.trim(), settings: cfg, waktu, jeda },
        })}>Buat room</button>
        <p className="hint">
          Setelah room dibuat, bagikan kodenya. Di lobby kamu bisa menambah bot (dari template atau kodemu), mengganti kursimu jadi bot,
          lalu mulai. Teman juga bisa menonton dan mengirim reaksi.
        </p>
      </div>
      <article className="panel guide-body">
        <h3>Cara main</h3>
        <RulesText meta={meta} />
      </article>
    </div>
  );
}

function Practice({ meta, toast }: { meta: GameMeta; toast: (m: string, err?: boolean) => void }) {
  const [code, setCode] = useState(() => loadBotCode(meta));
  const [lawan, setLawan] = useState<string[]>(() => meta.templates.slice(0, Math.max(1, Math.min(3, meta.max_pemain - 1))).map((t) => t.id));
  const [cfg, setCfg] = useState(() => defaultSettings(meta));
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<LatihanResult | null>(null);
  const maxLawan = meta.max_pemain - 1;
  const minLawan = Math.max(0, meta.min_pemain - 1);

  const run = async () => {
    setBusy(true);
    setRes(null);
    try {
      const r = await latihan({ game: meta.id, kode: code, nama: load<string>(HUB_KEYS.nama, '') || 'Botku', lawan, settings: cfg });
      setRes(r);
      if (!r.ok) toast(`Kode belum valid: ${r.error.pesan}`, true);
    } catch (e) {
      toast((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="practice-hub">
      <div className="two-col">
        <div className="panel">
          <h3>Kode botmu</h3>
          <HubBotPanel meta={meta} code={code} setCode={setCode} />
        </div>
        <div className="lobby-side">
          <div className="panel">
            <h3>Lawan ({lawan.length})</h3>
            <p className="hint">Klik template untuk menambah lawan (boleh sama lebih dari sekali), klik ✕ untuk menghapus.</p>
            <div className="row">
              {meta.templates.map((t) => (
                <button key={t.id} type="button" className="btn small" disabled={lawan.length >= maxLawan} onClick={() => setLawan([...lawan, t.id])}>+ {t.nama}</button>
              ))}
            </div>
            <ul className="players">
              {lawan.map((id, k) => (
                <li key={k}>
                  <span className="seat-dot">🤖</span>
                  <span className="pn">{meta.templates.find((t) => t.id === id)?.nama ?? id}</span>
                  <span className="tags"><button type="button" className="btn small" onClick={() => setLawan(lawan.filter((_, j) => j !== k))} aria-label="Hapus lawan">✕</button></span>
                </li>
              ))}
            </ul>
            {lawan.length < minLawan && <p className="hint">Butuh minimal {minLawan} lawan.</p>}
          </div>
          <div className="panel">
            <h3>Pengaturan</h3>
            <SettingsForm meta={meta} values={cfg} onChange={setCfg} />
          </div>
          <button type="button" className="btn primary big" disabled={busy || lawan.length < minLawan} onClick={run}>
            {busy ? 'Menjalankan…' : '▶ Jalankan latihan'}
          </button>
        </div>
      </div>
      {res?.ok && (
        <>
          <div className="panel">
            <h3>Hasil</h3>
            <ol className="board">
              {res.result.ranking.map((i, k) => (
                <li key={i} className={i === 0 ? 'me' : ''}>
                  <span className="rk">{k + 1}</span>
                  <span className="dot" style={{ ['--c' as string]: seatColor(i) }} />
                  <span className="nm">{res.names[i]}{i === 0 && <small> (botmu)</small>}</span>
                  <span className="v">{fmt(res.result.skor[i], 2)}<small>{res.result.label_skor}</small></span>
                </li>
              ))}
            </ol>
          </div>
          <FrameReplay frames={res.frames} meta={meta} names={res.names} settings={res.settings} />
          <HubBotLog name={res.names[0]} log={res.log} />
        </>
      )}
      {res && !res.ok && <div className="err-box"><b>{res.error.baris ? `Baris ${res.error.baris}` : 'Error'}</b>: {res.error.pesan}</div>}
    </div>
  );
}

function GuidePage({ meta }: { meta: GameMeta }) {
  const [html, setHtml] = useState<string | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    let alive = true;
    Promise.all([getPanduan(meta.id), import('marked')])
      .then(([md, { marked }]) => alive && setHtml(marked.parse(md, { async: false }) as string))
      .catch((e) => alive && setErr((e as Error).message));
    return () => {
      alive = false;
    };
  }, [meta.id]);
  return (
    <div className="guide" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="panel">
        <h2>Pakai AI untuk menulis bot {meta.nama}</h2>
        <p className="hint">
          Salin panduan ini, tempel ke ChatGPT/Claude/Gemini, lalu ceritakan strategi yang kamu mau dengan bahasa biasa. Tempel kode hasilnya ke
          tab Latihan bot untuk dicek dan diuji melawan template.
        </p>
        <div className="row"><CopyHubGuide gid={meta.id} className="btn primary" /></div>
      </div>
      {err && <div className="err-box">{err}</div>}
      {html == null && !err && <div className="spinner" />}
      {/* panduan dibuat server dari definisi game sendiri */}
      {html != null && <article className="guide-body panel" dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  );
}

function Liga({ meta }: { meta: GameMeta }) {
  const [rows, setRows] = useState<LigaRow[] | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    getLiga(meta.id).then((r) => setRows(r.board)).catch((e) => setErr((e as Error).message));
  }, [meta.id]);
  return (
    <div className="panel">
      <h3>Liga {meta.nama}</h3>
      <p className="hint">Rating ELO (mulai 1200) untuk pemain yang masuk akun. Dihitung dari setiap match di room, termasuk kursi yang dimainkan bot milikmu.</p>
      {err && <div className="err-box">{err}</div>}
      {rows == null && !err && <div className="spinner" />}
      {rows && rows.length === 0 && <p className="hint">Belum ada match yang tercatat.</p>}
      {rows && rows.length > 0 && (
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>#</th><th>Pemain</th><th>Rating</th><th>Match</th><th>Menang</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.username}><td>{r.rank}</td><td>{r.username}</td><td className="num">{Math.round(r.rating)}</td><td className="num">{r.games}</td><td className="num">{r.wins}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
