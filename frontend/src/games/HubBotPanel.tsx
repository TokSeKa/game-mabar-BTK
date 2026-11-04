import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react';
import { load, save } from '../storage';
import type { BotErrorInfo } from '../types';
import { copyText } from '../util';
import { getPanduan, HUB_KEYS, validasi, type GameMeta, type HubLogEntry } from './hubApi';

const CodeEditor = lazy(() => import('../editor/CodeEditor').then((m) => ({ default: m.CodeEditor })));

export function loadBotCode(meta: GameMeta): string {
  return load<string | null>(HUB_KEYS.bot(meta.id), null) ?? meta.templates[0]?.kode ?? `def ${meta.fungsi_bot}():\n    return None\n`;
}

export function saveBotCode(meta: GameMeta, code: string): void {
  save(HUB_KEYS.bot(meta.id), code);
}

type Check = { s: 'idle' } | { s: 'cek' } | { s: 'ok' } | { s: 'err'; e: BotErrorInfo } | { s: 'off' };

export function CopyHubGuide({ gid, className = 'btn' }: { gid: string; className?: string }) {
  const [msg, setMsg] = useState('');
  return (
    <button type="button" className={className} onClick={async () => {
      try {
        const ok = await copyText(await getPanduan(gid));
        setMsg(ok ? 'Tersalin!' : 'Gagal menyalin');
      } catch {
        setMsg('Gagal memuat');
      }
      window.setTimeout(() => setMsg(''), 2000);
    }}>
      {msg || '📋 Salin panduan untuk AI'}
    </button>
  );
}

/** Editor bot untuk satu game: template, kode, cek error otomatis, referensi fungsi. */
export function HubBotPanel({ meta, code, setCode, children, compact }: {
  meta: GameMeta; code: string; setCode: (c: string) => void; children?: ReactNode; compact?: boolean;
}) {
  const [check, setCheck] = useState<Check>({ s: 'idle' });
  const [showRef, setShowRef] = useState(false);
  const [showTpl, setShowTpl] = useState(!compact);

  useEffect(() => {
    setCheck({ s: 'cek' });
    const t = window.setTimeout(async () => {
      try {
        const r = await validasi(meta.id, code);
        setCheck(r.ok ? { s: 'ok' } : { s: 'err', e: r.error! });
      } catch {
        setCheck({ s: 'off' });
      }
    }, 500);
    return () => window.clearTimeout(t);
  }, [code, meta.id]);

  const update = (c: string) => {
    setCode(c);
    saveBotCode(meta, c);
  };

  return (
    <div className="editor-wrap">
      <div className="editor-bar">
        <button type="button" className={`btn small ${showTpl ? 'primary' : ''}`} onClick={() => setShowTpl(!showTpl)}>Template</button>
        <button type="button" className={`btn small ${showRef ? 'primary' : ''}`} onClick={() => setShowRef(!showRef)}>Daftar fungsi</button>
        <CopyHubGuide gid={meta.id} className="btn small" />
        <span className="spacer" />
        {check.s === 'cek' && <span className="status-pill">mengecek…</span>}
        {check.s === 'ok' && <span className="status-pill ok">✓ kode valid</span>}
        {check.s === 'err' && <span className="status-pill err">✗ ada error</span>}
        {check.s === 'off' && <span className="status-pill warn">server tidak terjangkau</span>}
      </div>
      {showTpl && (
        <div className="tpl-list">
          {meta.templates.map((t) => (
            <button key={t.id} type="button" className="tpl" onClick={() => {
              if (code.trim() && code !== t.kode && !window.confirm(`Ganti kode sekarang dengan template "${t.nama}"?`)) return;
              update(t.kode);
            }}>
              <b>{t.nama}</b>
              <span>{t.ket}</span>
            </button>
          ))}
        </div>
      )}
      {showRef && (
        <div className="lib-ref">
          {meta.lib_docs.map((d) => (
            <div key={d.nama} className="lib-item"><code>{d.tanda}</code><div>{d.ket}</div></div>
          ))}
        </div>
      )}
      <Suspense fallback={<div className="spinner" />}>
        <CodeEditor value={code} onChange={update} docs={meta.lib_docs} error={check.s === 'err' ? check.e : null} />
      </Suspense>
      {check.s === 'err' && (
        <div className="err-box"><b>{check.e.baris ? `Baris ${check.e.baris}` : 'Error'}</b>: {check.e.pesan}</div>
      )}
      <p className="hint">
        Wajib ada <code>def {meta.fungsi_bot}():</code> yang mengembalikan aksi. Info permainan diambil dengan <code>info()</code>.
        Bot tidak punya memori antar langkah dan tidak boleh memakai keacakan.
      </p>
      {children}
    </div>
  );
}

export function HubBotLog({ name, log }: { name: string; log: HubLogEntry[] }) {
  const errors = log.filter((e) => e.error).length;
  return (
    <div className="panel">
      <h3>Log bot {name}</h3>
      <p className="hint">{errors ? `${errors} langkah error (memakai aksi bawaan).` : 'Tidak ada error.'} Hanya pemilik bot yang melihat log ini.</p>
      <ol className="botlog">
        {log.map((e, i) => (
          <li key={i} className={e.error ? 'err' : ''}>
            <span className="r">#{e.langkah}</span>
            <span className="steps">{e.steps ?? 0} lgkh</span>
            <span className="msg">
              {e.error && <span className="e">{e.error.baris ? `Baris ${e.error.baris}: ` : ''}{e.error.pesan}</span>}
              {e.catatan && <span className="n"> {e.catatan}</span>}
              {e.cetak?.map((c, j) => <code key={j}>{c}</code>)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
