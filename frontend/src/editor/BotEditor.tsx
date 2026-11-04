import { useEffect, useState, type ReactNode } from 'react';
import { getGuide, getLibrary, getTemplates, validateCode } from '../api';
import type { SavedBot } from '../storage';
import type { BotErrorInfo, LibDoc, Template } from '../types';
import { BlockEditor } from './BlockEditor';
import { CodeEditor } from './CodeEditor';

export type CheckState = { state: 'checking' } | { state: 'ok' } | { state: 'err'; error: BotErrorInfo } | { state: 'offline' };

interface Props {
  bot: SavedBot;
  onChange: (b: SavedBot) => void;
  onCheck?: (c: CheckState) => void;
  children?: ReactNode;
}

export { copyText } from '../util';
import { copyText } from '../util';

export function CopyGuideButton({ className = 'btn' }: { className?: string }) {
  const [label, setLabel] = useState('Salin panduan untuk AI');
  const [fallback, setFallback] = useState<string | null>(null);
  return (
    <>
      <button
        className={className}
        type="button"
        title="Salin panduan lengkap, lalu tempel ke ChatGPT/Claude/Gemini dan jelaskan strategi yang kamu mau."
        onClick={async () => {
          try {
            const text = await getGuide();
            if (await copyText(text)) {
              setLabel('Tersalin ✓');
              setTimeout(() => setLabel('Salin panduan untuk AI'), 2000);
            } else setFallback(text);
          } catch {
            setLabel('Panduan tidak tersedia');
          }
        }}
      >
        {label}
      </button>
      {fallback != null && (
        <div className="panel" style={{ flexBasis: '100%' }}>
          <p className="hint">Browser menolak menyalin otomatis. Pilih semua teks di bawah (Ctrl+A) lalu salin.</p>
          <textarea className="input" rows={8} readOnly value={fallback} onFocus={(e) => e.currentTarget.select()} />
          <button className="btn small" type="button" onClick={() => setFallback(null)}>Tutup</button>
        </div>
      )}
    </>
  );
}

export function BotEditor({ bot, onChange, onCheck, children }: Props) {
  const [docs, setDocs] = useState<LibDoc[] | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [check, setCheck] = useState<CheckState>({ state: 'checking' });
  const [tab, setTab] = useState<'editor' | 'contoh' | 'fungsi'>('editor');
  const [confirm, setConfirm] = useState<null | { label: string; run: () => void }>(null);
  const [blocksKey, setBlocksKey] = useState(0);

  useEffect(() => {
    getLibrary().then((l) => setDocs(l.fungsi)).catch(() => setDocs([]));
    getTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, []);

  useEffect(() => {
    setCheck({ state: 'checking' });
    const t = setTimeout(async () => {
      try {
        const r = await validateCode(bot.code);
        setCheck(r.ok ? { state: 'ok' } : { state: 'err', error: r.error! });
      } catch {
        setCheck({ state: 'offline' });
      }
    }, 450);
    return () => clearTimeout(t);
  }, [bot.code]);

  useEffect(() => {
    onCheck?.(check);
  }, [check, onCheck]);

  const ask = (label: string, run: () => void) => setConfirm({ label, run });

  const pickTemplate = (tpl: Template) => {
    const apply = () => {
      onChange({ mode: 'code', code: tpl.kode, blocks: bot.blocks });
      setTab('editor');
    };
    if (bot.code.trim() && bot.code !== tpl.kode) ask(`Ganti bot sekarang dengan "${tpl.nama}"?`, apply);
    else apply();
  };

  const toCode = () => onChange({ ...bot, mode: 'code' });
  const toBlocks = () =>
    ask('Kembali ke mode blok? Perubahan yang kamu ketik di mode kode akan diganti kode dari blok.', () => {
      onChange({ ...bot, mode: 'blocks' });
      setBlocksKey((k) => k + 1);
    });
  const resetBlocks = () =>
    ask('Kosongkan blok dan mulai dari contoh awal?', () => {
      onChange({ mode: 'blocks', code: '', blocks: null });
      setBlocksKey((k) => k + 1);
    });

  const errorInfo = check.state === 'err' ? check.error : null;

  return (
    <div className="editor-wrap">
      <div className="editor-bar">
        <div className="tabs" role="tablist" aria-label="Editor bot">
          <button type="button" role="tab" aria-selected={tab === 'editor'} onClick={() => setTab('editor')}>
            {bot.mode === 'blocks' ? 'Blok' : 'Kode'}
          </button>
          <button type="button" role="tab" aria-selected={tab === 'contoh'} onClick={() => setTab('contoh')}>Contoh bot</button>
          <button type="button" role="tab" aria-selected={tab === 'fungsi'} onClick={() => setTab('fungsi')}>Daftar fungsi</button>
        </div>
        <span className="spacer" />
        {bot.mode === 'blocks' ? (
          <>
            <button className="btn small" type="button" onClick={resetBlocks}>Reset blok</button>
            <button className="btn small" type="button" onClick={toCode}>Ubah ke mode kode</button>
          </>
        ) : (
          <button className="btn small" type="button" onClick={toBlocks}>Mode blok</button>
        )}
      </div>

      {confirm && (
        <div className="row panel" role="alert">
          <span style={{ flex: '1 1 240px' }}>{confirm.label}</span>
          <button className="btn small primary" type="button" onClick={() => { confirm.run(); setConfirm(null); }}>Ya</button>
          <button className="btn small" type="button" onClick={() => setConfirm(null)}>Batal</button>
        </div>
      )}

      <div hidden={tab !== 'editor'}>
        {bot.mode === 'blocks' ? (
          <div className="editor-wrap">
            <BlockEditor
              key={blocksKey}
              initial={bot.blocks}
              onChange={(code, state) => onChange({ mode: 'blocks', code, blocks: state })}
            />
            <details>
              <summary className="hint" style={{ cursor: 'pointer' }}>Lihat kode Python dari blok ini</summary>
              <pre className="code-preview">{bot.code}</pre>
            </details>
          </div>
        ) : docs ? (
          <CodeEditor value={bot.code} onChange={(code) => onChange({ ...bot, mode: 'code', code })} docs={docs} error={errorInfo} />
        ) : (
          <div className="cm-host" />
        )}
      </div>

      {tab === 'contoh' && (
        <div className="panel">
          <p className="hint">Pilih salah satu sebagai titik awal, lalu ubah sesukamu. Bot contoh juga jadi lawan di arena latihan.</p>
          <div className="tpl-list">
            {templates.map((t) => (
              <button key={t.id} type="button" className="tpl" onClick={() => pickTemplate(t)}>
                <span className="lv">{t.level}</span>
                <b>{t.nama}</b>
                <span>{t.ket}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === 'fungsi' && (
        <div className="panel">
          <p className="hint">
            Bot ditulis sebagai fungsi <code>def pilih():</code> yang mengembalikan BATU, GUNTING, atau KERTAS. Setiap ronde bot mulai dari nol
            (tidak ada memori), jadi semua info diambil dari fungsi-fungsi ini. Tidak ada fungsi acak.
          </p>
          <div className="lib-ref">
            {(docs ?? []).map((d) => (
              <div className="lib-item" key={d.nama}>
                <code>{d.tanda}</code>
                <div>{d.ket}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <CheckBox check={check} />
      <div className="row">
        {children}
        <span className="spacer" />
        <CopyGuideButton className="btn small" />
      </div>
    </div>
  );
}

function CheckBox({ check }: { check: CheckState }) {
  if (check.state === 'checking') return <div className="status-pill">Mengecek kode…</div>;
  if (check.state === 'offline') return <div className="status-pill warn">Tidak bisa menghubungi server untuk mengecek kode.</div>;
  if (check.state === 'ok') return <div className="ok-box">Kode valid. Bot siap dipakai.</div>;
  return (
    <div className="err-box" role="status">
      {check.error.baris ? <b>Baris {check.error.baris}: </b> : null}
      {check.error.pesan}
    </div>
  );
}
