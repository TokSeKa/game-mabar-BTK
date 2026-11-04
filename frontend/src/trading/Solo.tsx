import { useEffect, useRef, useState } from 'react';
import { load, remove, save } from '../storage';
import { LAST_KEY, pasarApi, type Katalog, type LastSession, type SessionInfo } from './api';
import { PasarConn } from './conn';
import { fmtNum } from './format';
import { TradeScreen } from './TradeScreen';

interface Props {
  toast: (m: string, err?: boolean) => void;
}

interface SetupCfg {
  pasar: string;
  aset: string;
  tf: string;
  buta: { nama: boolean; tanggal: boolean; harga: boolean };
  modal: number;
  fee_beli: number;
  fee_jual: number;
  slippage: number;
  mulai: string;
}

export function NoData() {
  return (
    <div className="panel nodata">
      <h2>Belum ada data pasar</h2>
      <p>Game ini memakai candle asli dari pasar. Unduh dulu datanya. Pilih salah satu cara di bawah sesuai cara kamu menjalankan game:</p>
      <ul>
        <li><b>Windows + Docker:</b> klik dua kali <code>scripts\unduh-data.bat</code>, lalu pilih "Cepat".</li>
        <li><b>Mac/Linux + Docker:</b> <code>./scripts/unduh-data.sh cepat</code></li>
        <li><b>Tanpa Docker:</b> dari folder <code>backend</code>: <code>python -m app.trading.unduh semua --preset cepat</code></li>
        <li><b>Sekadar mencoba tanpa internet:</b> <code>python -m app.trading.unduh contoh</code> (data buatan, bukan pasar nyata)</li>
      </ul>
      <p className="hint">Preset "cepat" butuh beberapa menit. Preset "penuh" (semua aset, kripto 1 menit sejak 2017) butuh beberapa jam dan puluhan GB. Halaman ini otomatis membaca data baru, cukup muat ulang.</p>
    </div>
  );
}

export function Solo({ toast }: Props) {
  const [kat, setKat] = useState<Katalog | null>(null);
  const [err, setErr] = useState('');
  const [cfg, setCfg] = useState<SetupCfg | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [starting, setStarting] = useState(false);
  const [last, setLast] = useState<LastSession | null>(() => load<LastSession | null>(LAST_KEY, null));
  const connRef = useRef<PasarConn | null>(null);
  const [conn, setConn] = useState<PasarConn | null>(null);

  useEffect(() => {
    pasarApi.katalog().then(setKat).catch((e) => setErr((e as Error).message));
    return () => connRef.current?.close();
  }, []);

  useEffect(() => {
    if (!kat || cfg) return;
    const saved = load<SetupCfg | null>('kilas-setup', null);
    const markets = Object.keys(kat.pasar);
    if (!markets.length) return;
    const pasar = saved && kat.pasar[saved.pasar] ? saved.pasar : markets.includes('crypto') ? 'crypto' : markets[0];
    const spec = kat.spec[pasar];
    setCfg(saved && saved.pasar === pasar ? saved : {
      pasar, aset: '', tf: spec.tfs.includes('1h') ? '1h' : spec.tfs[0],
      buta: { nama: true, tanggal: true, harga: true }, modal: spec.modal, fee_beli: spec.fee_beli, fee_jual: spec.fee_jual,
      slippage: spec.slippage, mulai: '',
    });
  }, [kat, cfg]);

  const begin = (hello: Record<string, any>) => {
    connRef.current?.close();
    setStarting(true);
    let info: SessionInfo | null = null;
    const c = new PasarConn(() => (info?.id ? { type: 'solo_resume', id: info.id, secret: info.secret } : hello));
    c.on((m) => {
      if (m.type === 'session') {
        info = m as SessionInfo;
        setSession(info);
        setStarting(false);
        const ls = { id: info.id!, secret: info.secret!, label: info.label, mode: info.mode };
        save(LAST_KEY, ls);
        setLast(ls);
      } else if (m.type === 'summary') {
        remove(LAST_KEY);
        setLast(null);
      } else if (m.type === 'error' && !info) {
        setStarting(false);
        toast(m.message, true);
        if (hello.type === 'solo_resume') {
          remove(LAST_KEY);
          setLast(null);
        }
        c.close();
        setConn(null);
      }
    });
    connRef.current = c;
    setConn(c);
  };

  const start = () => {
    if (!cfg) return;
    save('kilas-setup', cfg);
    const config: Record<string, any> = {
      pasar: cfg.pasar, aset: cfg.aset || null, tf: cfg.tf, buta: cfg.buta, modal: cfg.modal,
      fee_beli: cfg.fee_beli, fee_jual: cfg.fee_jual, slippage: cfg.slippage,
    };
    if (!cfg.buta.tanggal && cfg.mulai) config.mulai = Math.floor(new Date(cfg.mulai + 'T00:00:00Z').getTime() / 1000);
    begin({ type: 'solo_start', config });
  };

  const exit = () => {
    connRef.current?.close();
    connRef.current = null;
    setConn(null);
    setSession(null);
  };

  if (session && conn) {
    return <TradeScreen key={session.id} conn={conn} session={session} toast={toast} onExit={exit} onAgain={() => { exit(); start(); }} />;
  }
  if (err) return <div className="err-box">{err}</div>;
  if (!kat) return <div className="spinner" />;
  if (!Object.keys(kat.pasar).length) return <NoData />;
  if (!cfg) return <div className="spinner" />;

  const market = kat.pasar[cfg.pasar];
  const spec = kat.spec[cfg.pasar];
  const asset = market?.assets.find((a) => a.id === cfg.aset);
  const tfsAvail = spec.tfs.filter((tf) => (asset ? asset.tfs.includes(tf) : market.assets.some((a) => a.tfs.includes(tf))));
  const set = (p: Partial<SetupCfg>) => setCfg({ ...cfg, ...p });
  const setMarket = (pasar: string) => {
    const s = kat.spec[pasar];
    setCfg({ ...cfg, pasar, aset: '', tf: s.tfs.includes(cfg.tf) ? cfg.tf : s.tfs.includes('1d') ? '1d' : s.tfs[0], modal: s.modal, fee_beli: s.fee_beli, fee_jual: s.fee_jual, slippage: s.slippage });
  };

  return (
    <div className="setup">
      {last && (
        <div className="panel resume">
          <span>Sesi terakhir belum selesai: <b>{last.label}</b></span>
          <button className="btn primary" type="button" onClick={() => begin({ type: 'solo_resume', id: last.id, secret: last.secret })}>Lanjutkan</button>
          <button className="btn small" type="button" onClick={() => { remove(LAST_KEY); setLast(null); }}>Buang</button>
        </div>
      )}
      <div className="setup-grid">
        <div className="panel">
          <h3>Pasar & aset</h3>
          <div className="seg wrap" role="group" aria-label="Pasar">
            {Object.values(kat.pasar).map((m) => (
              <button key={m.id} type="button" aria-pressed={cfg.pasar === m.id} onClick={() => setMarket(m.id)}>
                {m.nama} <small>({m.assets.length})</small>
              </button>
            ))}
          </div>
          <label className="field" htmlFor="s-aset">
            Aset
            <select id="s-aset" value={cfg.aset} onChange={(e) => set({ aset: e.target.value })}>
              <option value="">Acak (disarankan, supaya tidak tertebak)</option>
              {market.assets.map((a) => <option key={a.id} value={a.id}>{a.symbol} · {a.name}</option>)}
            </select>
          </label>
          <label className="field" htmlFor="s-tf">
            Timeframe chart awal (bisa diganti saat main)
            <select id="s-tf" value={cfg.tf} onChange={(e) => set({ tf: e.target.value })}>
              {tfsAvail.map((tf) => <option key={tf} value={tf}>{kat.tf_label[tf] ?? tf}</option>)}
            </select>
          </label>
          {asset && (
            <p className="hint">{fmtNum(asset.candles, 0)} candle tersimpan untuk aset ini di {asset.tfs.length} timeframe.</p>
          )}
        </div>
        <div className="panel">
          <h3>Mode buta</h3>
          <p className="hint">Sembunyikan hal yang bisa membuatmu "ingat" kejadian aslinya, supaya kamu benar-benar membaca chart.</p>
          {([['nama', 'Sembunyikan nama aset'], ['tanggal', 'Sembunyikan tanggal'], ['harga', 'Samarkan level harga']] as const).map(([k, l]) => (
            <label key={k} className="toggle" htmlFor={`b-${k}`}>
              <input id={`b-${k}`} type="checkbox" checked={cfg.buta[k]} onChange={(e) => set({ buta: { ...cfg.buta, [k]: e.target.checked } })} /> {l}
            </label>
          ))}
          {!cfg.buta.tanggal && (
            <label className="field" htmlFor="s-mulai">
              Mulai dari tanggal (kosong = acak)
              <input id="s-mulai" type="date" value={cfg.mulai} onChange={(e) => set({ mulai: e.target.value })} />
            </label>
          )}
          <p className="hint">Identitas aset dan tanggal asli dibuka di layar hasil.</p>
        </div>
        <div className="panel">
          <h3>Modal & biaya</h3>
          <div className="fields">
            <label className="field" htmlFor="s-modal">Modal ({spec.currency})<input id="s-modal" type="number" min={1} value={cfg.modal} onChange={(e) => set({ modal: Number(e.target.value) })} /></label>
            <label className="field" htmlFor="s-slip">Slippage (%)<input id="s-slip" type="number" step="0.01" min={0} max={2} value={+(cfg.slippage * 100).toFixed(4)} onChange={(e) => set({ slippage: Number(e.target.value) / 100 })} /></label>
            <label className="field" htmlFor="s-fb">Fee beli (%)<input id="s-fb" type="number" step="0.01" min={0} max={5} value={+(cfg.fee_beli * 100).toFixed(4)} onChange={(e) => set({ fee_beli: Number(e.target.value) / 100 })} /></label>
            <label className="field" htmlFor="s-fj">Fee jual (%)<input id="s-fj" type="number" step="0.01" min={0} max={5} value={+(cfg.fee_jual * 100).toFixed(4)} onChange={(e) => set({ fee_jual: Number(e.target.value) / 100 })} /></label>
          </div>
          <p className="hint">{spec.catatan_fee}</p>
          <button className="btn primary big" type="button" disabled={starting} onClick={start}>{starting ? 'Menyiapkan…' : 'Mulai sesi'}</button>
        </div>
      </div>
    </div>
  );
}
