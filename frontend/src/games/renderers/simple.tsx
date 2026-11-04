import { useMemo, type ReactNode } from 'react';
import { ICON, LABEL, SENJATA } from '../../replay/assets';
import type { Senjata } from '../../types';
import { fmt, seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, scoreRows, useResetState, type RenderProps } from './common';

/* ------------------------------------------------------------------ Angka Dua Pertiga */
export function RDuaPertiga({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const [guess, setGuess] = useResetState<number>(Math.round(v.batas / 3), v.ronde);
  const last = v.riwayat?.[v.riwayat.length - 1];
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">Target = {fmt(v.faktor, 3)} × rata-rata semua tebakan</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Pilih angka 0–{v.batas}.</TurnNote>
        {canAct && (
          <div className="act-box">
            <NumberPicker value={guess} onChange={setGuess} min={0} max={v.batas} />
            <button type="button" className="btn primary big" onClick={() => act(guess)}>Kirim {guess}</button>
          </div>
        )}
        {last && <NumberLine batas={v.batas} entry={last} names={names} />}
        <History rows={(v.riwayat ?? []).slice().reverse()} render={(r: any) => (
          <>
            <b>R{r.ronde}</b> rata {fmt(r.rata, 2)} → target <b className="gold">{fmt(r.target, 2)}</b>
            <span className="hist-chips">
              {Object.entries(r.tebakan).map(([n, x]) => (
                <span key={n} className={`chip ${r.pemenang.includes(n) ? 'win' : ''}`} style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>{n} <b>{String(x)}</b></span>
              ))}
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
  return (
    <div className="numline" aria-label={`Ronde ${entry.ronde}: target ${entry.target}`}>
      <div className="nl-axis" />
      <div className="nl-target" style={{ left: pos(entry.target) }}><span>target {fmt(entry.target, 1)}</span></div>
      {Object.entries(entry.tebakan).map(([n, x], k) => (
        <div key={n} className="nl-dot" title={`${n}: ${x}`} style={{ left: pos(Number(x)), top: 30 + (k % 3) * 14, background: seatColor(idxOf(names, n)) }} />
      ))}
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
export function RFarol({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const hist = v.riwayat ?? [];
  const maxN = Math.max(names.length, 1);
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Malam {v.malam}/{v.malam_total}</b><span className="spacer" />
          <span className="hint">Nyaman kalau yang datang ≤ {v.kapasitas} orang</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me} />
        {canAct && (
          <div className="act-box">
            <button type="button" className="btn big good" onClick={() => act('datang')}>🎡 Datang</button>
            <button type="button" className="btn big" onClick={() => act('rumah')}>🏠 Di rumah</button>
          </div>
        )}
        <div className="bars" role="img" aria-label="Jumlah pengunjung tiap malam">
          {hist.map((h: any) => (
            <div key={h.malam} className={`bar ${h.ramai ? 'bad' : 'ok'}`} style={{ height: `${(h.jumlah / maxN) * 100}%` }} title={`Malam ${h.malam}: ${h.jumlah} datang`} />
          ))}
          <div className="cap-line" style={{ bottom: `${(v.kapasitas / maxN) * 100}%` }}><span>kapasitas {v.kapasitas}</span></div>
        </div>
        <History rows={hist.slice().reverse()} render={(r: any) => (
          <>
            <b>Malam {r.malam}</b> {r.jumlah} datang · {r.ramai ? <span className="bad">sumpek (−1)</span> : <span className="good">nyaman (+1)</span>}
            <span className="hist-chips">{r.datang.map((n: string) => <NameChip key={n} name={n} idx={idxOf(names, n)} />)}</span>
          </>
        )} />
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor, 0)} me={me} />
    </div>
  );
}

/* ------------------------------------------------------------------ Dilema Kas Desa */
export function RKasDesa({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const [give, setGive] = useResetState<number>(Math.round(v.pendapatan / 2), v.ronde);
  const total = names.length;
  const preview = (give * v.pengali) / Math.max(total, 1);
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">Kas × {fmt(v.pengali, 2)} lalu dibagi rata ke {total} orang</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Kamu dapat {v.pendapatan} koin. Berapa yang disumbang?</TurnNote>
        {canAct && (
          <div className="act-box">
            <NumberPicker value={give} onChange={setGive} min={0} max={v.pendapatan} />
            <span className="hint">Sumbanganmu sendiri kembali {fmt(preview, 2)} koin ke kamu (dan sama ke setiap orang).</span>
            <button type="button" className="btn primary big" onClick={() => act(give)}>Sumbang {give}</button>
          </div>
        )}
        <History rows={(v.riwayat ?? []).slice().reverse()} render={(r: any) => (
          <>
            <b>R{r.ronde}</b> kas {r.total} → tiap orang +{fmt(r.bagian, 2)}
            {v.terbuka && (
              <span className="hist-chips">
                {Object.entries(r.sumbangan).map(([n, x]) => (
                  <span key={n} className="chip" style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>{n} <b>{String(x)}</b></span>
                ))}
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
export function RBlotto({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const n = v.medan as number;
  const even = useMemo(() => {
    const base = Array(n).fill(Math.floor(v.pasukan / n));
    base[0] += v.pasukan - base.reduce((a: number, b: number) => a + b, 0);
    return base as number[];
  }, [n, v.pasukan]);
  const [alloc, setAlloc] = useResetState<number[]>(even, v.ronde);
  const used = alloc.reduce((a, b) => a + b, 0);
  const left = v.pasukan - used;
  const last = v.riwayat?.[v.riwayat.length - 1];
  const set = (k: number, x: number) => setAlloc(alloc.map((a, j) => (j === k ? Math.max(0, Math.min(x, a + left)) : a)));
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {v.ronde}/{v.ronde_total}</b><span className="spacer" />
          <span className="hint">{v.pasukan} pasukan, {n} medan</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Bagi pasukanmu.</TurnNote>
        <div className="fields-row">
          {(v.nilai ?? []).map((val: number, k: number) => (
            <div key={k} className="field-card">
              <div className="fc-val">⭐ {val}</div>
              <div className="fc-next hint">besok {v.nilai_berikut ? v.nilai_berikut[k] : '–'}</div>
              {canAct && (
                <div className="fc-input">
                  <button type="button" className="btn small" onClick={() => set(k, alloc[k] - 5)}>−5</button>
                  <input type="number" className="input" min={0} value={alloc[k]} onChange={(e) => set(k, Number(e.target.value) || 0)} aria-label={`Pasukan medan ${k + 1}`} />
                  <button type="button" className="btn small" onClick={() => set(k, alloc[k] + 5)}>+5</button>
                </div>
              )}
              {last && (
                <div className="fc-last">
                  {last.penguasa[k].length ? last.penguasa[k].map((nm: string) => <NameChip key={nm} name={nm} idx={idxOf(names, nm)} />) : <span className="hint">kosong</span>}
                </div>
              )}
            </div>
          ))}
        </div>
        {canAct && (
          <div className="row">
            <span className={left < 0 ? 'bad' : 'hint'}>Sisa pasukan: <b>{left}</b></span>
            <span className="spacer" />
            <button type="button" className="btn small" onClick={() => setAlloc(even)}>Bagi rata</button>
            <button type="button" className="btn primary" disabled={left < 0} onClick={() => act(alloc)}>Kirim alokasi</button>
          </div>
        )}
        {last && (
          <div className="table-wrap">
            <table className="tbl">
              <caption className="hint">Alokasi ronde {last.ronde}</caption>
              <thead><tr><th>Pemain</th>{last.nilai.map((x: number, k: number) => <th key={k}>⭐{x}</th>)}<th>Poin</th></tr></thead>
              <tbody>
                {Object.entries(last.alokasi).map(([nm, al]: [string, any]) => (
                  <tr key={nm}>
                    <td><NameChip name={nm} idx={idxOf(names, nm)} /></td>
                    {al.map((x: number, k: number) => <td key={k} className={last.penguasa[k].includes(nm) ? 'win-cell' : ''}>{x}</td>)}
                    <td>{fmt(last.poin[nm], 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <ScoreBoard rows={scoreRows(names, v.skor)} me={me} />
    </div>
  );
}

/* ------------------------------------------------------------------ Lelang Rahasia */
export function RLelang({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const myCoins = me != null ? v.koin[names[me]] ?? 0 : 0;
  const [bid, setBid] = useResetState<number>(0, v.ronde);
  const cur = v.barang;
  const rows = names
    .map((n, i) => ({ n, i, sc: (v.poin[n] ?? 0) + (v.koin[n] ?? 0) * v.nilai_sisa }))
    .sort((a, b) => b.sc - a.sc)
    .map((r) => ({ name: r.n, idx: r.i, value: fmt(r.sc, 1), sub: `${v.poin[r.n]} poin · ${v.koin[r.n]} koin` }));
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="lot-strip" aria-label="Jadwal barang">
          {v.jadwal.map((nilai: number, k: number) => {
            const h = v.riwayat[k];
            return (
              <div key={k} className={`lot ${k + 1 === v.ronde && !h ? 'now' : ''} ${h ? 'done' : ''}`}>
                <span className="lot-v">{nilai}</span>
                <span className="lot-n">{v.nama_barang[k]}</span>
                {h && <span className="lot-w">{h.pemenang ? `${h.pemenang} · ${h.harga}` : h.hangus ? 'hangus' : 'tidak laku'}</span>}
              </div>
            );
          })}
        </div>
        {cur && (
          <div className="lot-now">
            <span className="hint">Ronde {v.ronde}/{v.ronde_total} sedang dilelang</span>
            <b>{cur.nama}</b>
            <span className="gold big-num">{cur.nilai} poin</span>
          </div>
        )}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>Tawar diam-diam. Koinmu {myCoins}.</TurnNote>
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
            <b>{r.nama}</b> ({r.nilai}) → {r.pemenang ? <><NameChip name={r.pemenang} idx={idxOf(names, r.pemenang)} /> bayar {r.harga}</> : <span className="bad">{r.hangus ? 'seri, hangus' : 'tidak ada tawaran'}</span>}
            <span className="hist-chips">
              {Object.entries(r.tawaran).map(([n, x]) => <span key={n} className="chip" style={{ ['--c' as string]: seatColor(idxOf(names, n)) }}>{n} <b>{String(x)}</b></span>)}
            </span>
          </>
        )} />
      </div>
      <ScoreBoard rows={rows} me={me} title={`Skor (koin × ${v.nilai_sisa})`} />
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
  return (
    <div className="game-grid">
      <div className="panel">
        <div className="row"><b>Ronde {Math.min(v.ronde, v.ronde_maks)}/{v.ronde_maks}</b><span className="spacer" />
          <span className="hint">Kalah = −{v.hp_kalah} HP, dibagi ke pemenangnya</span></div>
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me} />
        {canAct && (
          <div className="weapon-row">
            {SENJATA.map((w) => (
              <button key={w} type="button" className={`weapon-btn ${w}`} onClick={() => act(w.toUpperCase())}>
                <span dangerouslySetInnerHTML={{ __html: ICON[w] }} />
                {LABEL[w]}
              </button>
            ))}
          </div>
        )}
        <div className="suit-seats">
          {names.map((n, i) => {
            const hp = v.hp[n] ?? 0;
            const ch = show?.pilihan?.[n] as Senjata | undefined;
            const d = show?.perubahan?.[n] ?? 0;
            return (
              <div key={n} className={`suit-seat ${hp <= 0 ? 'out' : ''} ${n === myName ? 'me' : ''}`} style={{ ['--c' as string]: seatColor(i) }}>
                <div className="ss-name">{n}</div>
                <div className="ss-weapon">{ch ? <span dangerouslySetInnerHTML={{ __html: ICON[ch] }} /> : <span className="hint">–</span>}</div>
                <div className="hpbar-s"><i style={{ width: `${(hp / maxHp) * 100}%` }} /></div>
                <div className="ss-hp">{fmt(hp)} {d !== 0 && <b className={d > 0 ? 'good' : 'bad'}>{d > 0 ? '+' : ''}{d}</b>}</div>
              </div>
            );
          })}
        </div>
        {show && (
          <p className="hint">
            Ronde {show.ronde}: {SENJATA.map((w) => `${LABEL[w]} ${show.jumlah?.[w] ?? 0}`).join(' · ')}
            {show.gugur?.length ? ` · gugur: ${show.gugur.join(', ')}` : ''}
          </p>
        )}
      </div>
      <ScoreBoard rows={scoreRows(names, v.hp, 0).map((r) => ({ ...r, dim: (v.hp[r.name] ?? 0) <= 0 }))} me={me} title="HP" />
    </div>
  );
}
