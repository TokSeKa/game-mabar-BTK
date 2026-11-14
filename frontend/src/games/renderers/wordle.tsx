import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { seatColor } from '../hubApi';
import { NameChip, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

type Row = { kata: string | null; warna: string | null; lewat?: boolean; asal?: boolean; pemain?: string };

const KEYS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
const RANK: Record<string, number> = { H: 3, K: 2, A: 1 };
const MODE: Record<string, string> = { balapan: 'Balapan', serentak: 'Serentak', gantian: 'Bergiliran' };

/** Status terbaik tiap huruf dari baris-baris yang sudah ditebak (hijau > kuning > abu-abu). */
function keyStatus(rows: Row[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const r of rows) {
    if (!r.kata || !r.warna || r.asal) continue;
    [...r.kata].forEach((ch, i) => {
      const c = r.warna![i];
      if (!out[ch] || RANK[c] > RANK[out[ch]]) out[ch] = c;
    });
  }
  return out;
}

function Tile({ ch, c, small }: { ch?: string | null; c?: string | null; small?: boolean }) {
  const cls = c === 'H' ? 'h' : c === 'K' ? 'k' : c === 'A' ? 'a' : c === '?' ? 'q' : ch ? 'typed' : '';
  return <span className={`wd-tile ${cls} ${small ? 'sm' : ''}`}>{ch ? ch.toUpperCase() : c === '?' ? '?' : ''}</span>;
}

function Grid({ rows, maks, input, small, showNames, names }: {
  rows: Row[]; maks: number; input?: string | null; small?: boolean; showNames?: boolean; names?: string[];
}) {
  const lines: ReactNode[] = rows.map((r, k) => (
    <div key={k} className={`wd-row ${r.lewat ? 'skip' : ''}`}>
      {showNames && r.pemain && <span className="wd-who"><NameChip name={r.pemain} idx={idxOf(names ?? [], r.pemain)} /></span>}
      {r.lewat
        ? <span className="wd-skip">{small ? '–' : 'baris hangus / dilewati'}</span>
        : Array.from({ length: 5 }, (_, i) => (
          <Tile key={i} small={small} ch={r.kata ? r.kata[i] : null} c={r.warna ? r.warna[i] : r.kata ? null : 'x'} />
        ))}
    </div>
  ));
  if (input != null && rows.length < maks) {
    lines.push(
      <div key="in" className="wd-row wd-in">
        {showNames && <span className="wd-who" />}
        {Array.from({ length: 5 }, (_, i) => <Tile key={i} small={small} ch={input[i] ?? null} />)}
      </div>,
    );
  }
  for (let k = lines.length; k < maks; k++) {
    lines.push(
      <div key={`e${k}`} className="wd-row empty">
        {showNames && <span className="wd-who" />}
        {Array.from({ length: 5 }, (_, i) => <Tile key={i} small={small} />)}
      </div>,
    );
  }
  return <div className={`wd-grid ${small ? 'sm' : ''}`}>{lines}</div>;
}

function Keyboard({ status, onKey, disabled, enterLabel }: {
  status: Record<string, string>; onKey: (k: string) => void; disabled: boolean; enterLabel: string;
}) {
  return (
    <div className="wd-kb" aria-label="Papan ketik">
      {KEYS.map((row, r) => (
        <div key={row} className="wd-kb-row">
          {r === 2 && <button type="button" className="wd-key wide" disabled={disabled} onClick={() => onKey('enter')}>{enterLabel}</button>}
          {[...row].map((ch) => (
            <button type="button" key={ch} className={`wd-key ${keyCls(status[ch])}`}
              disabled={disabled} onClick={() => onKey(ch)}>{ch.toUpperCase()}</button>
          ))}
          {r === 2 && <button type="button" className="wd-key wide" disabled={disabled} onClick={() => onKey('back')} aria-label="Hapus huruf">⌫</button>}
        </div>
      ))}
    </div>
  );
}

const keyCls = (c?: string) => (c === 'H' ? 'h' : c === 'K' ? 'k' : c === 'A' ? 'a' : '');

/** Petunjuk warna huruf (tidak bisa dipencet): dipakai saat mengetik dengan keyboard HP. */
function LetterHints({ status }: { status: Record<string, string> }) {
  return (
    <div className="wd-hints" aria-label="Status huruf">
      {KEYS.map((row) => (
        <div key={row} className="wd-hints-row">
          {[...row].map((ch) => <span key={ch} className={`wd-hint ${keyCls(status[ch])}`}>{ch.toUpperCase()}</span>)}
        </div>
      ))}
    </div>
  );
}

/** Semua tebakan (huruf + warna) tiap pemain untuk satu kata yang sudah selesai. */
function RoundBoards({ r, names, me }: { r: any; names: string[]; me: number | null }) {
  const papan: Record<string, Row[]> = r?.papan ?? {};
  const order = Object.keys(papan).filter((n) => n !== 'bersama')
    .sort((a, b) => (a === names[me ?? -1] ? -1 : b === names[me ?? -1] ? 1 : names.indexOf(a) - names.indexOf(b)));
  if (!order.length) return null;
  return (
    <div className="wd-round-boards">
      {order.map((n) => {
        const h = r.hasil?.[n];
        const rows = papan[n] ?? [];
        return (
          <div key={n} className={`wd-other wd-md ${h?.menang ? 'won' : 'lost'}`}>
            <div className="row"><NameChip name={n} idx={idxOf(names, n)} />
              <span className="hint">{h?.menang ? `✅ ${h.tebakan} tebakan` : '❌'} · +{h?.poin ?? 0}</span></div>
            {rows.length ? <Grid rows={rows} maks={rows.length} /> : <div className="hint">tidak menebak</div>}
          </div>
        );
      })}
    </div>
  );
}

const KB_KEY = 'mabar-wordle-keyboard';
function initialKeyboard(): 'hp' | 'layar' {
  try {
    const saved = localStorage.getItem(KB_KEY);
    if (saved === 'hp' || saved === 'layar') return saved;
  } catch { /* penyimpanan tidak tersedia */ }
  return typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches ? 'hp' : 'layar';
}

export function RWordle({ view, names, me, canAct, acted, act, replay, draft, tunggu }: RenderProps) {
  const v = view;
  const gantian = v.mode === 'gantian';
  const myName = me != null ? names[me] : null;
  const board = myName ? v.papan?.[myName] : null;
  const myRows: Row[] = gantian ? (v.bersama ?? []) : (board?.baris ?? []);
  const [input, setInput] = useResetState<string>('', `${v.ronde}-${myRows.length}`);
  const cooling = (tunggu ?? 0) > 0;
  const status = useMemo(() => keyStatus(myRows), [myRows]);

  const [kb, setKb] = useState<'hp' | 'layar'>(initialKeyboard);
  const inRef = useRef<HTMLInputElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const chooseKb = (k: 'hp' | 'layar') => {
    setKb(k);
    try { localStorage.setItem(KB_KEY, k); } catch { /* abaikan */ }
    if (k === 'hp') setTimeout(() => inRef.current?.focus(), 0);
  };

  const setText = (raw: string) => {
    if (!canAct) return;
    const next = raw.toLowerCase().replace(/[^a-z]/g, '').slice(0, 5);
    if (next === input) return;
    setInput(next);
    // kata lengkap yang terlihat di layar dikirim otomatis kalau waktu habis; selain itu baris dilewati
    draft?.(next.length === 5 ? next : '-');
  };
  const submit = () => {
    if (canAct && input.length === 5 && !cooling) act(input);
  };
  const type = (k: string) => {
    if (!canAct) return;
    if (k === 'enter') submit();
    else if (k === 'back') setText(input.slice(0, -1));
    else if (/^[a-z]$/.test(k)) setText(input + k);
  };

  useEffect(() => {
    if (!canAct) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key === 'Enter' ? 'enter' : e.key === 'Backspace' ? 'back' : e.key.length === 1 ? e.key.toLowerCase() : '';
      if (!k) return;
      e.preventDefault();
      type(k);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const last = v.riwayat?.[v.riwayat.length - 1];
  const freshRound = myRows.length === 0 && last && last.ronde === v.ronde - 1;
  const others = names.filter((n) => n !== myName);
  const enterLabel = cooling ? `⏳ ${Math.ceil(tunggu ?? 0)}` : 'TEBAK';
  const selesai = !gantian && board?.selesai;
  // kolom ketik tetap terpasang selama match (tidak dilepas sesaat setelah menebak) supaya keyboard HP tidak tertutup
  const showType = !replay && me != null && !selesai;

  return (
    <div className="game-grid wd">
      <div className="panel">
        <div className="row"><b>Kata {v.ronde}/{v.ronde_total}</b><span className="tag-mini">{MODE[v.mode] ?? v.mode}</span><span className="spacer" />
          <span className="hint">maks {v.maks_tebakan} tebakan</span></div>
        <ul className="rule-notes">
          {v.mode === 'balapan' && <li>🏁 Real-time: tebak benar di baris ke-k = {v.maks_tebakan + 1} − k poin{v.bonus_cepat ? ', tiga tercepat +3 / +2 / +1' : ''}.</li>}
          {v.hukuman_detik > 0 && <li>⏳ Tebakan salah = tunggu {v.hukuman_detik} detik sebelum menebak lagi (anti spam).</li>}
          {gantian && <li>🔁 Satu papan bersama: tebak benar +5, tebakan yang membuka huruf hijau baru +1.</li>}
          {v.mode_sulit && <li>🧩 Mode sulit: huruf hijau harus tetap, huruf kuning wajib dipakai lagi.</li>}
          {v.licik && <li>😈 Kata licik: jawabannya belum ditentukan dan selalu menghindar.</li>}
          {v.kata_asal === 'hangus' && <li>🚫 Kata di luar kamus tetap memakan satu baris (tanpa petunjuk).</li>}
          {v.kata_asal === 'bebas' && <li>Kata di luar kamus diterima.</li>}
        </ul>
        {gantian && v.giliran && <p className="hint">Giliran: <NameChip name={v.giliran} idx={idxOf(names, v.giliran)} /></p>}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>{gantian ? 'Tebak satu kata untuk papan bersama.' : 'Ketik kata 5 huruf.'}</TurnNote>
        {selesai && <div className="turn-note done">{board.menang ? `✅ Kamu menebak benar (urutan ke-${(v.urut_selesai ?? []).indexOf(myName) + 1}). Menunggu yang lain…` : '❌ Barismu habis. Menunggu yang lain…'}</div>}
        {freshRound && (
          <div className="wd-reveal">
            Kata sebelumnya: <b className="gold">{(last.jawaban ?? (myName && last.jawaban_pemain?.[myName]) ?? '?').toUpperCase()}</b>
            {last.urut?.length ? <> · tercepat {last.urut.slice(0, 3).join(', ')}</> : null}
            {!gantian && (
              <details className="wd-round-det" open>
                <summary>Tebakan semua pemain</summary>
                <RoundBoards r={last} names={names} me={me} />
              </details>
            )}
          </div>
        )}
        <div ref={boxRef} className="wd-box">
          {(gantian || me != null) && (
            <div className="wd-main" onClick={() => kb === 'hp' && canAct && inRef.current?.focus()}>
              <Grid rows={myRows} maks={v.maks_tebakan} input={canAct || acted ? input : null} showNames={gantian} names={names} />
            </div>
          )}
          {showType && kb === 'hp' && (
            <form className="wd-type" onSubmit={(e) => { e.preventDefault(); submit(); }}>
              <input ref={inRef} className="wd-input" value={input} onChange={(e) => setText(e.target.value)}
                placeholder={canAct ? 'ketik kata…' : 'tunggu giliran…'} aria-label="Ketik kata 5 huruf" maxLength={5} inputMode="text" enterKeyHint="send"
                autoComplete="off" autoCorrect="off" autoCapitalize="none" spellCheck={false}
                onFocus={() => setTimeout(() => boxRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' }), 300)} />
              <button type="submit" className="btn primary wd-send" disabled={!canAct || input.length < 5 || cooling}>{enterLabel}</button>
            </form>
          )}
        </div>
        {canAct && kb === 'layar' && <Keyboard status={status} onKey={type} disabled={!canAct} enterLabel={enterLabel} />}
        {showType && kb === 'hp' && <LetterHints status={status} />}
        {showType && (
          <p className="wd-kb-switch">
            {kb === 'hp'
              ? <button type="button" className="linklike" onClick={() => chooseKb('layar')}>⌨️ Pakai papan huruf di layar</button>
              : <button type="button" className="linklike" onClick={() => chooseKb('hp')}>📱 Pakai keyboard HP / laptop biasa</button>}
          </p>
        )}
        {!gantian && others.length > 0 && (
          <div className="wd-others">
            {others.map((n) => {
              const b = v.papan?.[n];
              if (!b) return null;
              const pos = (v.urut_selesai ?? []).indexOf(n);
              return (
                <div key={n} className={`wd-other ${b.menang ? 'won' : b.selesai ? 'lost' : ''}`}>
                  <div className="row"><NameChip name={n} idx={idxOf(names, n)} /><span className="hint">
                    {b.menang ? `✅ #${pos + 1}` : b.selesai ? '❌' : `${b.baris.length}/${v.maks_tebakan}`}</span></div>
                  {v.info_lawan === 'tidak' && !replay
                    ? <div className="hint">papan rahasia</div>
                    : <Grid rows={b.baris} maks={v.maks_tebakan} small />}
                </div>
              );
            })}
          </div>
        )}
        {(v.riwayat ?? []).length > 0 && (
          <ul className="hist">
            {(v.riwayat ?? []).slice().reverse().map((r: any) => (
              <li key={r.ronde}>
                <b>Kata {r.ronde}</b>{' '}
                {r.jawaban ? <b className="gold">{r.jawaban.toUpperCase()}</b>
                  : <span className="hint">licik: {Object.entries(r.jawaban_pemain ?? {}).map(([n, w]) => `${n} ${String(w).toUpperCase()}`).join(', ')}</span>}
                <span className="hist-chips">
                  {Object.entries(r.hasil).map(([n, h]: [string, any]) => (
                    <span key={n} className={`chip ${h.menang ? 'win' : ''}`} style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>
                      {n} {h.menang ? `✓${gantian ? '' : ` ${h.tebakan}`}` : gantian ? `${h.tebakan}×` : '✗'} <b>+{h.poin}</b>
                    </span>
                  ))}
                </span>
                {!gantian && r.papan && (
                  <details className="wd-round-det">
                    <summary>lihat tebakan</summary>
                    <RoundBoards r={r} names={names} me={me} />
                  </details>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      <ScoreBoard me={me} rows={names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, sub: `${v.tebakan_total?.[n] ?? 0} tebakan` }))
        .sort((a, b) => Number(b.value) - Number(a.value))} />
    </div>
  );
}
