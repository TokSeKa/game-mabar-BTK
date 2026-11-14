import { useEffect, useState } from 'react';
import { NameChip, ScoreBoard, TurnNote, idxOf, type RenderProps } from './common';

type G = { rahasia?: boolean; emoji?: string; nama?: string; foto?: string | null; kategori?: string | null };

const KAT: Record<string, string> = {
  hewan: 'hewan', makanan: 'makanan & minuman', benda: 'benda', profesi: 'profesi', tempat: 'tempat',
  kendaraan: 'kendaraan', olahraga: 'olahraga', tambahan: 'isian tambahan',
};
const JAWAB_EMO: Record<string, string> = { ya: '👍', tidak: '👎', mungkin: '🤷', mungkin_ya: '🙂', mungkin_tidak: '😕', tidak_tahu: '🤷' };

export function fotoUrl(kode: string | undefined, fid: string) {
  return kode ? `/api/main/foto/${encodeURIComponent(kode)}/${encodeURIComponent(fid)}` : '';
}

/** Gambar tebakan: foto unggahan host, emoji, atau kartu rahasia. */
export function Gambar({ g, kode, big }: { g?: G | null; kode?: string; big?: boolean }) {
  const [broken, setBroken] = useState(false);
  if (!g) return null;
  if (g.rahasia) {
    return (
      <span className={`tg-pic secret ${big ? 'big' : ''}`}>
        <span className="tg-emoji">❓</span>
        <small>{g.kategori ? `kategori: ${KAT[g.kategori] ?? g.kategori}` : 'rahasia'}</small>
      </span>
    );
  }
  const url = g.foto ? fotoUrl(kode, g.foto) : '';
  return (
    <span className={`tg-pic ${big ? 'big' : ''}`}>
      {url && !broken ? <img src={url} alt={g.nama ?? ''} onError={() => setBroken(true)} />
        : <span className="tg-emoji">{g.emoji || '🖼️'}</span>}
      <b>{g.nama}</b>
    </span>
  );
}

export function RTebakGambar({ view, names, me, canAct, act, replay, kode }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const [tanya, setTanya] = useState('');
  const [tebak, setTebak] = useState('');
  const [lihat, setLihat] = useState<string | null>(null);
  const pilihan: string[][] = v.pilihan_jawaban ?? [];
  const label = (w: string) => pilihan.find((p) => p[0] === w)?.[1] ?? w;
  const myTurn = canAct && v.giliran === myName && v.fase === 'tanya';
  const answering = canAct && v.fase === 'jawab' && (v.penjawab ?? []).includes(myName);
  useEffect(() => {
    if (myTurn) return;
    setTanya('');
    setTebak('');
  }, [myTurn]);
  const shown = lihat ?? v.giliran ?? myName ?? names[0];
  const catatan: any[] = v.catatan?.[shown] ?? [];

  return (
    <div className="game-grid tg">
      <div className="panel">
        <div className="row">
          <b>Putaran {v.putaran}/{v.maks_putaran}</b>
          <span className="tag-mini">{pilihan.length} tombol jawaban</span>
          <span className="spacer" />
          {v.giliran && <span className="hint">giliran <NameChip name={v.giliran} idx={idxOf(names, v.giliran)} /></span>}
        </div>
        <div className="tg-arena">
          {names.map((n, i) => {
            const st = v.status?.[n];
            return (
              <button type="button" key={n} className={`tg-card ${v.giliran === n ? 'turn' : ''} ${shown === n ? 'sel' : ''} ${st !== 'main' ? st : ''}`}
                onClick={() => setLihat(n)} title="Lihat papan tanya-jawabnya">
                <Gambar g={v.gambar?.[n]} kode={kode} />
                <span className="tg-who"><NameChip name={n} idx={i} />{n === myName && <small> (kamu)</small>}</span>
                <small className="tg-st">{st === 'menang' ? '🎉 menang' : st === 'kalah' ? '💀 kalah' : `salah ${v.salah?.[n] ?? 0}/${v.kesempatan}`}</small>
              </button>
            );
          })}
        </div>
        <TurnNote canAct={canAct} acted={false} replay={replay} me={me}>
          {answering ? `Jawab pertanyaan ${v.giliran}.` : 'Tanya sesuatu tentang gambarmu, atau tebak!'}
        </TurnNote>
        {v.fase === 'jawab' && (
          <div className="tg-q">
            <div className="tg-q-head">
              <Gambar g={v.gambar?.[v.giliran]} kode={kode} />
              <div>
                <small className="hint">{v.giliran} bertanya:</small>
                <p className="tg-q-text">{v.pertanyaan}</p>
                <small className="hint">sudah menjawab: {(v.sudah_jawab ?? []).join(', ') || '-'}</small>
              </div>
            </div>
            {answering && (
              <div className={`tg-answers n${pilihan.length}`}>
                {pilihan.map(([w, l]) => (
                  <button key={w} type="button" className={`btn big tg-a ${w}`} onClick={() => act({ jawab: w })}>{JAWAB_EMO[w]} {l}</button>
                ))}
              </div>
            )}
          </div>
        )}
        {myTurn && (
          <div className="tg-act">
            {v.tanya_sisa > 0 ? (
              <form className="row" onSubmit={(e) => { e.preventDefault(); act({ tanya: tanya.trim() }); }}>
                <input className="input" value={tanya} maxLength={160} placeholder="Apakah aku bisa dimakan?" onChange={(e) => setTanya(e.target.value)} />
                <button type="submit" className="btn primary">{tanya.trim() ? 'Tanya' : '🎙️ Tanya lewat suara'}</button>
              </form>
            ) : <p className="hint">Jatah pertanyaan giliran ini habis: tebak atau akhiri giliran.</p>}
            <form className="row" onSubmit={(e) => { e.preventDefault(); if (tebak.trim()) act({ tebak: tebak.trim() }); }}>
              <input className="input" value={tebak} maxLength={60} placeholder="Tebakanku: aku adalah…" onChange={(e) => setTebak(e.target.value)} />
              <button type="submit" className="btn" disabled={!tebak.trim()}>Tebak ({(v.kesempatan ?? 0) - (v.salah?.[myName!] ?? 0)} kesempatan)</button>
              <button type="button" className="btn small" onClick={() => act('lewat')}>Akhiri giliran</button>
            </form>
          </div>
        )}
        <div className="tg-notes">
          <div className="row">
            <h3>Papan tanya-jawab</h3>
            <select className="input" value={shown} onChange={(e) => setLihat(e.target.value)} aria-label="Papan milik">
              {names.map((n) => <option key={n} value={n}>{n}{n === myName ? ' (kamu)' : ''}</option>)}
            </select>
          </div>
          {catatan.length === 0 ? <p className="hint">Belum ada pertanyaan.</p> : (
            <ol className="tg-list">
              {catatan.map((c, k) => (
                <li key={k}>
                  <span className="tg-qq">{c.tanya}</span>
                  <span className="tg-res">
                    {Object.entries(c.rangkum ?? {}).sort((a: any, b: any) => b[1] - a[1]).map(([w, x]) => (
                      <span key={w} className={`tg-ans ${w}`} title={Object.entries(c.jawaban).filter(([, ww]) => ww === w).map(([nn]) => nn).join(', ')}>
                        {JAWAB_EMO[w]} {label(w)}{Number(x) > 1 ? ` ×${x}` : ''}
                      </span>
                    ))}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
      <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, dim: v.status?.[n] === 'kalah',
        sub: v.status?.[n] === 'menang' ? `#${(v.urut_menang ?? []).indexOf(n) + 1}` : v.status?.[n] === 'kalah' ? 'kalah' : `${(v.catatan?.[n] ?? []).length} tanya` }))
        .sort((a, b) => Number(b.value) - Number(a.value))} />
    </div>
  );
}
