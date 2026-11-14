import { useEffect, useRef, useState } from 'react';
import { NameChip, ScoreBoard, TurnNote, idxOf, type RenderProps } from './common';

type Item = { no: number; jenis: string; nilai: number; palsu?: boolean; terbalik?: boolean; putar: number; geser: number[]; sebar: number[] };

const WARNA: Record<number, string> = {
  1000: '#7f9f62', 2000: '#8c8f99', 5000: '#a8814a', 10000: '#8a58a6', 20000: '#3f9468', 50000: '#3b6fb6', 100000: '#c9474b',
};
const rp = (x: number) => `Rp${x.toLocaleString('id-ID')}`;

/** Satu lembar/koin. Desain fiktif "Bank Mabar" (bukan tiruan uang asli). */
export function Lembar({ it, small, onClick, done }: { it: Item; small?: boolean; onClick?: () => void; done?: boolean }) {
  const cls = `hu-item ${it.jenis} ${small ? 'sm' : ''} ${it.terbalik ? 'balik' : ''} ${done ? 'done' : ''}`;
  let body;
  if (it.jenis === 'koin') {
    body = <span className={`hu-coin ${it.nilai >= 500 ? 'emas' : ''}`}><b>{it.nilai}</b><small>rupiah</small></span>;
  } else if (it.jenis === 'kupon' || it.jenis === 'mainan') {
    body = (
      <span className={`hu-note ${it.jenis}`}>
        <small className="hu-bank">{it.jenis === 'kupon' ? 'KUPON BELANJA' : 'UANG MAINAN · TIDAK BERLAKU'}</small>
        <b className="hu-val">{rp(it.nilai)}</b>
        <small className="hu-foot">{it.jenis === 'kupon' ? 'potongan harga, tukar di kasir' : 'untuk bermain pasar-pasaran'}</small>
      </span>
    );
  } else {
    body = (
      <span className="hu-note" style={{ ['--hu' as string]: WARNA[it.nilai] ?? '#777' }}>
        {!it.palsu && <i className="hu-pita" aria-hidden="true" />}
        {it.terbalik ? (
          <>
            <span className="hu-back-pattern" aria-hidden="true" />
            <small className="hu-val-sm">{it.nilai.toLocaleString('id-ID')}</small>
          </>
        ) : (
          <>
            <small className="hu-bank">BANK MABAR</small>
            <b className="hu-val">{rp(it.nilai)}</b>
            <small className="hu-foot">{(it.nilai / 1000).toLocaleString('id-ID')} RIBU RUPIAH</small>
          </>
        )}
      </span>
    );
  }
  // versi kecil (tumpukan 'sudah dihitung' / meja sebar) tidak digeser jauh supaya tidak menutupi tulisan di sekitarnya
  const style = small
    ? { transform: `rotate(${it.putar / 2 + (it.terbalik ? 180 : 0)}deg)` }
    : { transform: `translate(${(it.geser?.[0] ?? 0) * 100}%, ${(it.geser?.[1] ?? 0) * 100}%) rotate(${it.putar + (it.terbalik ? 180 : 0)}deg)` };
  if (!onClick) return <span className={cls} style={style}>{body}</span>;
  return <button type="button" className={cls} style={style} onClick={onClick} aria-label={done ? 'sudah dihitung' : 'geser lembar ini'}>{body}</button>;
}

export function RHitungUang({ view, names, me, canAct, act, replay, tunggu }: RenderProps) {
  const v = view;
  const gepok: Item[] = v.gepok ?? [];
  const [moved, setMoved] = useState<number[]>([]);
  const [jawab, setJawab] = useState('');
  const ronde = useRef(v.ronde);
  const inRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ronde.current !== v.ronde) {
      ronde.current = v.ronde;
      setMoved([]);
      setJawab('');
    }
  }, [v.ronde]);

  const myName = me != null ? names[me] : null;
  const st = myName ? v.status?.[myName] : null;
  const cooling = (tunggu ?? 0) > 0;
  const left = gepok.filter((it) => !moved.includes(it.no));
  const top = left[0];
  const lastMoved = moved.length ? gepok.find((it) => it.no === moved[moved.length - 1]) : null;
  const digits = jawab.replace(/\D/g, '');
  const submit = () => {
    if (!canAct || !digits || cooling) return;
    act({ jawab: Number(digits) });
  };
  const last = v.riwayat?.[v.riwayat.length - 1];
  const fresh = last && last.ronde === v.ronde - 1 && moved.length === 0;
  const aturan = v.aturan_aktif ?? {};

  return (
    <div className="game-grid hu">
      <div className="panel">
        <div className="row">
          <b>Gepok {v.ronde}/{v.ronde_total}</b>
          <span className="tag-mini">{v.lembar} benda</span>
          <span className="spacer" />
          {st && <span className="hint">salah {st.salah}/{v.kesempatan}</span>}
        </div>
        <ul className="rules-mini">
          {aturan.palsu && <li>✨ Uang asli punya <b>pita perak</b>. Tanpa pita = palsu, jangan dihitung.</li>}
          {aturan.kupon && <li>🎟️ Kupon belanja dan uang mainan tidak dihitung.</li>}
          {aturan.terbalik && <li>🔄 Ada lembar terbalik: angkanya kecil di sisi belakang.</li>}
          {aturan.koin && <li>🪙 Koin ikut dihitung.</li>}
        </ul>
        {fresh && (
          <div className="hu-reveal">
            Gepok {last.ronde}: <b className="gold">{rp(last.total)}</b>
            {last.abaikan ? <> · {last.abaikan} benda tidak dihitung</> : null}
            {last.urut?.length ? <> · tercepat {last.urut.slice(0, 3).join(', ')}</> : null}
            <div className="hint">{Object.entries(last.rinci).sort((a, b) => Number(b[0]) - Number(a[0])).map(([n, k]) => `${rp(Number(n))}×${k}`).join(' · ')}</div>
          </div>
        )}
        <TurnNote canAct={canAct} acted={false} replay={replay} me={me}>
          {v.tampilan === 'tumpuk' ? 'Ketuk lembar teratas untuk menggesernya, hitung, lalu ketik totalnya.' : 'Ketuk uang yang sudah kamu hitung untuk menandainya, lalu ketik totalnya.'}
        </TurnNote>
        {st?.selesai && !replay && (
          <div className="turn-note done">{st.urutan ? `✅ Benar! Kamu urutan ke-${st.urutan}. Menunggu yang lain…` : '❌ Kesempatanmu habis untuk gepok ini. Menunggu yang lain…'}</div>
        )}
        {gepok.length > 0 && !st?.selesai && (
          v.tampilan === 'sebar' ? (
            <div className="hu-table">
              {gepok.map((it) => (
                <div key={it.no} className="hu-spot" style={{ left: `${it.sebar[0] * 100}%`, top: `${it.sebar[1] * 100}%`, zIndex: it.no + 1 }}>
                  <Lembar it={it} small done={moved.includes(it.no)} onClick={canAct ? () => setMoved((m) => (m.includes(it.no) ? m.filter((x) => x !== it.no) : [...m, it.no])) : undefined} />
                </div>
              ))}
            </div>
          ) : (
            <div className="hu-piles">
              <div className="hu-pile left">
                {top ? (
                  <>
                    {left.length > 1 && <span className="hu-under" aria-hidden="true" />}
                    <Lembar key={top.no} it={top} onClick={canAct ? () => setMoved((m) => [...m, top.no]) : undefined} />
                  </>
                ) : <span className="hint">Semua sudah digeser.</span>}
                <small className="hint">belum: {left.length}</small>
              </div>
              <div className="hu-pile right">
                {lastMoved ? <Lembar key={lastMoved.no} it={lastMoved} small onClick={canAct ? () => setMoved((m) => m.slice(0, -1)) : undefined} />
                  : <span className="hu-empty">tumpukan sudah dihitung</span>}
                <small className="hint">sudah: {moved.length}{moved.length ? ' · ketuk untuk kembalikan' : ''}</small>
              </div>
            </div>
          )
        )}
        {me != null && !replay && !st?.selesai && (
          <form className="hu-answer" onSubmit={(e) => { e.preventDefault(); submit(); }}>
            <span className="hu-rp">Rp</span>
            <input ref={inRef} className="input" inputMode="numeric" autoComplete="off" placeholder="total uang"
              value={digits ? Number(digits).toLocaleString('id-ID') : ''} onChange={(e) => setJawab(e.target.value.replace(/\D/g, '').slice(0, 9))}
              aria-label="Jumlah uang" disabled={!canAct} />
            <button type="submit" className="btn primary" disabled={!canAct || !digits || cooling}>{cooling ? `⏳ ${Math.ceil(tunggu ?? 0)}` : 'Jawab'}</button>
            <button type="button" className="btn small" disabled={!canAct} onClick={() => window.confirm('Menyerah untuk gepok ini (0 poin)?') && act('lewat')}>Menyerah</button>
          </form>
        )}
        {(v.jawaban_saya ?? []).length > 0 && !st?.selesai && (
          <p className="hint">Jawabanmu yang salah: {v.jawaban_saya.map((x: number) => rp(x)).join(', ')}</p>
        )}
        <div className="hu-status">
          {names.map((n, i) => {
            const s = v.status?.[n];
            return (
              <span key={n} className={`chip ${s?.urutan ? 'win' : ''}`}>
                <NameChip name={n} idx={idxOf(names, n)} /> {s?.urutan ? `✅ #${s.urutan}` : s?.selesai ? '❌' : s?.salah ? `${s.salah}× salah` : 'menghitung…'}
              </span>
            );
          })}
        </div>
      </div>
      <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, sub: `gepok ini ${v.poin_ronde?.[n] ?? 0}` }))
        .sort((a, b) => Number(b.value) - Number(a.value))} />
    </div>
  );
}
