import { useState } from 'react';
import { cekKustom, type CekKustom, type KartuKustom } from './hubApi';
import { describeEvent } from './renderers';

const MAKS = 8;
const WARNA_OPT: [KartuKustom['warna'], string][] = [
  ['liar', '🌈 Liar (kapan saja, pilih warna)'], ['semua', '🎨 Semua warna (1 per warna)'],
  ['merah', '🟥 Merah'], ['kuning', '🟨 Kuning'], ['hijau', '🟩 Hijau'], ['biru', '🟦 Biru'],
];
const KOSONG: KartuKustom = {
  nama: '', simbol: '★', warna: 'liar', jumlah: 1, target: false, nilai: 50, ket: '',
  kode: 'def efek():\n    # contoh: pemain berikutnya menarik 1 kartu\n    tarik(berikutnya(), 1)\n',
};

function warnaLabel(w: string) {
  return WARNA_OPT.find(([v]) => v === w)?.[1].split(' (')[0] ?? w;
}

/**
 * Editor kartu power kustom (Satu!): tambah dari contoh, tulis sendiri, atau tempel JSON hasil AI.
 * Setiap kartu dicek server (kompilasi + dicoba di meja contoh) sebelum masuk daftar.
 */
export function KartuEditor({ gid, value, onChange, contoh, disabled }: {
  gid: string; value: KartuKustom[]; onChange: (v: KartuKustom[]) => void; contoh: KartuKustom[]; disabled?: boolean;
}) {
  const list = Array.isArray(value) ? value : [];
  const [edit, setEdit] = useState<{ idx: number; card: KartuKustom } | null>(null);
  const [cek, setCek] = useState<CekKustom | null>(null);
  const [busy, setBusy] = useState(false);
  const [paste, setPaste] = useState<string | null>(null);
  const [msg, setMsg] = useState('');

  const put = (idx: number, card: KartuKustom) => {
    const next = [...list];
    if (idx < 0) next.push(card);
    else next[idx] = card;
    onChange(next.slice(0, MAKS));
  };

  const check = async (card: KartuKustom) => {
    setBusy(true);
    try {
      const r = await cekKustom(gid, card);
      setCek(r);
      return r;
    } catch (e) {
      const r: CekKustom = { ok: false, error: { baris: null, pesan: (e as Error).message }, kartu: null };
      setCek(r);
      return r;
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async () => {
    if (!edit) return;
    const r = await check(edit.card);
    if (r.ok && r.kartu) {
      put(edit.idx, r.kartu);
      setEdit(null);
      setMsg(`Kartu "${r.kartu.nama}" disimpan. Jangan lupa tekan Simpan aturan.`);
    }
  };

  const importJson = async () => {
    if (paste == null) return;
    let items: unknown[];
    try {
      const parsed = JSON.parse(paste.trim().replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, ''));
      items = Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      setMsg('JSON tidak bisa dibaca. Salin persis objek {...} dari jawaban AI.');
      return;
    }
    const ok: KartuKustom[] = [];
    const bad: string[] = [];
    setBusy(true);
    for (const it of items.slice(0, MAKS)) {
      try {
        const r = await cekKustom(gid, it);
        if (r.ok && r.kartu) ok.push(r.kartu);
        else bad.push(`${(it as any)?.nama ?? '?'}: ${r.error?.baris ? `baris ${r.error.baris}: ` : ''}${r.error?.pesan ?? 'tidak valid'}`);
      } catch (e) {
        bad.push((e as Error).message);
      }
    }
    setBusy(false);
    if (ok.length) onChange([...list, ...ok].slice(0, MAKS));
    setMsg(`${ok.length} kartu ditambahkan${bad.length ? `; ditolak: ${bad.join(' · ')}` : ''}.`);
    if (!bad.length) setPaste(null);
  };

  return (
    <div className="kartu-editor">
      {list.length === 0 && <p className="hint">Belum ada kartu kustom. Tambahkan dari contoh, tulis sendiri, atau minta AI (panduannya di tab Panduan bot).</p>}
      <ul className="kartu-list">
        {list.map((k, i) => (
          <li key={`${k.nama}-${i}`}>
            <span className={`mini-kartu w-${k.warna}`}>{k.simbol}</span>
            <span className="kartu-info"><b>{k.nama}</b> <small className="hint">{warnaLabel(k.warna)} ×{k.jumlah}{k.target ? ' · bertarget' : ''} · {k.nilai} poin</small>
              {k.ket && <small className="hint">{k.ket}</small>}</span>
            {!disabled && (
              <span className="row">
                <button type="button" className="btn small" onClick={() => { setEdit({ idx: i, card: { ...k } }); setCek(null); }}>✏️</button>
                <button type="button" className="btn small" aria-label={`Hapus ${k.nama}`} onClick={() => onChange(list.filter((_, j) => j !== i))}>🗑️</button>
              </span>
            )}
          </li>
        ))}
      </ul>
      {!disabled && !edit && (
        <div className="row kartu-actions">
          <select className="input" value="" disabled={list.length >= MAKS} onChange={(e) => {
            const c = contoh.find((x) => x.nama === e.target.value);
            if (c) { put(-1, { ...c }); setMsg(`Kartu "${c.nama}" ditambahkan.`); }
          }}>
            <option value="">+ Tambah dari contoh…</option>
            {contoh.map((c) => <option key={c.nama} value={c.nama}>{c.simbol} {c.nama}: {c.ket}</option>)}
          </select>
          <button type="button" className="btn small" disabled={list.length >= MAKS} onClick={() => { setEdit({ idx: -1, card: { ...KOSONG } }); setCek(null); }}>✍️ Tulis kartu</button>
          <button type="button" className="btn small" disabled={list.length >= MAKS} onClick={() => setPaste(paste == null ? '' : null)}>📋 Tempel JSON</button>
        </div>
      )}
      {paste != null && !disabled && (
        <div className="kartu-form">
          <textarea className="input code" rows={6} value={paste} placeholder='{"nama": "...", "warna": "liar", "kode": "def efek():\n    ..."}'
            onChange={(e) => setPaste(e.target.value)} />
          <div className="row"><button type="button" className="btn small primary" disabled={busy || !paste.trim()} onClick={importJson}>{busy ? 'Mengecek…' : 'Cek & tambahkan'}</button>
            <button type="button" className="btn small" onClick={() => setPaste(null)}>Batal</button></div>
        </div>
      )}
      {edit && !disabled && (
        <div className="kartu-form">
          <div className="fields">
            <label className="field"><span>Nama</span><input className="input" maxLength={24} value={edit.card.nama} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, nama: e.target.value } })} /></label>
            <label className="field"><span>Simbol</span><input className="input" maxLength={8} value={edit.card.simbol} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, simbol: e.target.value } })} /></label>
            <label className="field"><span>Warna</span>
              <select className="input" value={edit.card.warna} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, warna: e.target.value as KartuKustom['warna'] } })}>
                {WARNA_OPT.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></label>
            <label className="field"><span>Jumlah per warna</span><input type="number" min={1} max={4} value={edit.card.jumlah} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, jumlah: Number(e.target.value) } })} /></label>
            <label className="field"><span>Nilai poin</span><input type="number" min={0} max={100} value={edit.card.nilai} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, nilai: Number(e.target.value) } })} /></label>
            <label className="field inline"><input type="checkbox" checked={edit.card.target} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, target: e.target.checked } })} /> <span>Pemain memilih target</span></label>
          </div>
          <label className="field"><span>Keterangan untuk pemain</span><input className="input" maxLength={200} value={edit.card.ket} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, ket: e.target.value } })} /></label>
          <label className="field"><span>Kode efek (<code>def efek():</code>)</span>
            <textarea className="input code" rows={8} spellCheck={false} value={edit.card.kode} onChange={(e) => setEdit({ ...edit, card: { ...edit.card, kode: e.target.value } })} /></label>
          <p className="hint">Fungsi: tarik(nama, n), lewati(n), balik(), ganti_warna(w), tukar_tangan(a, b), buang(nama, n), beri(dari, ke, n), putar_tangan(),
            giliran_lagi(), tambah_tumpukan(n), poin(nama, n), pesan(teks), lalu pemain_ini(), target(), berikutnya(), sebelumnya(), lawan(), jumlah_kartu(nama), info().</p>
          <div className="row">
            <button type="button" className="btn small" disabled={busy} onClick={() => check(edit.card)}>{busy ? 'Mengecek…' : '🧪 Coba'}</button>
            <button type="button" className="btn small primary" disabled={busy || !edit.card.nama.trim()} onClick={saveEdit}>Cek & simpan</button>
            <button type="button" className="btn small" onClick={() => { setEdit(null); setCek(null); }}>Batal</button>
          </div>
        </div>
      )}
      {cek && (
        <div className={cek.ok ? 'kartu-cek ok' : 'kartu-cek err'}>
          {cek.ok ? (
            <>
              <b>✅ Kode jalan.</b> Dicoba di meja contoh (Kamu, Lawan1, Lawan2{cek.kartu?.target ? '; target Lawan1' : ''}):
              <ul>{(cek.contoh ?? []).map((e, k) => <li key={k}>{describeEvent(e) ?? JSON.stringify(e)}</li>)}
                {!(cek.contoh ?? []).length && <li>tidak ada efek yang terlihat</li>}</ul>
              <small className="hint">Sesudahnya: {Object.entries(cek.sesudah ?? {}).map(([n, x]) => `${n} ${x} kartu`).join(', ')} · giliran berikutnya {cek.giliran_berikut}</small>
            </>
          ) : (
            <><b>❌ {cek.error?.baris ? `Baris ${cek.error.baris}: ` : ''}{cek.error?.pesan}</b></>
          )}
        </div>
      )}
      {msg && <p className="hint">{msg}</p>}
    </div>
  );
}
