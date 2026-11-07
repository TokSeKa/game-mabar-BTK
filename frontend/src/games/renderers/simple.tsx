import { useEffect, useMemo, type ReactNode } from 'react';
import { ICON, LABEL, SENJATA } from '../../replay/assets';
import type { Senjata } from '../../types';
import { fmt, seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, scoreRows, useResetState, type RenderProps } from './common';

/* ------------------------------------------------------------------ Angka Dua Pertiga */
const MEDALI: Record<number, string> = { 3: '🥇', 2: '🥈', 1: '🥉' };

export function RDuaPertiga({ view, names, me, canAct, acted, act, replay, draft }: RenderProps) {
  const v = view;
  const [guess, setGuessRaw] = useResetState<number>(Math.round(v.batas / 3), v.ronde);
  const setGuess = (x: number) => {
    setGuessRaw(x);
    draft?.(x);
  };
  // angka yang terlihat di pemilih dikirim otomatis kalau waktu habis
  useEffect(() => {
    if (canAct) draft?.(guess);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAct, v.ronde]);
  const terlarang: number[] = v.terlarang ?? [];
  const acuan = v.acuan === 'median' ? 'median' : 'rata-rata';
  const bertingkat = v.poin_mode === 'bertingkat';
  const last = v.riwayat?.[v.riwayat.length - 1];
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">
            {v.faktor != null
              ? <>Target = <b>{fmt(v.faktor, 3)}</b> × {acuan} semua tebakan</>
              : <>Target = faktor <b>rahasia {fmt(v.faktor_min, 2)}–{fmt(v.faktor_max, 2)}</b> × {acuan} (dibuka setelah ronde)</>}
          </span></div>
        <ul className="rule-notes">
          {v.kembar_gugur && <li>⚠️ Angka yang ditebak lebih dari satu orang gugur (tidak bisa menang).</li>}
          {bertingkat && <li>🏅 Tiga tebakan terdekat dapat poin 3 · 2 · 1.</li>}
          {v.tebakan_rahasia && <li>🙈 Tebakan lawan dirahasiakan: setelah ronde hanya {acuan}, target, dan pemenang yang dibuka.</li>}
          {terlarang.length > 0 && (
            <li>🚫 Angka terlarang ronde ini: {terlarang.map((x, k) => <span key={x}>{k > 0 ? ' ' : ''}<b className="chip out">{x}</b></span>)} (tebakan di sini gugur)</li>
          )}
        </ul>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Pilih angka 0–{v.batas}.</TurnNote>
        {canAct && (
          <div className="act-box">
            <NumberPicker value={guess} onChange={setGuess} min={0} max={v.batas} />
            <button type="button" className="btn primary big" onClick={() => act(guess)}>Kirim {guess}</button>
            {terlarang.includes(guess) && <span className="bad">⚠️ {guess} angka terlarang: tebakan ini pasti gugur.</span>}
          </div>
        )}
        {last && <NumberLine batas={v.batas} entry={last} names={names} />}
        <History rows={(v.riwayat ?? []).slice().reverse()} render={(r: any) => (
          <>
            <b>R{r.ronde}</b> {r.acuan === 'median' ? <>median {fmt(r.median, 2)}</> : <>rata {fmt(r.rata, 2)}</>}
            {r.faktor != null && <> × {fmt(r.faktor, 3)}</>} → target <b className="gold">{fmt(r.target, 2)}</b>
            {!r.pemenang.length && <span className="bad"> tidak ada pemenang</span>}
            {r.terlarang?.length > 0 && <span className="hint"> · terlarang {r.terlarang.join(', ')}</span>}
            <span className="hist-chips">
              {Object.entries(r.tebakan).map(([n, x]) => {
                const pt = r.poin?.[n];
                const out = r.gugur?.includes(n);
                return (
                  <span key={n} className={`chip ${r.pemenang.includes(n) ? 'win' : ''} ${out ? 'out' : ''}`}
                    title={out ? (r.terlarang?.includes(x) ? 'angka terlarang: gugur' : 'kembar: gugur') : undefined}
                    style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>
                    {n} <b>{x == null ? '?' : String(x)}</b>{out ? ' ✕' : ''}{bertingkat && pt ? ` ${MEDALI[pt] ?? ''}+${pt}` : ''}
                  </span>
                );
              })}
            </span>
          </>
        )} />
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor, 0)} me={me} />
    </div>
  );
}

function NumberLine({ batas, entry, names }: { batas: number; entry: any; names: string[] }) {
  const pos = (x: number) => `${(Math.min(Math.max(x, 0), batas) / batas) * 100}%`;
  const shown = Object.entries(entry.tebakan).filter(([, x]) => x != null);
  return (
    <div className="numline" aria-label={`Ronde ${entry.ronde}: target ${entry.target}`}>
      <div className="nl-axis" />
      {(entry.terlarang ?? []).map((x: number) => <div key={`t${x}`} className="nl-ban" style={{ left: pos(x) }} title={`terlarang: ${x}`} />)}
      <div className="nl-target" style={{ left: pos(entry.target) }}><span>target {fmt(entry.target, 1)}{entry.faktor != null ? ` (×${fmt(entry.faktor, 2)})` : ''}</span></div>
      {shown.map(([n, x], k) => (
        <div key={n} className={`nl-dot ${entry.gugur?.includes(n) ? 'out' : ''}`} title={`${n}: ${x}${entry.gugur?.includes(n) ? ' (gugur)' : ''}`}
          style={{ left: pos(Number(x)), top: 30 + (k % 3) * 14, background: seatColor(idxOf(names, n)) }} />
      ))}
      {shown.length < Object.keys(entry.tebakan).length && <div className="nl-hidden">tebakan lawan dirahasiakan</div>}
      <div className="nl-tick" style={{ left: 0 }}>0</div>
      <div className="nl-tick" style={{ left: '100%' }}>{batas}</div>
    </div>
  );
}

export function History({ rows, render, max = 30 }: { rows: any[]; render: (r: any) => ReactNode; max?: number }) {
  if (!rows.length) return null;
  return (
    <div>
      <h3 className="sub-h">Riwayat</h3>
      <ol className="hist">
        {rows.slice(0, max).map((r, i) => <li key={i}>{render(r)}</li>)}
      </ol>
    </div>
  );
}

/* ------------------------------------------------------------------ Pasar Malam Sepi */
type Tempat = { id: string; nama: string; kapasitas: number | null; hadiah: number; jumlah?: number | null; ramai?: boolean; datang?: string[] };

function tempatOf(h: any): Tempat[] {
  return h.tempat ?? [{ id: 'pasar', nama: '🎡 Pasar Malam', kapasitas: h.kapasitas, hadiah: 1, jumlah: h.jumlah, ramai: h.ramai, datang: h.datang }];
}

export function RFarol({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const hist: any[] = v.riwayat ?? [];
  const tempat: Tempat[] = v.tempat ?? tempatOf(v);
  const multi = tempat.length > 1;
  const maxN = Math.max(names.length, 1);
  const hukuman = v.hukuman ?? 1;
  const pct = (x: number) => `${(Math.min(x, maxN) / maxN) * 100}%`;
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Malam {v.malam}/{v.malam_total}</b><span className="spacer" />
          {!multi && (
            <span className="hint">
              {tempat[0].kapasitas != null ? <>Nyaman kalau yang datang ≤ <b>{tempat[0].kapasitas}</b> orang</> : <>Kapasitas malam ini <b>rahasia</b> (dibuka setelah malam)</>}
            </span>
          )}</div>
        {v.spesial && <div className={`spesial-banner ${v.spesial.jenis}`}>{v.spesial.teks}</div>}
        {multi && (
          <ul className="venue-list">
            {tempat.map((t) => (
              <li key={t.id}><b>{t.nama}</b> nyaman kalau ≤ <b>{t.kapasitas ?? '?'}</b> orang → <span className="good">+{t.hadiah}</span></li>
            ))}
          </ul>
        )}
        <ul className="rule-notes">
          <li>Nyaman {multi ? 'dapat hadiah tempatnya' : <>dapat <b className="good">+{tempat[0].hadiah}</b></>}, sumpek <b className="bad">−{hukuman}</b>, di rumah selalu 0.</li>
          {v.kapasitas_mode === 'berubah' && <li>🔀 Kapasitas berubah tiap malam (70%–130% dari biasanya).</li>}
          {v.kapasitas_mode === 'rahasia' && <li>🔀 Kapasitas berubah tiap malam dan baru dibuka setelah malam selesai.</li>}
          {v.jumlah_rahasia && <li>🙈 Jumlah pengunjung dirahasiakan: setelah malam hanya diumumkan nyaman atau sumpek.</li>}
        </ul>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me} />
        {canAct && (
          <div className="act-box">
            {tempat.map((t) => (
              <button key={t.id} type="button" className="btn big good" onClick={() => act(t.id)}>
                {multi ? <>{t.nama} <small>+{t.hadiah}</small></> : '🎡 Datang'}
              </button>
            ))}
            <button type="button" className="btn big" onClick={() => act('rumah')}>🏠 Di rumah</button>
          </div>
        )}
        {hist.length > 0 && (
          <div className="bars farol-bars" role="img" aria-label="Jumlah pengunjung tiap malam">
            {hist.map((h: any) => (
              <div key={h.malam} className="bar-group" title={`Malam ${h.malam}${h.spesial ? ` (${h.spesial})` : ''}`}>
                {tempatOf(h).map((t) => (
                  <div key={t.id} className={`bar-col venue-${t.id}`}
                    title={`Malam ${h.malam} · ${t.nama}: ${t.jumlah ?? '?'} datang, kapasitas ${t.kapasitas ?? '?'} (${t.ramai ? 'sumpek' : 'nyaman'})`}>
                    <div className={`bar ${t.ramai ? 'bad' : 'ok'} ${t.jumlah == null ? 'unknown' : ''}`}
                      style={{ height: t.jumlah == null ? '100%' : pct(t.jumlah) }} />
                    {t.kapasitas != null && <i className="cap-tick" style={{ bottom: pct(t.kapasitas) }} />}
                  </div>
                ))}
                {h.spesial && <span className="bar-badge">{h.spesial === 'festival' ? '🎉' : '🌧️'}</span>}
              </div>
            ))}
          </div>
        )}
        {hist.length > 0 && <p className="hint">Garis kuning = kapasitas malam itu{v.jumlah_rahasia ? ' · batang bergaris = jumlah dirahasiakan (hijau nyaman, merah sumpek)' : ''}.</p>}
        <History rows={hist.slice().reverse()} render={(r: any) => (
          <>
            <b>Malam {r.malam}</b>{r.spesial ? ` ${r.spesial === 'festival' ? '🎉' : '🌧️'}` : ''}{' '}
            {tempatOf(r).map((t) => (
              <span key={t.id} className="venue-res">
                {multi && <>{t.nama} </>}{t.jumlah ?? '?'}/{t.kapasitas ?? '?'} datang ·{' '}
                {t.ramai ? <span className="bad">sumpek (−{hukuman})</span> : <span className="good">nyaman (+{t.hadiah})</span>}
                <span className="hist-chips">
                  {(t.datang ?? []).map((n: string) => <NameChip key={n} name={n} idx={idxOf(names, n)} />)}
                  {t.jumlah == null && <span className="hint">{(t.datang ?? []).length ? 'yang lain dirahasiakan' : 'siapa yang datang dirahasiakan'}</span>}
                </span>
              </span>
            ))}
          </>
        )} />
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor, 0)} me={me} />
    </div>
  );
}

/* ------------------------------------------------------------------ Dilema Kas Desa */
function KasSanksi({ v, names, myName, act, draft }: { v: any; names: string[]; myName: string; act: (a: unknown) => void; draft?: (a: unknown) => void }) {
  const last = v.riwayat?.[v.riwayat.length - 1];
  const [denda, setDendaRaw] = useResetState<Record<string, number>>({}, `${v.ronde}-${v.fase}`);
  const [usir, setUsirRaw] = useResetState<string | null>(null, `${v.ronde}-${v.fase}`);
  const others = names.filter((n) => n !== myName);
  const spent = Object.values(denda).reduce((a, b) => a + b, 0);
  const budget = v.pendapatan - spent;
  const sanksi = (d: Record<string, number>, u: string | null) => ({ denda: d, usir: u });
  const setDenda = (d: Record<string, number>) => {
    setDendaRaw(d);
    draft?.(sanksi(d, usir));
  };
  const setUsir = (u: string | null) => {
    setUsirRaw(u);
    draft?.(sanksi(denda, u));
  };
  return (
    <div className="act-box sanksi-box">
      <b>⚖️ Fase sanksi</b>
      <span className="hint">
        {v.denda > 0 ? `Tiap koin yang kamu bayar menghapus ${v.denda} koin tabungan orang itu (maksimal bayar ${v.pendapatan}). ` : ''}
        {v.usir_aktif ? 'Pilih satu orang untuk diusir: yang dipilih lebih dari separuh pemain lain tidak dapat bagian kas ronde depan.' : ''}
      </span>
      <ul className="sanksi-list">
        {others.map((n) => (
          <li key={n}>
            <NameChip name={n} idx={idxOf(names, n)} />
            <span className="hint">sumbang {last?.sumbangan?.[n] ?? '?'}</span>
            <span className="spacer" />
            {v.denda > 0 && (
              <span className="row-inline">
                <button type="button" className="btn small" disabled={!denda[n]} onClick={() => setDenda({ ...denda, [n]: Math.max(0, (denda[n] ?? 0) - 1) })}>−</button>
                <b>{denda[n] ?? 0}</b>
                <button type="button" className="btn small" disabled={budget <= 0} onClick={() => setDenda({ ...denda, [n]: (denda[n] ?? 0) + 1 })}>+</button>
              </span>
            )}
            {v.usir_aktif && (
              <button type="button" className={`btn small ${usir === n ? 'danger' : ''}`} onClick={() => setUsir(usir === n ? null : n)}>
                {usir === n ? '👢 diusir' : 'usir?'}
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className="row">
        <button type="button" className="btn primary" onClick={() => act(sanksi(denda, usir))}>Kirim sanksi</button>
        <button type="button" className="btn" onClick={() => act(sanksi({}, null))}>Tanpa sanksi</button>
      </div>
    </div>
  );
}

export function RKasDesa({ view, names, me, canAct, acted, act, replay, draft }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const [give, setGiveRaw] = useResetState<number>(0, `${v.ronde}-${v.fase}`);
  const setGive = (x: number) => {
    setGiveRaw(x);
    draft?.(x);
  };
  // angka yang terlihat di pemilih dikirim otomatis kalau waktu habis
  useEffect(() => {
    if (canAct && v.fase !== 'sanksi') draft?.(give);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAct, v.ronde, v.fase]);
  const total = names.length;
  const receivers = Math.max(1, total - (v.dikucilkan?.length ?? 0));
  const preview = v.pengali != null ? (give * v.pengali) / receivers : null;
  const target: number = v.target ?? 0;
  const last = v.riwayat?.[v.riwayat.length - 1];
  const rondeLabel = v.akhir_pasti ? `Ronde ${v.ronde}/${v.ronde_total}` : `Ronde ${v.ronde} dari sekitar ${v.ronde_total}`;
  const berhasil = (v.riwayat ?? []).filter((r: any) => r.tercapai).length;
  const sayaDiusir = myName != null && (v.dikucilkan ?? []).includes(myName);
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>{rondeLabel}{v.fase === 'sanksi' ? ' · sanksi' : ''}</b><span className="spacer" />
          <span className="hint">Kas × {v.pengali != null ? fmt(v.pengali, 2) : v.pengali_kisaran ? `? (rahasia, antara ${fmt(v.pengali_kisaran[0], 2)}–${fmt(v.pengali_kisaran[1], 2)})` : '? (rahasia)'} lalu dibagi rata ke {receivers} orang</span></div>
        {target > 0 && (
          <div className="kas-target">
            <span>🎯 Target kas: <b>{target}</b> koin → kalau tercapai, <b>semua</b> dapat bonus <b className="gold">+{v.bonus}</b></span>
            {v.riwayat?.length > 0 && <span className="hint">tercapai {berhasil} dari {v.riwayat.length} ronde</span>}
            {v.bencana > 0 && <span className="hint">🌊 gagal 2× berturut-turut = banjir (−{v.bencana}% tabungan)</span>}
          </div>
        )}
        {(v.dikucilkan?.length ?? 0) > 0 && v.fase !== 'sanksi' && (
          <p className="bad">👢 Diusir ronde ini: {v.dikucilkan.join(', ')} (tidak menyumbang, tidak dapat bagian & bonus)</p>
        )}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {v.fase === 'sanksi' ? 'Pilih sanksi untuk pemain lain (boleh tanpa sanksi).' : `Kamu dapat ${v.pendapatan} koin. Berapa yang disumbang?`}
        </TurnNote>
        {sayaDiusir && v.fase !== 'sanksi' && !replay && <p className="hint">Kamu sedang diusir: tunggu ronde berikutnya.</p>}
        {canAct && v.fase === 'sanksi' && myName && <KasSanksi v={v} names={names} myName={myName} act={act} draft={draft} />}
        {canAct && v.fase !== 'sanksi' && (
          <div className="act-box">
            <NumberPicker value={give} onChange={setGive} min={0} max={v.pendapatan} />
            <span className="hint">
              {preview != null ? `Sumbanganmu kembali ${fmt(preview, 2)} koin ke kamu (dan sama ke setiap orang).` : 'Pengali rahasia: kembalinya baru ketahuan setelah ronde.'}
              {target > 0 && ` Kalau sumbanganmu yang membuat kas mencapai ${target}, kamu (dan semua) dapat +${v.bonus}.`}
            </span>
            <button type="button" className="btn primary big" onClick={() => act(give)}>Sumbang {give}</button>
          </div>
        )}
        {last && target > 0 && (
          <div className="kas-bar" aria-label={`Kas ronde ${last.ronde}: ${last.total} dari target ${last.target}`}>
            <i className={last.tercapai ? 'ok' : 'bad'} style={{ width: `${Math.min(100, (last.total / Math.max(v.pendapatan * total, 1)) * 100)}%` }} />
            <span className="kb-target" style={{ left: `${(last.target / Math.max(v.pendapatan * total, 1)) * 100}%` }} />
            <small>Ronde {last.ronde}: kas {last.total}/{last.target} {last.tercapai ? '✅ bonus untuk semua' : '❌ bonus hilang'}</small>
          </div>
        )}
        <History rows={(v.riwayat ?? []).slice().reverse()} render={(r: any) => (
          <>
            <b>R{r.ronde}</b> kas {r.total}{r.target ? `/${r.target}` : ''} × {fmt(r.pengali, 2)} → tiap orang +{fmt(r.bagian, 2)}
            {r.target > 0 && (r.tercapai ? <span className="good">✅ +{r.bonus} bonus</span> : <span className="bad">❌ target gagal</span>)}
            {r.bencana && <span className="bad">🌊 banjir!</span>}
            <span className="hist-chips">
              {Object.entries(r.sumbangan).map(([n, x]) => (
                <span key={n} className="chip" style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>{n} <b>{x == null ? '?' : String(x)}</b></span>
              ))}
            </span>
            {r.sanksi && (Object.keys(r.sanksi.denda).length > 0 || r.sanksi.diusir.length > 0) && (
              <span className="hint">
                ⚖️ {Object.entries(r.sanksi.denda).map(([a, t]: [string, any]) => `${a} denda ${Object.entries(t).map(([x, k]) => `${x} ${k}`).join(', ')}`).join(' · ')}
                {r.sanksi.diusir.length ? ` · 👢 diusir: ${r.sanksi.diusir.join(', ')}` : ''}
              </span>
            )}
          </>
        )} />
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor)} me={me} title="Koin" />
    </div>
  );
}

/* ------------------------------------------------------------------ Rebutan Lahan */
const KHUSUS_ICON: Record<string, string> = { ganda: '⭐×2', misteri: '🌫️' };

export function RBlotto({ view, names, me, canAct, acted, act, replay, draft }: RenderProps) {
  const v = view;
  const n = v.medan as number;
  const myName = me != null ? names[me] : null;
  const pool: number = v.pasukan_saya ?? v.pasukan;
  const even = useMemo(() => {
    const base = Array(n).fill(Math.floor(pool / n));
    base[0] += pool - base.reduce((a: number, b: number) => a + b, 0);
    return base as number[];
  }, [n, pool]);
  const zero = useMemo(() => Array(n).fill(0) as number[], [n]);
  // mulai dari 0 di semua medan supaya tombol + langsung bisa dipakai
  const [alloc, setAllocRaw] = useResetState<number[]>(zero, v.ronde);
  const setAlloc = (a: number[]) => {
    setAllocRaw(a);
    // alokasi yang terlihat dikirim otomatis kalau waktu habis (masih kosong semua = dibagi rata)
    if (a.some((x) => x > 0)) draft?.(a);
  };
  const used = alloc.reduce((a, b) => a + b, 0);
  const left = pool - used;
  const last = v.riwayat?.[v.riwayat.length - 1];
  const set = (k: number, x: number) => setAlloc(alloc.map((a, j) => (j === k ? Math.max(0, Math.min(x, a + left)) : a)));
  const showVal = (x: number | null) => (x == null ? '?' : x);
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">{pool} pasukan{v.menyusut && pool !== v.pasukan ? ` (awal ${v.pasukan})` : ''}, {n} medan</span></div>
        {(v.benteng > 0 || v.menyusut || v.alokasi_rahasia) && (
          <p className="hint">
            {v.benteng > 0 ? `🏰 Benteng: penguasa tunggal ronde lalu dihitung +${v.benteng}% di medannya. ` : ''}
            {v.menyusut ? '⚔️ Pasukan di medan yang kalah hilang; ada bala bantuan tiap ronde. ' : ''}
            {v.alokasi_rahasia ? '🌫️ Alokasi lawan rahasia.' : ''}
          </p>
        )}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Bagi pasukanmu.</TurnNote>
        <div className="fields-row">
          {(v.nilai ?? []).map((val: number | null, k: number) => {
            const kh = v.khusus?.[k];
            const fort = v.benteng > 0 && v.pemilik?.[k];
            return (
              <div key={k} className={`field-card ${kh ? `kh-${kh}` : ''}`}>
                <div className="fc-val">⭐ {showVal(val)} {kh && <small>{KHUSUS_ICON[kh]}</small>}</div>
                <div className="fc-next hint">besok {v.nilai_berikut ? `${showVal(v.nilai_berikut[k])}${v.khusus_berikut?.[k] ? ` ${KHUSUS_ICON[v.khusus_berikut[k]]}` : ''}` : '?'}</div>
                {fort && <div className="hint">🏰 {v.pemilik[k]}{v.pemilik[k] === myName ? ' (kamu)' : ''}</div>}
                {canAct && (
                  <div className="fc-input">
                    <button type="button" className="btn small" onClick={() => set(k, alloc[k] - 5)}>−5</button>
                    <input type="number" className="input" min={0} value={alloc[k]} onChange={(e) => set(k, Number(e.target.value) || 0)} aria-label={`Pasukan medan ${k + 1}`} />
                    <button type="button" className="btn small" onClick={() => set(k, alloc[k] + 5)}>+5</button>
                  </div>
                )}
                {last && (
                  <div className="fc-last">
                    <small className="hint">R{last.ronde} (⭐{last.nilai[k]}):</small>
                    {last.penguasa[k].length ? last.penguasa[k].map((nm: string) => <NameChip key={nm} name={nm} idx={idxOf(names, nm)} />) : <span className="hint">kosong</span>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {canAct && (
          <div className="row">
            <span className={left < 0 ? 'bad' : 'hint'}>Sisa pasukan: <b>{left}</b></span>
            <span className="spacer" />
            <button type="button" className="btn small" onClick={() => setAlloc(even)}>Bagi rata</button>
            <button type="button" className="btn small" onClick={() => setAlloc(zero)}>Nol semua</button>
            <button type="button" className="btn primary" disabled={left < 0} onClick={() => act(alloc)}>Kirim alokasi</button>
          </div>
        )}
        {canAct && (
          <p className="hint">Kalau waktu habis, alokasi yang terlihat dikirim otomatis (sisa pasukan tidak dipakai). Masih kosong semua = dibagi rata.</p>
        )}
        {last && (
          <div className="table-wrap">
            <table className="tbl">
              <caption className="hint">Alokasi ronde {last.ronde}</caption>
              <thead><tr><th>Pemain</th>{last.nilai.map((x: number, k: number) => <th key={k}>⭐{x}{last.khusus?.[k] ? ` ${KHUSUS_ICON[last.khusus[k]]}` : ''}</th>)}<th>Poin</th>{v.menyusut && <th>Hilang</th>}</tr></thead>
              <tbody>
                {Object.entries(last.alokasi).map(([nm, al]: [string, any]) => (
                  <tr key={nm} className={nm === myName ? 'me' : ''}>
                    <td><NameChip name={nm} idx={idxOf(names, nm)} /></td>
                    {al == null
                      ? last.nilai.map((_: number, k: number) => <td key={k} className={last.penguasa[k].includes(nm) ? 'win-cell' : ''}>?</td>)
                      : al.map((x: number, k: number) => <td key={k} className={last.penguasa[k].includes(nm) ? 'win-cell' : ''}>{x}</td>)}
                    <td>{fmt(last.poin[nm], 2)}</td>
                    {v.menyusut && <td>{last.hilang?.[nm] == null ? '?' : `−${last.hilang[nm]}`}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor).map((r) => ({ ...r, sub: v.pasukan_semua ? `${v.pasukan_semua[r.name]} pasukan` : undefined }))} me={me} />
    </div>
  );
}

/* ------------------------------------------------------------------ Lelang Rahasia */
const KAT_ICON: Record<string, string> = { Pusaka: '🗡️', Seni: '🎭', Kriya: '🧵', Harta: '💰' };
const JENIS_TEKS: Record<string, string> = {
  pertama: 'pemenang bayar tawarannya', kedua: 'pemenang bayar tawaran tertinggi KEDUA', semua_bayar: 'SEMUA penawar bayar tawarannya',
};

function LotValue({ nilai, mode, now }: { nilai: number | null; mode: string; now?: boolean }) {
  if (nilai == null) return <span className="lot-v hidden-v">?</span>;
  const minus = nilai < 0;
  return (
    <span className={`lot-v ${minus ? 'bad' : ''}`}>
      {minus ? '💀' : ''}{mode === 'taksiran' && now ? '≈' : ''}{nilai}
    </span>
  );
}

export function RLelang({ view, names, me, canAct, acted, act, replay, draft }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const myCoins: number = myName ? v.koin[myName] ?? 0 : 0;
  const [bid, setBidRaw] = useResetState<number>(0, v.ronde);
  const setBid = (x: number) => {
    setBidRaw(x);
    draft?.(x);
  };
  // pilihan yang terlihat di layar ikut terkirim otomatis kalau waktu habis
  useEffect(() => {
    if (canAct) draft?.(bid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canAct, v.ronde]);
  const cur = v.barang;
  const curMinus = cur?.nilai != null && cur.nilai < 0;
  const rows = names
    .map((n, i) => ({ n, i, sc: v.skor?.[n] }))
    .sort((a, b) => (b.sc ?? -1e9) - (a.sc ?? -1e9) || (v.poin[b.n] ?? 0) - (v.poin[a.n] ?? 0))
    .map((r) => ({
      name: r.n, idx: r.i, value: r.sc == null ? `${v.poin[r.n]} poin` : fmt(r.sc, 1),
      sub: `${v.poin[r.n]} poin · ${v.koin[r.n] == null ? '? koin' : `${v.koin[r.n]} koin`}${v.bonus_set ? ` · set ${Object.entries(v.koleksi?.[r.n] ?? {}).map(([k, x]) => `${KAT_ICON[k] ?? k}${x}`).join(' ') || '–'}` : ''}`,
    }));
  const valueText = () => {
    if (!cur) return null;
    if (cur.nilai == null) return <span className="hint big-num">nilai rahasia</span>;
    if (curMinus) return <span className="bad big-num">💀 barang kutukan ({cur.nilai})</span>;
    return <span className="gold big-num">{v.nilai_mode === 'taksiran' ? `≈ ${cur.nilai} poin (taksiranmu)` : `${cur.nilai} poin`}</span>;
  };
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="lot-strip" aria-label="Jadwal barang">
          {v.jadwal.map((nilai: number | null, k: number) => {
            const h = v.riwayat[k];
            const nama = v.nama_barang[k];
            return (
              <div key={k} className={`lot ${k + 1 === v.ronde && !h ? 'now' : ''} ${h ? 'done' : ''} ${nama == null ? 'secret' : ''}`}>
                <LotValue nilai={h ? h.nilai : nilai} mode={v.nilai_mode} now={!h} />
                <span className="lot-n">{nama == null ? '❔ rahasia' : `${KAT_ICON[v.kategori?.[k]] ?? ''} ${nama}`}</span>
                {h && (
                  <span className="lot-w">
                    {h.minus ? `kena: ${h.kena_minus.join(', ') || '–'}` : h.pemenang ? `${h.pemenang}${h.harga != null ? ` · ${h.harga}` : ''}` : h.hangus ? 'seri, hangus' : 'tidak laku'}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {cur && (
          <div className={`lot-now ${curMinus ? 'minus' : ''}`}>
            <span className="hint">Ronde {v.ronde}/{v.ronde_total} sedang dilelang{cur.kategori ? ` · ${KAT_ICON[cur.kategori] ?? ''} ${cur.kategori}` : ''}</span>
            <b>{cur.nama}</b>
            {valueText()}
          </div>
        )}
        <p className="hint lelang-rules">
          Jenis: {JENIS_TEKS[v.jenis] ?? v.jenis}
          {v.hangus_persen > 0 && v.jenis !== 'semua_bayar' ? ` · seri tertinggi: barang hangus & ${v.hangus_persen}% tawaran yang seri ikut hangus` : ''}
          {v.koin_ronde > 0 ? ` · +${v.koin_ronde} koin tiap ronde` : ''}
          {v.ada_minus ? ' · ada barang 💀 minus: poin minusnya kena penawar tertinggi, terendah' + (names.length % 2 === 1 && names.length > 3 ? ', dan tengah' : '') + ' (tidak ada yang bayar)' : ''}
          {v.bonus_set ? ` · tiap 3 barang sekategori = +${v.bonus_set} poin` : ''}
          {v.lihat_depan < v.ronde_total ? ` · jadwal terlihat ${v.lihat_depan} barang ke depan` : ''}
        </p>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {curMinus ? 'Barang minus: jangan jadi yang tertinggi, terendah, atau di tengah!' : 'Tawar diam-diam.'} Koinmu {myCoins}.
        </TurnNote>
        {canAct && (
          <div className="act-box">
            <NumberPicker value={bid} onChange={setBid} min={0} max={myCoins} />
            <div className="row">
              {[0, 1, Math.floor(myCoins / 4), Math.floor(myCoins / 2), myCoins].map((x, k) => (
                <button key={k} type="button" className="btn small" onClick={() => setBid(x)}>{x}</button>
              ))}
            </div>
            <button type="button" className="btn primary big" onClick={() => act(bid)}>Tawar {bid}</button>
          </div>
        )}
        <History rows={v.riwayat.slice().reverse()} render={(r: any) => (
          <>
            <b>{r.nama}</b> ({r.minus ? '💀' : ''}{r.nilai}) →{' '}
            {r.minus
              ? <span className="bad">kutukan kena {r.kena_minus.join(', ') || '–'}</span>
              : r.pemenang
                ? <><NameChip name={r.pemenang} idx={idxOf(names, r.pemenang)} />{r.harga != null ? ` bayar ${r.harga}` : ''}</>
                : <span className="bad">{r.hangus ? 'seri, hangus' : 'tidak ada tawaran'}</span>}
            {r.hangus_koin && Object.keys(r.hangus_koin).length > 0 && (
              <span className="bad"> · koin hangus {Object.entries(r.hangus_koin).map(([n, x]) => `${n} −${x}`).join(', ')}</span>
            )}
            {r.tawaran ? (
              <span className="hist-chips">
                {Object.entries(r.tawaran).map(([n, x]) => <span key={n} className="chip" style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>{n} <b>{String(x)}</b></span>)}
              </span>
            ) : r.tawaran_saya != null ? <span className="hint"> · tawaranmu {r.tawaran_saya}</span> : null}
          </>
        )} />
      </div>
      <ScoreBoard rows={rows} me={me} title={`Skor (koin × ${v.nilai_sisa}${v.bonus_set ? ' + set' : ''})`} />
    </div>
  );
}

/* ------------------------------------------------------------------ Suit Live */
export function RSuit({ view, names, me, canAct, acted, act, replay, events }: RenderProps) {
  const v = view;
  const last = v.terakhir;
  const maxHp = Math.max(v.hp_awal, ...Object.values(v.hp as Record<string, number>));
  const myName = me != null ? names[me] : null;
  const ev = events?.find((e) => e.jenis === 'ronde') ?? null;
  const show = ev ?? last;
  const kej = v.kejutan;
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {Math.min(v.ronde, v.ronde_maks)}{v.ronde_pasti === false ? ` dari sekitar ${v.ronde_maks}` : `/${v.ronde_maks}`}</b><span className="spacer" />
          <span className="hint">Kalah = −{v.hp_kalah} HP, dibagi ke pemenangnya</span></div>
        {kej && !replay && <div className="kejutan-banner">🎲 {kej.teks}</div>}
        {v.pemimpin && <p className="hint">👑 Buruan: {v.pemimpin} (kalah = −{Math.floor((v.hp_kalah * v.buruan) / 100)} HP ekstra untuk yang mengalahkannya)</p>}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me} />
        {canAct && (
          <div className="weapon-row">
            {SENJATA.map((w) => (
              <button key={w} type="button" className={`weapon-btn ${w} ${kej?.jenis === 'terlarang' && kej.senjata === w ? 'banned' : ''}`}
                onClick={() => act(w.toUpperCase())}>
                <span dangerouslySetInnerHTML={{ __html: ICON[w] }} />
                {LABEL[w]}{kej?.jenis === 'terlarang' && kej.senjata === w ? ' 🚫' : ''}
              </button>
            ))}
          </div>
        )}
        <div className="suit-seats">
          {names.map((n, i) => {
            const hp = v.hp[n] ?? 0;
            const ch = show?.pilihan?.[n] as Senjata | undefined;
            const d = show?.perubahan?.[n];
            return (
              <div key={n} className={`suit-seat ${hp <= 0 ? 'out' : ''} ${n === myName ? 'me' : ''}`} style={{ ['--c' as string]: seatColor(i) }}>
                <div className="ss-name">{v.pemimpin === n ? '👑 ' : ''}{n}</div>
                <div className="ss-weapon">{ch ? <span dangerouslySetInnerHTML={{ __html: ICON[ch] }} /> : <span className="hint">–</span>}</div>
                <div className="hpbar-s"><i style={{ width: `${(hp / maxHp) * 100}%` }} /></div>
                <div className="ss-hp">{v.hp_samar && n !== myName ? '≈' : ''}{fmt(hp)} {d != null && d !== 0 && <b className={d > 0 ? 'good' : 'bad'}>{d > 0 ? '+' : ''}{d}</b>}</div>
              </div>
            );
          })}
        </div>
        {show && (
          <p className="hint">
            Ronde {show.ronde}: {SENJATA.map((w) => `${LABEL[w]} ${show.jumlah?.[w] ?? 0}`).join(' · ')}
            {show.gugur?.length ? ` · gugur: ${show.gugur.join(', ')}` : ''}
            {show.kejutan ? ` · 🎲 ${show.kejutan.teks}` : ''}
            {show.buruan ? ` · 👑 ${show.buruan.pemimpin} −${show.buruan.ekstra} ekstra` : ''}
          </p>
        )}
      </div>
      <ScoreBoard rows={scoreRows(names, v.hp, 0).map((r) => ({ ...r, dim: (v.hp[r.name] ?? 0) <= 0, value: `${v.hp_samar && r.name !== myName ? '≈' : ''}${r.value}` }))} me={me} title="HP" />
    </div>
  );
}
