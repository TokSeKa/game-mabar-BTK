import { useEffect, useMemo, useRef, useState } from 'react';
import { load, save } from '../storage';
import { pasarApi, type Katalog } from './api';
import { AssetChart, EquityCharts } from './BacktestCharts';
import { btApi, type AsetChart, type Hasil, type JobStatus, type PengumpulStatus, type RiwayatRow, type StrategiMeta, type Trade } from './backtestApi';
import { fmtMoney, fmtNum, fmtPct, makeTimeFmt } from './format';

interface Props {
  toast: (m: string, err?: boolean) => void;
}

const DEFAULTS: Record<string, any> = {
  pasar: 'crypto', aset: 'semua', timeframe: '1d', mulai: '', selesai: '', mode: 'per_aset', produk: 'spot', aturan: 'nyata',
  modal: null, leverage: 1, margin: 'cross', slippage: null, fee_beli: null, fee_jual: null, fee_maker: null, fee_taker: null,
  bunga: null, biaya_pinjam: null, pemanasan: 300,
};
const tfmt = makeTimeFmt(false, 0);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

function asetText(v: any): string {
  if (Array.isArray(v)) return v.join(', ');
  return v == null || v === '' ? 'semua' : String(v);
}

function fmtRatio(v: number | null | undefined): string {
  if (v == null) return '–';
  return fmtNum(v, 2);
}

function jam(h: number | null | undefined): string {
  if (h == null) return '–';
  if (h < 48) return `${fmtNum(h, 1)} jam`;
  return `${fmtNum(h / 24, 1)} hari`;
}

export function Backtest({ toast }: Props) {
  const [info, setInfo] = useState<{ folder: string; strategi: StrategiMeta[]; pengumpul: PengumpulStatus } | null>(null);
  const [kat, setKat] = useState<Katalog | null>(null);
  const [sel, setSel] = useState<string>(() => load<string>('bt-sel', ''));
  const [form, setForm] = useState<Record<string, any>>({});
  const [par, setPar] = useState<Record<string, any>>({});
  const [job, setJob] = useState<JobStatus | null>(null);
  const [hasil, setHasil] = useState<Hasil | null>(null);
  const [riwayat, setRiwayat] = useState<RiwayatRow[]>([]);
  const [err, setErr] = useState('');
  const poll = useRef<number | undefined>();

  const refresh = () => {
    btApi.strategi().then(setInfo).catch((e) => setErr((e as Error).message));
    btApi.riwayat().then((r) => {
      setRiwayat(r.hasil);
      if (r.berjalan[0] && !job) watch(r.berjalan[0]);
    }).catch(() => undefined);
  };

  useEffect(() => {
    refresh();
    pasarApi.katalog().then(setKat).catch(() => setKat(null));
    const last = load<string>('bt-hasil', '');
    if (last) btApi.hasil(last).then(setHasil).catch(() => undefined);
    return () => window.clearTimeout(poll.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const meta = info?.strategi.find((s) => s.file === sel) ?? null;
  useEffect(() => {
    if (!meta) return;
    const saved = load<{ f: Record<string, any>; p: Record<string, any> } | null>(`bt-cfg-${meta.file}`, null);
    setForm({ ...DEFAULTS, ...meta.pengaturan, ...(saved?.f ?? {}) });
    setPar({ ...meta.parameter, ...(saved?.p ?? {}) });
  }, [meta?.file, info]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = (file: string) => {
    setSel(file);
    save('bt-sel', file);
  };

  const watch = (j: JobStatus) => {
    setJob(j);
    window.clearTimeout(poll.current);
    const tick = async () => {
      try {
        const s = await btApi.job(j.id);
        setJob(s);
        if (s.status === 'jalan') {
          poll.current = window.setTimeout(tick, 600);
          return;
        }
        if (s.status === 'selesai') {
          const h = await btApi.hasil(s.id);
          setHasil(h);
          save('bt-hasil', h.id);
          refresh();
        } else if (s.status === 'gagal') {
          toast(s.error || 'Backtest gagal.', true);
        }
      } catch (e) {
        toast((e as Error).message, true);
      }
    };
    poll.current = window.setTimeout(tick, 400);
  };

  const jalankan = async () => {
    if (!meta) return;
    save(`bt-cfg-${meta.file}`, { f: form, p: par });
    const peng: Record<string, any> = {};
    for (const [k, v] of Object.entries(form)) {
      if (v === null || v === '' || v === undefined) continue;
      peng[k] = v;
    }
    const a = String(form.aset ?? '').trim();
    peng.aset = !a || a.toLowerCase() === 'semua' ? 'semua' : a.split(/[,\s]+/).map((x) => x.trim().toUpperCase()).filter(Boolean);
    try {
      watch(await btApi.jalankan(meta.file, peng, par));
    } catch (e) {
      toast((e as Error).message, true);
    }
  };

  const reset = () => {
    if (!meta) return;
    save(`bt-cfg-${meta.file}`, null);
    setForm({ ...DEFAULTS, ...meta.pengaturan });
    setPar({ ...meta.parameter });
  };

  if (err) return <div className="err-box">{err}</div>;
  if (!info) return <div className="spinner" />;

  return (
    <div className="bt">
      <div className="bt-top">
        <StrategyList info={info} sel={sel} onPick={pick} />
        <div className="panel bt-config">
          {!meta ? (
            <p className="hint">Pilih strategi di kiri. Strategi ditulis sebagai file Python di folder <code>strategi/</code>; lihat <code>strategi/README.md</code>.</p>
          ) : (
            <>
              <div className="bt-config-head">
                <div>
                  <h3>{meta.judul || meta.nama}</h3>
                  <span className="hint"><code>{meta.file}</code></span>
                </div>
                <button type="button" className="btn small" onClick={reset} title="Kembalikan ke nilai di file">Reset</button>
              </div>
              {meta.deskripsi && <p className="bt-desc">{meta.deskripsi.split('\n').slice(1).join(' ').trim() || meta.deskripsi}</p>}
              {meta.error ? <div className="err-box">{meta.error}</div> : (
                <>
                  <SettingsForm kat={kat} form={form} setForm={setForm} />
                  <ParamForm par={par} setPar={setPar} />
                  <div className="row bt-run">
                    <button type="button" className="btn primary big" disabled={job?.status === 'jalan'} onClick={jalankan}>
                      {job?.status === 'jalan' ? 'Berjalan…' : '▶ Jalankan backtest'}
                    </button>
                    {job?.status === 'jalan' && (
                      <button type="button" className="btn small danger" onClick={() => btApi.batal(job.id).then(setJob)}>Batalkan</button>
                    )}
                  </div>
                  {job && job.status === 'jalan' && (
                    <div className="bt-progress">
                      <div className="ts-progress"><div style={{ width: `${Math.round(job.progres * 100)}%` }} /></div>
                      <span className="hint">{Math.round(job.progres * 100)}% · {job.pesan} · {fmtNum(job.durasi, 0)} dtk</span>
                    </div>
                  )}
                  {job && job.status === 'gagal' && <div className="err-box bt-err">{job.error}</div>}
                </>
              )}
            </>
          )}
        </div>
      </div>

      {hasil && <ResultView key={hasil.id} hasil={hasil} />}

      <History rows={riwayat} current={hasil?.id} onOpen={(id) => btApi.hasil(id).then((h) => { setHasil(h); save('bt-hasil', id); window.scrollTo({ top: 0, behavior: 'smooth' }); }).catch((e) => toast((e as Error).message, true))}
        onDelete={(id) => btApi.hapus(id).then(() => { if (hasil?.id === id) setHasil(null); refresh(); }).catch((e) => toast((e as Error).message, true))} />
    </div>
  );
}

// ---------------------------------------------------------------- daftar strategi
function StrategyList({ info, sel, onPick }: { info: { folder: string; strategi: StrategiMeta[]; pengumpul: PengumpulStatus }; sel: string; onPick: (f: string) => void }) {
  const pg = info.pengumpul;
  const nY = Object.values(pg.yahoo).reduce((a, b) => a + b.length, 0);
  return (
    <div className="panel bt-list">
      <h3>Strategi</h3>
      {!info.strategi.length && <p className="hint">Belum ada file strategi di <code>{info.folder}</code>.</p>}
      <ul>
        {info.strategi.map((s) => (
          <li key={s.file}>
            <button type="button" className={s.file === sel ? 'on' : ''} onClick={() => onPick(s.file)}>
              <b>{s.judul || s.nama}</b>
              <span>{s.file}{s.error ? ' · error' : ''}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="hint">Tambah strategi: salin <code>strategi/_template.py</code> jadi nama baru, edit di VS Code, lalu muat ulang halaman ini. Tidak perlu build ulang.</p>
      <div className="bt-pg">
        <span className="lbl">Data pengumpul-data</span>
        {pg.ada ? (
          <span>{nY} simbol Yahoo ({Object.keys(pg.yahoo).join(', ') || '–'}) · asing/domestik IDX {pg.idx_saham} hari · broker {pg.idx_broker} hari · tick {pg.tick.length} simbol</span>
        ) : (
          <span>Belum ada. Jalankan pengumpul di <code>anything/pengumpul-data</code> supaya VIX, forex, komoditas, dan arus asing IDX bisa dipakai strategi.</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- form pengaturan
function SettingsForm({ kat, form, setForm }: { kat: Katalog | null; form: Record<string, any>; setForm: (f: Record<string, any>) => void }) {
  const set = (p: Record<string, any>) => setForm({ ...form, ...p });
  const markets = kat ? Object.keys(kat.spec).filter((m) => m !== 'demo' || kat.pasar.demo) : ['crypto', 'idx', 'us'];
  const spec = kat?.spec[form.pasar];
  const assets = kat?.pasar[form.pasar]?.assets ?? [];
  const prods = kat?.produk?.[(form.aturan === 'bebas' ? 'bebas' : 'nyata')]?.[form.pasar] ?? {};
  const prod = form.produk !== 'spot' ? prods[form.produk] : undefined;
  const asetStr = asetText(form.aset);
  const chosen = new Set(asetStr.toLowerCase() === 'semua' ? [] : asetStr.split(/[,\s]+/).map((x) => x.trim().toUpperCase()).filter(Boolean));
  const toggleAset = (sym: string) => {
    const n = new Set(chosen);
    if (n.has(sym)) n.delete(sym);
    else n.add(sym);
    set({ aset: n.size ? [...n].join(', ') : 'semua' });
  };
  const pctIn = (k: string, label: string, step = '0.01') => (
    <label className="field" htmlFor={`bt-${k}`}>{label}
      <input id={`bt-${k}`} type="number" step={step} min={0} placeholder="default" value={form[k] == null || form[k] === '' ? '' : +(Number(form[k]) * 100).toFixed(5)}
        onChange={(e) => set({ [k]: e.target.value === '' ? null : Number(e.target.value) / 100 })} />
    </label>
  );
  return (
    <div className="bt-form">
      <div className="fields">
        <label className="field" htmlFor="bt-pasar">Pasar
          <select id="bt-pasar" value={form.pasar} onChange={(e) => set({ pasar: e.target.value, aset: 'semua', produk: 'spot', timeframe: kat?.spec[e.target.value]?.tfs.includes(form.timeframe) ? form.timeframe : '1d' })}>
            {markets.map((m) => <option key={m} value={m}>{kat?.spec[m]?.nama ?? m}{kat && !kat.pasar[m] ? ' (belum ada data)' : ''}</option>)}
          </select>
        </label>
        <label className="field" htmlFor="bt-tf">Timeframe
          <select id="bt-tf" value={form.timeframe} onChange={(e) => set({ timeframe: e.target.value })}>
            {(spec?.tfs ?? [form.timeframe]).map((tf) => <option key={tf} value={tf}>{kat?.tf_label[tf] ?? tf}</option>)}
          </select>
        </label>
        <label className="field" htmlFor="bt-mulai">Mulai
          <input id="bt-mulai" type="date" value={form.mulai ?? ''} onChange={(e) => set({ mulai: e.target.value })} />
        </label>
        <label className="field" htmlFor="bt-selesai">Selesai
          <input id="bt-selesai" type="date" value={form.selesai ?? ''} onChange={(e) => set({ selesai: e.target.value })} />
        </label>
      </div>
      <label className="field" htmlFor="bt-aset">Aset (pisahkan dengan koma, atau "semua")
        <input id="bt-aset" value={asetStr} onChange={(e) => set({ aset: e.target.value })} />
      </label>
      {assets.length > 0 && (
        <div className="bt-chips">
          {assets.slice(0, 60).map((a) => (
            <button key={a.symbol} type="button" aria-pressed={chosen.has(a.symbol)} onClick={() => toggleAset(a.symbol)} title={a.name}>{a.symbol}</button>
          ))}
          {assets.length > 60 && <span className="hint">+{assets.length - 60} lagi (ketik manual)</span>}
        </div>
      )}
      <div className="bt-segs">
        <div className="seg" role="group" aria-label="Mode">
          <button type="button" aria-pressed={form.mode === 'per_aset'} onClick={() => set({ mode: 'per_aset' })} title="Tiap aset diuji sendiri dengan modal penuh">Per aset</button>
          <button type="button" aria-pressed={form.mode === 'portofolio'} onClick={() => set({ mode: 'portofolio' })} title="Satu modal dibagi ke semua aset">Portofolio</button>
        </div>
        <div className="seg" role="group" aria-label="Produk">
          <button type="button" aria-pressed={form.produk === 'spot'} onClick={() => set({ produk: 'spot' })}>Spot</button>
          {Object.values(prods).map((p) => (
            <button key={p.id} type="button" aria-pressed={form.produk === p.id} onClick={() => set({ produk: p.id, leverage: Math.max(1, Math.min(p.max_lev, Number(form.leverage) > 1 ? Number(form.leverage) : p.default_lev)) })}>
              {p.kind === 'perp' ? 'Futures' : 'Margin + short'}
            </button>
          ))}
        </div>
        {form.pasar !== 'crypto' && (
          <label className="toggle" htmlFor="bt-aturan"><input id="bt-aturan" type="checkbox" checked={form.aturan === 'bebas'} onChange={(e) => set({ aturan: e.target.checked ? 'bebas' : 'nyata' })} /> Aturan bebas</label>
        )}
      </div>
      <div className="fields">
        <label className="field" htmlFor="bt-modal">Modal ({spec?.currency ?? ''})
          <input id="bt-modal" type="number" min={1} placeholder={spec ? String(spec.modal) : ''} value={form.modal ?? ''} onChange={(e) => set({ modal: e.target.value === '' ? null : Number(e.target.value) })} />
        </label>
        {form.produk !== 'spot' && (
          <label className="field" htmlFor="bt-lev">Leverage (maks {prod?.max_lev ?? '?'}×)
            <input id="bt-lev" type="number" min={1} max={prod?.max_lev ?? 125} step={1} value={form.leverage ?? 1} onChange={(e) => set({ leverage: Number(e.target.value) || 1 })} />
          </label>
        )}
        {form.produk === 'futures' && (
          <label className="field" htmlFor="bt-margin">Mode margin
            <select id="bt-margin" value={form.margin ?? 'cross'} onChange={(e) => set({ margin: e.target.value })}>
              <option value="cross">Cross</option>
              <option value="isolated">Isolated</option>
            </select>
          </label>
        )}
      </div>
      <details className="rules">
        <summary>Fee, slippage & lanjutan (kosong = default pasar{prod ? ` / ${prod.nama}` : ''})</summary>
        <div className="fields">
          {pctIn('slippage', 'Slippage (%)')}
          {form.produk === 'futures' ? (<>{pctIn('fee_maker', 'Fee maker (%)', '0.001')}{pctIn('fee_taker', 'Fee taker (%)', '0.001')}</>) : (<>{pctIn('fee_beli', 'Fee beli (%)')}{pctIn('fee_jual', 'Fee jual (%)')}</>)}
          {form.produk === 'margin' && (<>{pctIn('bunga', 'Bunga margin (%/thn)', '0.1')}{pctIn('biaya_pinjam', 'Pinjam saham (%/thn)', '0.1')}</>)}
          <label className="field" htmlFor="bt-warm">Candle pemanasan
            <input id="bt-warm" type="number" min={0} value={form.pemanasan ?? 300} onChange={(e) => set({ pemanasan: Number(e.target.value) })} />
          </label>
        </div>
        <p className="hint">
          Default: {form.produk === 'futures' && prod ? `maker ${fmtNum((prod.maker ?? 0) * 100, 3)}% / taker ${fmtNum(prod.fee_beli * 100, 3)}%, funding ${fmtNum(prod.funding * 100, 4)}%/8 jam (atau data asli)` :
            prod ? `beli ${fmtNum(prod.fee_beli * 100, 3)}% / jual ${fmtNum(prod.fee_jual * 100, 3)}%, bunga ${fmtNum(prod.interest_apr * 100, 2)}%/thn` :
              spec ? `beli ${fmtNum(spec.fee_beli * 100, 3)}% / jual ${fmtNum(spec.fee_jual * 100, 3)}%` : ''}
          {spec ? `, slippage ${fmtNum(spec.slippage * 100, 3)}%.` : ''} Candle pemanasan dipakai untuk menghitung indikator sebelum tanggal mulai.
        </p>
      </details>
    </div>
  );
}

function ParamForm({ par, setPar }: { par: Record<string, any>; setPar: (p: Record<string, any>) => void }) {
  const keys = Object.keys(par);
  if (!keys.length) return null;
  return (
    <div className="bt-params">
      <span className="lbl">Parameter</span>
      <div className="fields">
        {keys.map((k) => {
          const v = par[k];
          if (typeof v === 'boolean') {
            return <label key={k} className="toggle" htmlFor={`bp-${k}`}><input id={`bp-${k}`} type="checkbox" checked={v} onChange={(e) => setPar({ ...par, [k]: e.target.checked })} /> {k}</label>;
          }
          if (typeof v === 'number') {
            return (
              <label key={k} className="field" htmlFor={`bp-${k}`}>{k}
                <input id={`bp-${k}`} type="number" step={Number.isInteger(v) ? 1 : 'any'} value={v} onChange={(e) => setPar({ ...par, [k]: e.target.value === '' ? 0 : Number(e.target.value) })} />
              </label>
            );
          }
          return (
            <label key={k} className="field" htmlFor={`bp-${k}`}>{k}
              <input id={`bp-${k}`} value={Array.isArray(v) ? v.join(', ') : String(v ?? '')} onChange={(e) => setPar({ ...par, [k]: Array.isArray(v) ? e.target.value.split(',').map((x) => x.trim()).filter(Boolean) : e.target.value })} />
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- hasil
function Metric({ label, value, cls, sub }: { label: string; value: string; cls?: string; sub?: string }) {
  return <div><span>{label}</span><b className={cls}>{value}</b>{sub && <em>{sub}</em>}</div>;
}

const sign = (v: number | null | undefined) => (v == null ? '' : v >= 0 ? 'up' : 'down');

function ResultView({ hasil }: { hasil: Hasil }) {
  const r = hasil.ringkasan;
  const cur = hasil.currency;
  const [logScale, setLogScale] = useState(false);
  const [asset, setAsset] = useState<string>(hasil.aset[0] ?? '');
  const [chart, setChart] = useState<AsetChart | null>(null);
  const [loadingChart, setLoadingChart] = useState(false);
  const [sortKey, setSortKey] = useState<string>(hasil.mode === 'per_aset' ? 'return_pct' : 'laba');
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(0);
  const p = hasil.pengaturan;
  const beat = (r.return_pct ?? 0) > (r.buy_hold_pct ?? 0);

  useEffect(() => {
    if (!asset) return;
    setLoadingChart(true);
    btApi.aset(hasil.id, asset).then(setChart).catch(() => setChart(null)).finally(() => setLoadingChart(false));
  }, [hasil.id, asset]);

  const rows = useMemo(() => {
    const k = sortKey as keyof (typeof hasil.per_aset)[0];
    return [...hasil.per_aset].sort((a, b) => ((b[k] as number) ?? -1e18) - ((a[k] as number) ?? -1e18));
  }, [hasil, sortKey]);
  const trades = useMemo(() => [...hasil.transaksi].reverse().filter((t) => !filter || t.sym === filter), [hasil, filter]);
  const PAGE = 100;
  const pages = Math.max(1, Math.ceil(trades.length / PAGE));
  const span = hasil.kurva.length ? `${tfmt.full(hasil.kurva[0][0]).slice(0, 11)} → ${tfmt.full(hasil.kurva[hasil.kurva.length - 1][0]).slice(0, 11)}` : '';

  return (
    <div className="panel bt-result">
      <div className="bt-res-head">
        <div>
          <h2 className={sign(r.return_pct)}>{fmtPct(r.return_pct)}</h2>
          <p>
            <b>{hasil.judul}</b> · {hasil.pasar_nama} {hasil.timeframe} · {hasil.mode === 'per_aset' ? `per aset (${hasil.aset.length} aset, rata-rata)` : `portofolio ${hasil.aset.length} aset`}
            {' '}· {p.produk === 'futures' ? `futures ${p.leverage}× ${p.margin}` : p.produk === 'margin' ? `margin ${p.leverage}×` : 'spot'} · {span}
          </p>
          <p className="hint">
            {beat ? 'Mengalahkan' : 'Kalah dari'} beli-lalu-tahan ({fmtPct(r.buy_hold_pct)}). Parameter: {Object.entries(hasil.parameter).map(([k, v]) => `${k}=${Array.isArray(v) ? v.join('/') : v}`).join(', ') || '–'}
            {' '}· dihitung {fmtNum(hasil.durasi_detik, 1)} dtk
          </p>
        </div>
      </div>
      {hasil.peringatan.length > 0 && (
        <div className="bt-warn">{hasil.peringatan.map((w, i) => <p key={i}>⚠ {w}</p>)}</div>
      )}
      <div className="sum-grid bt-metrics">
        <Metric label="Ekuitas akhir" value={fmtMoney(r.equity, cur)} sub={`modal ${fmtMoney(r.modal, cur)}`} />
        <Metric label="CAGR" value={fmtPct(r.cagr_pct)} cls={sign(r.cagr_pct)} />
        <Metric label="Max drawdown" value={fmtPct(r.max_dd_pct == null ? null : -r.max_dd_pct)} cls="down" sub={r.dd_terlama_hari ? `terlama ${fmtNum(r.dd_terlama_hari, 0)} hari` : undefined} />
        <Metric label="Sharpe / Sortino" value={`${fmtRatio(r.sharpe)} / ${fmtRatio(r.sortino)}`} sub={`Calmar ${fmtRatio(r.calmar)}`} />
        <Metric label="Transaksi" value={String(r.n_trades)} sub={`${r.n_long} long · ${r.n_short} short`} />
        <Metric label="Win rate" value={fmtPct(r.win_rate, 1, false)} sub={`profit factor ${fmtRatio(r.profit_factor)}`} />
        <Metric label="Rata-rata transaksi" value={fmtPct(r.rata_pct)} cls={sign(r.rata_pct)} sub={`untung ${fmtPct(r.rata_untung_pct)} · rugi ${fmtPct(r.rata_rugi_pct)}`} />
        <Metric label="Lama posisi" value={jam(r.rata_tahan_jam)} sub={`di pasar ${fmtPct(r.exposure_pct, 0, false)}`} />
        <Metric label="Fee" value={fmtMoney(r.fees, cur)} cls="down" />
        <Metric label={p.produk === 'margin' ? 'Bunga + pinjam saham' : 'Funding'} value={fmtMoney(p.produk === 'margin' ? r.bunga + r.biaya_pinjam : r.funding, cur)} cls={(p.produk === 'margin' ? r.bunga + r.biaya_pinjam : r.funding) > 0 ? 'down' : 'up'} />
        <Metric label="Likuidasi" value={String(r.n_likuidasi ?? 0)} cls={r.n_likuidasi ? 'down' : ''} />
        {hasil.mode === 'per_aset' ? (
          <Metric label="Aset untung" value={fmtPct(r.aset_untung_pct, 0, false)} sub={`median ${fmtPct(r.median_return_pct)}`} />
        ) : (
          <Metric label="Volatilitas/thn" value={fmtPct(r.volatilitas_pct, 1, false)} />
        )}
      </div>

      <div className="bt-sec-head">
        <h3>Kurva ekuitas {hasil.mode === 'per_aset' && hasil.aset.length > 1 ? '(rata-rata semua aset)' : ''}</h3>
        <label className="toggle" htmlFor="bt-log"><input id="bt-log" type="checkbox" checked={logScale} onChange={(e) => setLogScale(e.target.checked)} /> Skala log</label>
      </div>
      <EquityCharts kurva={hasil.kurva} log={logScale} />
      <Monthly bulanan={hasil.bulanan} />

      <h3>{hasil.mode === 'per_aset' ? 'Hasil per aset' : 'Kontribusi per aset'}</h3>
      <div className="tbl-wrap">
        <table className="tbl bt-tbl">
          <thead>
            <tr>
              <th>Aset</th>
              {hasil.mode === 'per_aset' ? (
                <>
                  <Th k="return_pct" label="Return" sortKey={sortKey} setSortKey={setSortKey} />
                  <Th k="buy_hold_pct" label="Beli-tahan" sortKey={sortKey} setSortKey={setSortKey} />
                  <Th k="max_dd_pct" label="Max DD" sortKey={sortKey} setSortKey={setSortKey} />
                  <Th k="sharpe" label="Sharpe" sortKey={sortKey} setSortKey={setSortKey} />
                </>
              ) : (
                <>
                  <Th k="laba" label="Laba/rugi" sortKey={sortKey} setSortKey={setSortKey} />
                  <Th k="buy_hold_pct" label="Beli-tahan" sortKey={sortKey} setSortKey={setSortKey} />
                </>
              )}
              <Th k="n_trades" label="Transaksi" sortKey={sortKey} setSortKey={setSortKey} />
              <Th k="win_rate" label="Win rate" sortKey={sortKey} setSortKey={setSortKey} />
              <Th k="profit_factor" label="PF" sortKey={sortKey} setSortKey={setSortKey} />
              <Th k="fees" label="Fee" sortKey={sortKey} setSortKey={setSortKey} />
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.simbol} className={x.simbol === asset ? 'sel' : ''} onClick={() => setAsset(x.simbol)}>
                <td><b>{x.simbol}</b> <span className="hint">{x.nama !== x.simbol ? x.nama : ''}</span></td>
                {hasil.mode === 'per_aset' ? (
                  <>
                    <td className={sign(x.return_pct)}>{fmtPct(x.return_pct)}</td>
                    <td className={sign(x.buy_hold_pct)}>{fmtPct(x.buy_hold_pct)}</td>
                    <td className="down">{fmtPct(x.max_dd_pct == null ? null : -x.max_dd_pct)}</td>
                    <td>{fmtRatio(x.sharpe)}</td>
                  </>
                ) : (
                  <>
                    <td className={sign(x.laba)}>{fmtMoney(x.laba, cur)}</td>
                    <td className={sign(x.buy_hold_pct)}>{fmtPct(x.buy_hold_pct)}</td>
                  </>
                )}
                <td>{x.n_trades}</td>
                <td>{fmtPct(x.win_rate, 0, false)}</td>
                <td>{fmtRatio(x.profit_factor)}</td>
                <td>{fmtMoney(x.fees, cur)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bt-sec-head">
        <h3>Chart transaksi</h3>
        <select value={asset} onChange={(e) => setAsset(e.target.value)} aria-label="Aset untuk chart">
          {hasil.aset.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        {hasil.plot.length > 0 && <span className="hint">garis: {hasil.plot.join(', ')}</span>}
      </div>
      {loadingChart && !chart ? <div className="spinner" /> : chart ? <AssetChart data={chart} /> : <p className="hint">Data chart tidak tersedia.</p>}

      <div className="bt-sec-head">
        <h3>Daftar transaksi ({hasil.n_transaksi > hasil.transaksi.length ? `${hasil.transaksi.length} terakhir dari ${hasil.n_transaksi}` : hasil.n_transaksi})</h3>
        <select value={filter} onChange={(e) => { setFilter(e.target.value); setPage(0); }} aria-label="Filter aset">
          <option value="">Semua aset</option>
          {hasil.aset.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>
      <TradeTable trades={trades.slice(page * PAGE, (page + 1) * PAGE)} cur={cur} deriv={p.produk !== 'spot'} />
      {pages > 1 && (
        <div className="row">
          <button type="button" className="btn small" disabled={page === 0} onClick={() => setPage(page - 1)}>‹</button>
          <span className="hint">halaman {page + 1} / {pages}</span>
          <button type="button" className="btn small" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>›</button>
        </div>
      )}
      {hasil.log.length > 0 && (
        <details className="rules">
          <summary>Log strategi & broker ({hasil.log.length})</summary>
          <pre className="bt-log">{hasil.log.join('\n')}</pre>
        </details>
      )}
    </div>
  );
}

function Th({ k, label, sortKey, setSortKey }: { k: string; label: string; sortKey: string; setSortKey: (k: string) => void }) {
  return <th><button type="button" className={`th-sort ${sortKey === k ? 'on' : ''}`} onClick={() => setSortKey(k)}>{label}{sortKey === k ? ' ▾' : ''}</button></th>;
}

function TradeTable({ trades, cur, deriv }: { trades: Trade[]; cur: string; deriv: boolean }) {
  if (!trades.length) return <p className="hint">Tidak ada transaksi.</p>;
  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr><th>Aset</th>{deriv && <th>Arah</th>}<th>Masuk</th><th>Keluar</th><th>Harga masuk</th><th>Harga keluar</th><th>Hasil</th><th>Laba/rugi</th>{deriv && <th>ROE</th>}<th>Fee</th></tr>
        </thead>
        <tbody>
          {trades.map((t, i) => (
            <tr key={i}>
              <td>{t.sym}</td>
              {deriv && <td className={t.side === 'short' ? 'down' : 'up'}>{t.side === 'short' ? 'Short' : 'Long'}{t.liquidated ? ' 💥' : ''}</td>}
              <td>{tfmt.full(t.entry_time)}</td>
              <td>{tfmt.full(t.exit_time)}</td>
              <td>{fmtNum(t.entry_price, t.entry_price >= 100 ? 2 : 4)}</td>
              <td>{fmtNum(t.exit_price, t.exit_price >= 100 ? 2 : 4)}</td>
              <td className={sign(t.pnl_pct)}>{fmtPct(t.pnl_pct)}</td>
              <td className={sign(t.pnl)}>{fmtMoney(t.pnl, cur)}</td>
              {deriv && <td className={sign(t.roe_pct)}>{fmtPct(t.roe_pct)}</td>}
              <td>{fmtMoney(t.fees, cur)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Monthly({ bulanan }: { bulanan: { bulan: string; return_pct: number | null }[] }) {
  if (bulanan.length < 2) return null;
  const years = new Map<string, (number | null)[]>();
  for (const m of bulanan) {
    const [y, mm] = m.bulan.split('-');
    if (!years.has(y)) years.set(y, Array(12).fill(null));
    years.get(y)![Number(mm) - 1] = m.return_pct;
  }
  const yearTotal = (vals: (number | null)[]) => (vals.reduce<number>((acc, v) => acc * (1 + (v ?? 0) / 100), 1) - 1) * 100;
  return (
    <details className="rules" open={bulanan.length <= 48}>
      <summary>Return bulanan</summary>
      <div className="tbl-wrap">
        <table className="tbl bt-month">
          <thead><tr><th>Tahun</th>{MONTHS.map((m) => <th key={m}>{m}</th>)}<th>Setahun</th></tr></thead>
          <tbody>
            {[...years.entries()].map(([y, vals]) => (
              <tr key={y}>
                <td>{y}</td>
                {vals.map((v, i) => (
                  <td key={i} style={v == null ? undefined : { background: v >= 0 ? `rgba(63,208,160,${Math.min(0.55, Math.abs(v) / 25)})` : `rgba(255,106,106,${Math.min(0.55, Math.abs(v) / 25)})` }}>
                    {v == null ? '' : fmtNum(v, 1)}
                  </td>
                ))}
                <td className={sign(yearTotal(vals))}><b>{fmtNum(yearTotal(vals), 1)}</b></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function History({ rows, current, onOpen, onDelete }: { rows: RiwayatRow[]; current?: string; onOpen: (id: string) => void; onDelete: (id: string) => void }) {
  const [confirm, setConfirm] = useState<string | null>(null);
  if (!rows.length) return null;
  return (
    <div className="panel">
      <h3>Riwayat backtest</h3>
      <div className="tbl-wrap">
        <table className="tbl bt-tbl">
          <thead><tr><th>Waktu</th><th>Strategi</th><th>Pasar</th><th>Parameter</th><th>Return</th><th>Beli-tahan</th><th>Max DD</th><th>Sharpe</th><th>Transaksi</th><th /></tr></thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id} className={x.id === current ? 'sel' : ''} onClick={() => onOpen(x.id)}>
                <td>{x.dibuat?.replace('T', ' ').slice(0, 16)}</td>
                <td><b>{x.judul}</b></td>
                <td>{x.pasar_nama} {x.timeframe} · {x.mode === 'per_aset' ? `${x.n_aset} aset` : `portofolio ${x.n_aset}`}{x.produk && x.produk !== 'spot' ? ` · ${x.produk}` : ''}</td>
                <td className="hint">{Object.entries(x.parameter ?? {}).map(([k, v]) => `${k}=${Array.isArray(v) ? v.join('/') : v}`).join(' ')}</td>
                <td className={sign(x.return_pct)}>{fmtPct(x.return_pct)}</td>
                <td className={sign(x.buy_hold_pct)}>{fmtPct(x.buy_hold_pct)}</td>
                <td className="down">{fmtPct(x.max_dd_pct == null ? null : -x.max_dd_pct)}</td>
                <td>{fmtRatio(x.sharpe)}</td>
                <td>{x.n_trades}</td>
                <td onClick={(e) => e.stopPropagation()}>
                  {confirm === x.id ? (
                    <button type="button" className="btn small danger" onClick={() => { onDelete(x.id); setConfirm(null); }}>Hapus?</button>
                  ) : (
                    <button type="button" className="btn small" aria-label="Hapus hasil" onClick={() => setConfirm(x.id)}>✕</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
