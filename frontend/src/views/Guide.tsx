import { useEffect, useState } from 'react';
import { marked } from 'marked';
import { getGuide } from '../api';
import { CopyGuideButton } from '../editor/BotEditor';

export function Guide() {
  const [html, setHtml] = useState<string | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    getGuide()
      .then((md) => setHtml(marked.parse(md, { async: false }) as string))
      .catch((e) => setErr((e as Error).message));
  }, []);
  return (
    <div className="guide" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="panel">
        <h2>Pakai AI untuk menulis bot</h2>
        <p className="hint">
          Salin seluruh panduan ini, tempel ke ChatGPT, Claude, atau Gemini, lalu jelaskan strategi yang kamu mau dengan bahasa biasa. Contoh:
          "Buatkan bot yang ikut senjata paling untung ronde lalu, tapi kalau HP-ku di bawah 300 pilih senjata paling sepi." Tempel kode
          hasilnya di mode kode, cek ada error atau tidak, lalu uji di arena latihan.
        </p>
        <div className="row"><CopyGuideButton className="btn primary" /></div>
      </div>
      {err && <div className="err-box">{err}</div>}
      {html == null && !err && <div className="spinner" />}
      {/* panduan berasal dari file milik server sendiri (docs/PANDUAN_BOT_LLM.md) */}
      {html != null && <article className="guide-body panel" dangerouslySetInnerHTML={{ __html: html }} />}
    </div>
  );
}
