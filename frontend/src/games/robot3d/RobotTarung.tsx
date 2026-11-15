/**
 * Robot Tarung: garasi (rakit robot, pratinjau 3D, simpan rakitan) dan arena (tampilan 3D, HUD, kendali keyboard/joystick).
 * Dimuat terpisah (lazy) supaya Three.js hanya diunduh saat game ini dibuka.
 */
import { useEffect, useRef, useState, type PointerEvent as RPointerEvent, type ReactNode } from 'react';
import { seatColor } from '../hubApi';
import { ScoreBoard, TurnNote, touchScreen, type RenderProps } from '../renderers/common';
import { Arena3D, Preview3D, webglOk, type Desain } from './scene';

const SISI = ['depan', 'kanan', 'belakang', 'kiri'] as const;
type Sisi = (typeof SISI)[number];
const KUNCI_SIMPAN = 'arena-rt-rakitan';
const KUNCI_TERAKHIR = 'arena-rt-terakhir';
const IKON: Record<string, string> = { tidak: '🛡️', spinner_h: '🌀', spinner_v: '🥁', flipper: '🦘', palu: '🔨', gergaji: '🪚' };
const SAKLAR = new Set(['spinner_h', 'spinner_v', 'gergaji']);        // senjata yang dinyalakan/dimatikan (bukan ditahan)
const KO_TEKS: Record<string, string> = { hancur: 'hancur', lubang: 'jatuh ke lubang', mogok: 'tidak bergerak 10 detik' };
const SISI_LABEL: Record<Sisi, string> = { depan: 'Depan', kanan: 'Kanan', belakang: 'Belakang', kiri: 'Kiri' };
type Kamera = 'arena' | 'dekat' | 'ikuti';
const KAMERA: Kamera[] = ['arena', 'dekat', 'ikuti'];
const KUNCI_KAMERA = 'arena-rt-kamera';
const LABEL_KAMERA: Record<Kamera, string> = { arena: 'Arena', dekat: 'Dekat', ikuti: 'Ikuti' };

/* ------------------------------------------------------------------ rakitan */
function beratDesain(K: any, d: Desain): number {
  if (!K) return 0;
  const a = d.armor;
  return K.sasis[d.sasis].berat + K.penggerak[d.penggerak].berat + K.baterai[d.baterai].berat + K.senjata[d.senjata].berat
    + (d.pembalik ? K.tambahan.pembalik.berat : 0) + SISI.reduce((t, s) => t + a[s], 0) * K.armor.berat_per_tingkat;
}

/** Sama dengan pas_berat di server: kurangi armor, baterai & roda, lalu pembalik, terakhir senjata. */
function pasBerat(K: any, src: Desain, maks: number): Desain {
  const d: Desain = { ...src, armor: { ...src.armor } };
  const turun: Record<string, string[]> = { baterai: ['besar', 'sedang', 'kecil'], penggerak: ['kuat', 'sedang', 'ringan'] };
  for (let n = 0; n < 80; n++) {
    if (beratDesain(K, d) <= maks) return d;
    const sd = SISI.reduce((m, s) => (d.armor[s] > d.armor[m] ? s : m), SISI[0]);
    if (d.armor[sd] > 1) {
      d.armor[sd] -= 1;
      continue;
    }
    let turunkan = false;
    for (const key of ['baterai', 'penggerak'] as const) {
      const urut = turun[key];
      const k = urut.indexOf(d[key]);
      if (k < urut.length - 1) {
        (d as any)[key] = urut[k + 1];
        turunkan = true;
        break;
      }
    }
    if (turunkan) continue;
    if (d.armor[sd] > 0) d.armor[sd] -= 1;
    else if (d.pembalik) d.pembalik = false;
    else if (d.senjata !== 'tidak') d.senjata = 'tidak';
    else if (d.sasis !== 'kotak') d.sasis = 'kotak';
    else break;
  }
  return d;
}

function sah(K: any, d: any): d is Desain {
  return !!(K && d && K.sasis[d.sasis] && K.penggerak[d.penggerak] && K.baterai[d.baterai] && K.senjata[d.senjata] && d.armor
    && SISI.every((s) => Number.isInteger(d.armor[s]) && d.armor[s] >= 0 && d.armor[s] <= K.armor.maks));
}

function bacaSimpanan(K: any): Desain[] {
  try {
    const x = JSON.parse(localStorage.getItem(KUNCI_SIMPAN) || '[]');
    return Array.isArray(x) ? x.filter((d) => sah(K, d)).slice(0, 12) : [];
  } catch {
    return [];
  }
}

function tulis(kunci: string, nilai: unknown) {
  try {
    localStorage.setItem(kunci, typeof nilai === 'string' ? nilai : JSON.stringify(nilai));
  } catch {
    /* penyimpanan browser penuh/terkunci: abaikan */
  }
}

function bacaTerakhir(K: any): Desain | null {
  try {
    const d = JSON.parse(localStorage.getItem(KUNCI_TERAKHIR) || 'null');
    return sah(K, d) ? d : null;
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ entri */
export default function RobotTarung(p: RenderProps) {
  const v = p.view;
  if (!v) return null;
  if (v.fase === 'garasi') return <Garasi {...p} />;
  return <Tarung {...p} />;
}

/* ------------------------------------------------------------------ garasi */
function Pilihan({ judul, kat, nilai, ubah, kunci, K, dis }: {
  judul: string; kat: string; nilai: string; ubah: (k: string) => void; kunci: boolean; K: any; dis?: (k: string) => boolean;
}) {
  const opsi = K[kat] as Record<string, any>;
  return (
    <div className="rt-sec">
      <div className="rt-sec-h">{judul}</div>
      <div className="rt-opts">
        {Object.entries(opsi).map(([k, o]) => (
          <button key={k} type="button" className={`rt-opt ${nilai === k ? 'on' : ''}`} disabled={kunci || dis?.(k)} onClick={() => ubah(k)}
            aria-pressed={nilai === k}>
            <span className="nm">{kat === 'senjata' ? `${IKON[k] ?? ''} ` : ''}{o.nama}</span>
            <small>{o.berat} kg{kat === 'baterai' ? ` · ${o.energi} energi` : ''}{kat === 'penggerak' ? ` · ${o.vmaks} m/s` : ''}</small>
          </button>
        ))}
      </div>
      {opsi[nilai]?.ket && <p className="hint">{opsi[nilai].ket}</p>}
    </div>
  );
}

/** Denah armor dari atas: makin tebal garis, makin tebal armornya. */
function DenahArmor({ a, maks }: { a: Record<Sisi, number>; maks: number }) {
  const w = (n: number) => (n ? 2 + (n / maks) * 9 : 0);
  const c = (n: number) => (n ? `rgba(215, 222, 235, ${0.45 + (n / maks) * 0.55})` : 'transparent');
  return (
    <svg viewBox="0 0 120 90" className="rt-denah" aria-hidden="true">
      <rect x="30" y="22" width="60" height="46" rx="6" fill="var(--stage-2)" stroke="var(--line)" />
      <path d="M84 45 l-10 -7 v14 z" fill="var(--muted)" />
      <line x1="96" y1="20" x2="96" y2="70" stroke={c(a.depan)} strokeWidth={w(a.depan)} strokeLinecap="round" />
      <line x1="24" y1="20" x2="24" y2="70" stroke={c(a.belakang)} strokeWidth={w(a.belakang)} strokeLinecap="round" />
      <line x1="30" y1="76" x2="90" y2="76" stroke={c(a.kanan)} strokeWidth={w(a.kanan)} strokeLinecap="round" />
      <line x1="30" y1="14" x2="90" y2="14" stroke={c(a.kiri)} strokeWidth={w(a.kiri)} strokeLinecap="round" />
      <text x="60" y="49" textAnchor="middle" fontSize="9" fill="var(--muted)">maju →</text>
    </svg>
  );
}

function Garasi({ view: v, meta, names, me, canAct, act, replay }: RenderProps) {
  const K = meta.katalog;
  const contoh = (meta.contoh_rakitan ?? []) as Desain[];
  const maks: number = v.berat_maks;
  const myName = me != null ? names[me] : null;
  const sudahSiap = !!(myName && v.siap?.[myName]);
  const [gl, setGl] = useState(webglOk);
  const [d, setD] = useState<Desain>(() => {
    const awal = bacaTerakhir(K) ?? contoh[0];
    return awal ? pasBerat(K, awal, maks) : (null as unknown as Desain);
  });
  const [simpanan, setSimpanan] = useState<Desain[]>(() => bacaSimpanan(K));
  const [kirim, setKirim] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const pv = useRef<Preview3D | null>(null);
  const tampil: Desain = (sudahSiap && v.desain_saya) || d;
  const tampilKey = JSON.stringify(tampil);

  useEffect(() => {
    if (!gl || !box.current) return;
    let p: Preview3D;
    try {
      p = new Preview3D(box.current, touchScreen);
    } catch {
      setGl(false);
      return;
    }
    pv.current = p;
    const ro = new ResizeObserver(() => p.resize());
    ro.observe(box.current);
    return () => {
      ro.disconnect();
      p.dispose();
      pv.current = null;
    };
  }, [gl]);
  useEffect(() => {
    if (tampil) pv.current?.set(tampil, seatColor(me ?? 0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tampilKey, me, gl]);
  useEffect(() => {
    if (sudahSiap) setKirim(false);
  }, [sudahSiap]);

  if (!K || !d) return <div className="panel">Katalog komponen belum dimuat.</div>;
  const pemain = me != null && !replay;
  const kunci = !pemain || sudahSiap || !canAct;
  const b = beratDesain(K, tampil);
  const lebih = b > maks;
  const ubah = (patch: Partial<Desain>) => setD((x) => ({ ...x, ...patch }));
  const armor = (s: Sisi, delta: number) => setD((x) => ({ ...x, armor: { ...x.armor, [s]: Math.max(0, Math.min(K.armor.maks, x.armor[s] + delta)) } }));
  const pg = K.penggerak[tampil.penggerak];
  const siapList = names.map((n, i) => ({ n, i, ok: !!v.siap?.[n] }));
  const kirimRakitan = () => {
    const out = { ...d, nama: (d.nama || 'Robot').trim().slice(0, 16) || 'Robot' };
    tulis(KUNCI_TERAKHIR, out);
    setKirim(true);
    act({ rakit: out });
    window.setTimeout(() => setKirim(false), 3000);
  };
  const simpan = () => {
    const nama = (d.nama || 'Robot').trim().slice(0, 16) || 'Robot';
    const baru = [{ ...d, nama }, ...simpanan.filter((x) => x.nama !== nama)].slice(0, 12);
    setSimpanan(baru);
    tulis(KUNCI_SIMPAN, baru);
  };
  const hapus = (nama: string) => {
    const baru = simpanan.filter((x) => x.nama !== nama);
    setSimpanan(baru);
    tulis(KUNCI_SIMPAN, baru);
  };
  const muat = (x: Desain) => setD(pasBerat(K, { ...x, armor: { ...x.armor } }, maks));

  return (
    <div className="game-grid rt">
      <div className="panel rt-garasi">
        <div className="row">
          <b>🔧 Garasi</b>
          <span className="tag-mini">ronde {v.ronde}/{v.ronde_total}</span>
          <span className="tag-mini">arena {v.arena} m</span>
          <span className="spacer" />
          <span className={`ul-clock ${v.sisa <= 15 ? 'low' : ''}`}>⏱ {Math.floor(v.sisa / 60)}:{String(Math.floor(v.sisa % 60)).padStart(2, '0')}</span>
        </div>
        <TurnNote canAct={canAct && !sudahSiap} acted={false} replay={replay} me={me}>
          Rakit robotmu lalu tekan <b>Siap tarung</b>. Kalau waktu habis, robot bawaan yang dipakai.
        </TurnNote>
        {sudahSiap && <div className="turn-note done">✅ Robotmu sudah masuk daftar. Menunggu pemain lain…</div>}
        <div className="rt-garasi-grid">
          <div className="rt-kiri">
            <div ref={box} className="rt-prev">
              {!gl && <div className="rt-nogl">Browser ini tidak mendukung 3D (WebGL). Game tetap bisa dimainkan dengan tampilan 2D.</div>}
              <div className="rt-prev-nama">{IKON[tampil.senjata]} {tampil.nama}</div>
            </div>
            <div className={`rt-berat ${lebih ? 'lebih' : ''}`} aria-label={`Berat ${b} dari ${maks} kg`}>
              <i style={{ width: `${Math.min(100, (b / maks) * 100)}%` }} />
              <span>{b} / {maks} kg{lebih ? ` · kelebihan ${b - maks} kg` : ` · sisa ${maks - b} kg`}</span>
            </div>
            <div className="rt-stat">
              <span>🏃 {pg.vmaks} m/s</span><span>💪 dorong {pg.daya}</span><span>🔄 putar {pg.putar}</span>
              <span>🔋 {K.baterai[tampil.baterai].energi}</span><span>🧱 rangka {K.sasis[tampil.sasis].rangka}</span>
              <span>🛡️ {SISI.reduce((t, s) => t + tampil.armor[s], 0) * K.armor.hp_per_tingkat} HP armor</span>
            </div>
            {pemain && !sudahSiap && (
              <div className="row wrap">
                {lebih && <button type="button" className="btn small" onClick={() => setD(pasBerat(K, d, maks))}>⚖️ Sesuaikan berat</button>}
                <button type="button" className="btn primary" disabled={kunci || lebih || kirim} onClick={kirimRakitan}>
                  {kirim ? 'Mengirim…' : '✅ Siap tarung'}
                </button>
                <button type="button" className="btn small" onClick={simpan}>💾 Simpan</button>
              </div>
            )}
            {pemain && !sudahSiap && (
              <div className="rt-sec">
                <div className="rt-sec-h">Contoh & rakitan tersimpan</div>
                <div className="rt-chips">
                  {contoh.map((x) => (
                    <button key={`c-${x.nama}`} type="button" className="chip-btn" onClick={() => muat(x)} title="Muat (disesuaikan ke batas berat)">
                      {IKON[x.senjata]} {x.nama}
                    </button>
                  ))}
                  {simpanan.map((x) => (
                    <span key={`s-${x.nama}`} className="chip-btn saved">
                      <button type="button" onClick={() => muat(x)} title="Muat rakitan tersimpan">💾 {x.nama}</button>
                      <button type="button" className="x" onClick={() => hapus(x.nama)} aria-label={`Hapus ${x.nama}`}>✕</button>
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="rt-sec">
              <div className="rt-sec-h">Siap tarung</div>
              <div className="rt-chips">
                {siapList.map((x) => (
                  <span key={x.n} className="chip" style={{ ['--c' as string]: seatColor(x.i) }}>{x.ok ? '✅' : '⏳'} {x.n}</span>
                ))}
              </div>
            </div>
          </div>
          {pemain && !sudahSiap ? (
            <div className="rt-kanan">
              <label className="field">
                <span>Nama robot</span>
                <input className="input" maxLength={16} value={d.nama} onChange={(e) => ubah({ nama: e.target.value })} />
              </label>
              <Pilihan judul="Sasis" kat="sasis" nilai={d.sasis} K={K} kunci={kunci} ubah={(k) => ubah({ sasis: k as Desain['sasis'] })} />
              <Pilihan judul="Senjata" kat="senjata" nilai={d.senjata} K={K} kunci={kunci} ubah={(k) => ubah({ senjata: k as Desain['senjata'] })} />
              <Pilihan judul="Roda & motor" kat="penggerak" nilai={d.penggerak} K={K} kunci={kunci} ubah={(k) => ubah({ penggerak: k })} />
              <Pilihan judul="Baterai" kat="baterai" nilai={d.baterai} K={K} kunci={kunci} ubah={(k) => ubah({ baterai: k })} />
              <div className="rt-sec">
                <div className="rt-sec-h">Armor ({K.armor.berat_per_tingkat} kg & {K.armor.hp_per_tingkat} HP per tingkat)</div>
                <div className="rt-armor">
                  <DenahArmor a={d.armor} maks={K.armor.maks} />
                  <div className="rt-armor-rows">
                    {SISI.map((s) => (
                      <div key={s} className="rt-armor-row">
                        <span>{SISI_LABEL[s]}</span>
                        <button type="button" className="btn small" disabled={kunci || d.armor[s] <= 0} onClick={() => armor(s, -1)} aria-label={`Kurangi armor ${s}`}>−</button>
                        <b>{d.armor[s]}</b>
                        <button type="button" className="btn small" disabled={kunci || d.armor[s] >= K.armor.maks} onClick={() => armor(s, 1)} aria-label={`Tambah armor ${s}`}>+</button>
                      </div>
                    ))}
                  </div>
                </div>
                <p className="hint">Depan melindungi senjata, kiri/kanan melindungi motor, belakang melindungi baterai.</p>
              </div>
              <label className="rt-toggle">
                <input type="checkbox" checked={d.pembalik} disabled={kunci} onChange={(e) => ubah({ pembalik: e.target.checked })} />
                <span>{K.tambahan.pembalik.nama} ({K.tambahan.pembalik.berat} kg) — {K.tambahan.pembalik.ket}{d.senjata === 'flipper' ? ' Flipper sudah bisa membalikkan badan sendiri.' : ''}</span>
              </label>
              <div className="rt-siap-bawah">
                <span className={lebih ? 'bad' : ''}>{b} / {maks} kg</span>
                {lebih && <button type="button" className="btn small" onClick={() => setD(pasBerat(K, d, maks))}>⚖️ Sesuaikan</button>}
                <button type="button" className="btn primary" disabled={kunci || lebih || kirim} onClick={kirimRakitan}>
                  {kirim ? 'Mengirim…' : '✅ Siap tarung'}
                </button>
              </div>
            </div>
          ) : (
            <div className="rt-kanan">
              {v.desain ? (
                <div className="rt-sec">
                  <div className="rt-sec-h">Rakitan pemain</div>
                  {names.map((n, i) => v.desain[n] && (
                    <p key={n} className="hint"><span className="chip" style={{ ['--c' as string]: seatColor(i) }}>{n}</span> {IKON[v.desain[n].senjata]} {v.desain[n].nama} · {beratDesain(K, v.desain[n])} kg</p>
                  ))}
                </div>
              ) : (
                <p className="hint">{sudahSiap ? 'Rakitan lawan baru terlihat di arena.' : 'Para pemain sedang merakit robot.'}</p>
              )}
            </div>
          )}
        </div>
      </div>
      <Papan view={v} names={names} me={me} />
    </div>
  );
}

/* ------------------------------------------------------------------ papan skor & riwayat */
function Papan({ view: v, names, me }: { view: any; names: string[]; me: number | null }) {
  const rows = names.map((n, i) => ({ name: n, idx: i, value: v.skor?.[n] ?? 0, sub: v.robot?.[n]?.desain?.nama }))
    .sort((a, b) => Number(b.value) - Number(a.value));
  return (
    <div className="rt-side">
      <ScoreBoard me={me} rows={rows} title="Poin" />
      {(v.riwayat ?? []).length > 0 && (
        <div className="panel">
          <h3>Riwayat ronde</h3>
          <ol className="hist small">
            {v.riwayat.map((r: any) => <li key={r.ronde}>{ringkasRonde(r)}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}

export function ringkasRonde(e: any): string {
  const ko = Object.entries(e.ko ?? {}).map(([n, s]) => `${n} ${KO_TEKS[String(s)] ?? s}`).join(', ');
  if (e.cara === 'juri') {
    const nilai = Object.entries(e.juri ?? {}).sort((a: any, b: any) => b[1] - a[1]).map(([n, x]) => `${n} ${x}`).join(' vs ');
    return `Ronde ${e.ronde}: ${e.pemenang} menang angka juri (${nilai})${ko ? ` · KO: ${ko}` : ''}`;
  }
  if (e.cara === 'seri_ko') return `Ronde ${e.ronde}: semua KO, ${e.pemenang} menang karena kerusakan terbanyak`;
  return `Ronde ${e.ronde}: ${e.pemenang} menang KO dalam ${e.detik} dtk${ko ? ` (${ko})` : ''}`;
}

/* ------------------------------------------------------------------ HUD */
function Bar({ nilai, maks, kelas, label }: { nilai: number; maks: number; kelas: string; label?: string }) {
  const f = maks > 0 ? Math.max(0, Math.min(1, nilai / maks)) : 0;
  return (
    <div className={`rt-bar ${kelas}`} title={label}>
      <i style={{ width: `${f * 100}%` }} />
    </div>
  );
}

function ArmorMini({ r }: { r: any }) {
  const op = (s: Sisi) => (r.armor_maks?.[s] ? 0.15 + 0.85 * Math.max(0, r.armor[s] / r.armor_maks[s]) : 0.06);
  return (
    <svg viewBox="0 0 24 24" className="rt-armor-mini" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" fill="none" stroke="currentColor" strokeOpacity="0.35" />
      <rect x="20" y="5" width="3" height="14" rx="1" fill="currentColor" fillOpacity={op('depan')} />
      <rect x="1" y="5" width="3" height="14" rx="1" fill="currentColor" fillOpacity={op('belakang')} />
      <rect x="5" y="20" width="14" height="3" rx="1" fill="currentColor" fillOpacity={op('kanan')} />
      <rect x="5" y="1" width="14" height="3" rx="1" fill="currentColor" fillOpacity={op('kiri')} />
    </svg>
  );
}

function KartuRobot({ nama, idx, r, saya }: { nama: string; idx: number; r: any; saya: boolean }) {
  const w = r.desain?.senjata;
  let senjata: ReactNode;
  if (w === 'spinner_h' || w === 'spinner_v') senjata = <Bar nilai={r.rpm} maks={1} kelas="rpm" label="Putaran senjata" />;
  else if (w === 'flipper' || w === 'palu') senjata = <span className={`rt-siap ${r.siap ? 'ok' : ''}`}>{r.siap ? 'siap' : `${r.cd.toFixed(1)}s`}</span>;
  else if (w === 'gergaji') senjata = <span className={`rt-siap ${r.aktif ? 'ok' : ''}`}>{r.aktif ? 'nyala' : 'mati'}</span>;
  else senjata = null;
  return (
    <div className={`rt-card ${saya ? 'me' : ''} ${r.ko ? 'ko' : ''}`} style={{ ['--c' as string]: seatColor(idx) }}>
      <div className="rt-card-h">
        <span className="dot" />
        <b>{nama}</b>
        <small>{IKON[w]} {r.desain?.nama}</small>
      </div>
      <Bar nilai={r.rangka} maks={r.rangka_maks} kelas="hp" label={`Rangka ${Math.round(r.rangka)}/${r.rangka_maks}`} />
      <Bar nilai={r.energi} maks={r.energi_maks} kelas="en" label={`Energi ${Math.round(r.energi)}/${r.energi_maks}`} />
      <div className="rt-card-f">
        <ArmorMini r={r} />
        <span className={`rt-motor ${r.motor[0] <= 0 ? 'mati' : ''}`} title="Motor kiri">⚙</span>
        <span className={`rt-motor ${r.motor[1] <= 0 ? 'mati' : ''}`} title="Motor kanan">⚙</span>
        {r.senjata_hp <= 0 ? <span className="rt-siap">senjata rusak</span> : senjata}
        {r.terbalik && !r.ko && <span className="rt-flag">terbalik</span>}
        {r.ko && <span className="rt-flag ko">KO</span>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ gambar 2D (cadangan tanpa WebGL) */
function gambar2D(cv: HTMLCanvasElement, v: any, names: string[]) {
  const box = cv.parentElement;
  if (!box || !v?.robot) return;
  const W = box.clientWidth, H = box.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  cv.width = W * dpr;
  cv.height = H * dpr;
  const g = cv.getContext('2d');
  if (!g) return;
  const N: number = v.arena;
  const s = Math.min(W, H) / N;
  const ox = (W - N * s) / 2, oy = (H - N * s) / 2;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.fillStyle = '#12131c';
  g.fillRect(0, 0, W, H);
  g.fillStyle = '#2b2e3a';
  g.fillRect(ox, oy, N * s, N * s);
  g.strokeStyle = v.dinding_duri ? '#c9ccd6' : 'rgba(255,200,60,0.5)';
  g.lineWidth = 3;
  g.strokeRect(ox, oy, N * s, N * s);
  for (const h of v.jebakan ?? []) {
    g.beginPath();
    g.arc(ox + h.x * s, oy + h.y * s, h.r * s, 0, Math.PI * 2);
    g.fillStyle = h.jenis === 'lubang' ? ((v.lubang_dalam ?? 0) > 0 ? '#55596a' : '#050507') : h.jenis === 'gergaji' ? '#d7dbe4' : 'rgba(255,59,59,0.3)';
    g.fill();
  }
  names.forEach((n, i) => {
    const r = v.robot[n];
    if (!r || r.ko === 'lubang') return;
    g.save();
    g.translate(ox + r.x * s, oy + r.y * s);
    g.rotate((r.a * Math.PI) / 180);
    g.globalAlpha = r.ko ? 0.35 : 1;
    g.fillStyle = seatColor(i);
    const R = r.r * s;
    g.fillRect(-R, -R * 0.8, 2 * R, 1.6 * R);
    g.fillStyle = r.terbalik ? '#ff6a6a' : '#fff';
    g.fillRect(R * 0.6, -R * 0.6, R * 0.4, R * 1.2);
    g.restore();
    g.fillStyle = '#fff';
    g.font = '600 12px sans-serif';
    g.textAlign = 'center';
    g.fillText(n, ox + r.x * s, oy + r.y * s - r.r * s - 6);
  });
}

/* ------------------------------------------------------------------ arena */
type Kendali = { maju: number; belok: number; senjata: boolean; balik: boolean };
const NOL: Kendali = { maju: 0, belok: 0, senjata: false, balik: false };
const TOMBOL = new Set(['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' ', 'e', 'f', 'j', 'k']);

function Tarung({ view: v, names, me, canAct, act, replay, events }: RenderProps) {
  const stage = useRef<HTMLDivElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const cv2d = useRef<HTMLCanvasElement>(null);
  const arena = useRef<Arena3D | null>(null);
  const [gl, setGl] = useState(webglOk);
  const namesRef = useRef(names);
  namesRef.current = names;
  const myName = me != null ? names[me] : null;
  const mine = myName ? v.robot?.[myName] : null;
  const pemain = me != null && !replay;
  const wpn: string = mine?.desain?.senjata ?? 'tidak';
  const bisaBalik = !!mine && (mine.desain?.pembalik || wpn === 'flipper');
  const [kamera, setKamera] = useState<Kamera>(() => {
    try {
      const k = localStorage.getItem(KUNCI_KAMERA) as Kamera | null;
      if (k && KAMERA.includes(k)) return k;
    } catch {
      /* abaikan */
    }
    return touchScreen ? 'dekat' : 'arena';
  });
  const [kilat, setKilat] = useState<{ teks: string; kelas: string; id: number } | null>(null);
  const [penuh, setPenuh] = useState(false);

  // --- 3D
  useEffect(() => {
    if (!gl || !host.current) return;
    let a: Arena3D;
    try {
      a = new Arena3D(host.current, (n) => seatColor(Math.max(0, namesRef.current.indexOf(n))), { lowPower: touchScreen });
    } catch {
      setGl(false);           // WebGL ada tapi gagal dibuat (driver/GPU): pakai gambar 2D
      return;
    }
    arena.current = a;
    a.update(v);
    const ro = new ResizeObserver(() => a.resize());
    ro.observe(host.current);
    return () => {
      ro.disconnect();
      a.dispose();
      arena.current = null;
    };
  }, [gl]);
  useEffect(() => {
    if (gl) arena.current?.update(v);
    else if (cv2d.current) gambar2D(cv2d.current, v, names);
  }, [v, gl, names]);
  const modeKamera: Kamera = kamera === 'ikuti' && !pemain ? 'dekat' : kamera;
  useEffect(() => {
    const a = arena.current;
    if (!a) return;
    a.mode = modeKamera;
    a.follow = myName;
  }, [modeKamera, myName, gl]);
  const gantiKamera = () => {
    const urut = KAMERA.filter((k) => k !== 'ikuti' || pemain);
    const next = urut[(urut.indexOf(modeKamera) + 1) % urut.length];
    setKamera(next);
    tulis(KUNCI_KAMERA, next);
  };
  // HP: geser layar supaya seluruh arena + joystick terlihat saat tarung dimulai
  useEffect(() => {
    if (!touchScreen || !pemain) return;
    const t = window.setTimeout(() => stage.current?.scrollIntoView({ block: 'start' }), 200);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [v.ronde]);

  // --- kejadian: percikan + teks besar (KO, mulai)
  useEffect(() => {
    if (!events?.length) return;
    arena.current?.events(events);
    for (const e of events) {
      if (e.jenis === 'ko') setKilat({ teks: `KO! ${e.pemain} ${KO_TEKS[e.sebab] ?? ''}`, kelas: 'ko', id: performance.now() });
      else if (e.jenis === 'mulai') setKilat({ teks: 'TARUNG!', kelas: 'go', id: performance.now() });
      else if (e.jenis === 'ronde_selesai') setKilat({ teks: `🏆 ${e.pemenang}`, kelas: 'win', id: performance.now() });
      else if (e.jenis === 'terbang' && e.balik && e.pemain === myName) setKilat({ teks: 'Terbalik!', kelas: 'warn', id: performance.now() });
    }
  }, [events, myName]);
  useEffect(() => {
    if (!kilat) return;
    const t = window.setTimeout(() => setKilat(null), kilat.kelas === 'win' ? 2600 : 1400);
    return () => window.clearTimeout(t);
  }, [kilat]);

  // --- kendali: keyboard + joystick + tombol layar, digabung lalu dikirim saat berubah
  const keys = useRef(new Set<string>());
  const joy = useRef({ x: 0, y: 0 });
  const tahan = useRef({ senjata: false, balik: false });
  const ctl = useRef<Kendali>({ ...NOL });
  const sent = useRef<Kendali & { t: number }>({ ...NOL, t: 0 });
  const timer = useRef<number>();
  const ubahSenjata = useRef(0);
  const boleh = useRef(false);
  boleh.current = pemain && canAct && !!mine?.hidup;
  const actRef = useRef(act);
  actRef.current = act;
  const wpnRef = useRef(wpn);
  wpnRef.current = wpn;

  const flush = () => {
    window.clearTimeout(timer.current);
    if (!boleh.current) return;
    const c = ctl.current, s = sent.current;
    const tombolBerubah = c.senjata !== s.senjata || c.balik !== s.balik;
    const analogBerubah = Math.abs(c.maju - s.maju) > 0.05 || Math.abs(c.belok - s.belok) > 0.05
      || (c.maju === 0 && s.maju !== 0) || (c.belok === 0 && s.belok !== 0);
    if (!tombolBerubah && !analogBerubah) return;
    const now = performance.now();
    if (!tombolBerubah && now - s.t < 50) {
      timer.current = window.setTimeout(flush, 50 - (now - s.t));
      return;
    }
    const out = { maju: Math.round(c.maju * 100) / 100, belok: Math.round(c.belok * 100) / 100, senjata: c.senjata, balik: c.balik };
    actRef.current(out);
    sent.current = { ...out, t: now };
  };
  const hitung = () => {
    const k = keys.current;
    const kb = {
      maju: (k.has('w') || k.has('arrowup') ? 1 : 0) - (k.has('s') || k.has('arrowdown') ? 1 : 0),
      belok: (k.has('d') || k.has('arrowright') ? 1 : 0) - (k.has('a') || k.has('arrowleft') ? 1 : 0),
    };
    const c = ctl.current;
    c.maju = Math.max(-1, Math.min(1, kb.maju + -joy.current.y));
    c.belok = Math.max(-1, Math.min(1, kb.belok + joy.current.x));
    if (!SAKLAR.has(wpnRef.current)) c.senjata = k.has(' ') || k.has('j') || tahan.current.senjata;
    c.balik = k.has('e') || k.has('f') || k.has('k') || tahan.current.balik;
    flush();
  };
  const saklarSenjata = () => {
    ctl.current.senjata = !ctl.current.senjata;
    ubahSenjata.current = performance.now();
    flush();
  };

  // ronde baru: robot dibuat ulang di server dengan kendali nol
  const faseLalu = useRef(v.fase);
  useEffect(() => {
    if (v.fase === 'hitung' && faseLalu.current !== 'hitung') {
      ctl.current = { ...NOL };
      sent.current = { ...NOL, t: 0 };
      hitung();
    }
    faseLalu.current = v.fase;
    // status senjata saklar mengikuti server (kecuali baru saja diubah di sini)
    if (mine && SAKLAR.has(wpn) && performance.now() - ubahSenjata.current > 600) {
      ctl.current.senjata = !!mine.aktif;
      sent.current.senjata = !!mine.aktif;
    }
  });

  useEffect(() => {
    if (!pemain) return;
    const bebas = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
    };
    const turun = (e: KeyboardEvent) => {
      if (bebas(e) || e.ctrlKey || e.metaKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (!TOMBOL.has(k)) return;
      e.preventDefault();
      if (e.repeat) return;
      if ((k === ' ' || k === 'j') && SAKLAR.has(wpnRef.current)) saklarSenjata();
      keys.current.add(k);
      hitung();
    };
    const naik = (e: KeyboardEvent) => {
      const k = e.key.toLowerCase();
      if (!keys.current.delete(k)) return;
      hitung();
    };
    const lepas = () => {
      keys.current.clear();
      joy.current = { x: 0, y: 0 };
      tahan.current = { senjata: false, balik: false };
      hitung();
    };
    // kirim ulang kendali yang sedang ditahan secara berkala: perintah yang jatuh saat jeda/sambung ulang tidak membuat
    // robot diam padahal tombol masih ditekan
    const detak = window.setInterval(() => {
      const c = ctl.current;
      if (!boleh.current || !(c.maju || c.belok || c.balik || (c.senjata && !SAKLAR.has(wpnRef.current)))) return;
      const out = { maju: Math.round(c.maju * 100) / 100, belok: Math.round(c.belok * 100) / 100, senjata: c.senjata, balik: c.balik };
      actRef.current(out);
      sent.current = { ...out, t: performance.now() };
    }, 400);
    window.addEventListener('keydown', turun);
    window.addEventListener('keyup', naik);
    window.addEventListener('blur', lepas);
    document.addEventListener('visibilitychange', lepas);
    return () => {
      window.removeEventListener('keydown', turun);
      window.removeEventListener('keyup', naik);
      window.removeEventListener('blur', lepas);
      document.removeEventListener('visibilitychange', lepas);
      window.clearTimeout(timer.current);
      window.clearInterval(detak);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pemain]);

  // --- joystick
  const knob = useRef<HTMLDivElement>(null);
  const joyId = useRef<number | null>(null);
  const gerakJoy = (e: RPointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget.getBoundingClientRect();
    const R = el.width / 2;
    let x = (e.clientX - (el.left + R)) / R;
    let y = (e.clientY - (el.top + R)) / R;
    const m = Math.hypot(x, y);
    if (m > 1) {
      x /= m;
      y /= m;
    }
    if (knob.current) knob.current.style.transform = `translate(${x * R * 0.6}px, ${y * R * 0.6}px)`;
    // zona mati kecil supaya mudah lurus; belok sedikit diredam supaya tidak terlalu liar
    joy.current = { x: Math.abs(x) < 0.15 ? 0 : x * 0.85, y: Math.abs(y) < 0.12 ? 0 : y };
    hitung();
  };
  const lepasJoy = () => {
    joyId.current = null;
    joy.current = { x: 0, y: 0 };
    if (knob.current) knob.current.style.transform = '';
    hitung();
  };
  const tombolLayar = (jenis: 'senjata' | 'balik', tekan: boolean) => {
    if (jenis === 'senjata' && SAKLAR.has(wpn)) {
      if (tekan) saklarSenjata();
      return;
    }
    tahan.current[jenis] = tekan;
    hitung();
  };

  // --- layar penuh: selalu lewat kelas CSS (iPhone tidak punya fullscreen elemen), plus fullscreen asli kalau didukung
  const fsAsli = useRef(false);
  useEffect(() => {
    const f = () => {
      if (!document.fullscreenElement && fsAsli.current) {
        fsAsli.current = false;
        setPenuh(false);
      }
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPenuh(false);
    };
    document.addEventListener('fullscreenchange', f);
    window.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('fullscreenchange', f);
      window.removeEventListener('keydown', esc);
    };
  }, []);
  useEffect(() => {
    document.body.classList.toggle('rt-kunci-gulir', penuh);
    return () => document.body.classList.remove('rt-kunci-gulir');
  }, [penuh]);
  const layarPenuh = () => {
    if (penuh) {
      setPenuh(false);
      if (document.fullscreenElement) document.exitFullscreen?.().catch(() => undefined);
      return;
    }
    setPenuh(true);
    const el = stage.current as any;
    const req = el?.requestFullscreen ?? el?.webkitRequestFullscreen;
    if (req) {
      try {
        const pr = req.call(el);
        fsAsli.current = true;
        pr?.catch?.(() => { fsAsli.current = false; });
      } catch {
        fsAsli.current = false;
      }
    }
  };

  const hitungMundur = v.fase === 'hitung' ? Math.max(1, Math.ceil(v.sisa)) : null;
  const sisa = Math.max(0, Math.ceil(v.sisa ?? 0));
  const adaLubang = (v.jebakan ?? []).some((h: any) => h.jenis === 'lubang');
  const robotList = names.map((n, i) => ({ n, i, r: v.robot?.[n] })).filter((x) => x.r);
  const sayaDulu = myName ? [...robotList.filter((x) => x.n === myName), ...robotList.filter((x) => x.n !== myName)] : robotList;
  const tampilKendali = pemain && touchScreen;
  const aktifSenjata = SAKLAR.has(wpn) ? !!mine?.aktif : false;
  const labelSenjata = ({ spinner_h: 'Putar', spinner_v: 'Putar', gergaji: 'Gergaji', flipper: 'Lempar', palu: 'Pukul' } as Record<string, string>)[wpn];

  let catatan: ReactNode = null;
  if (pemain && mine) {
    if (mine.ko) catatan = `💥 Robotmu KO (${KO_TEKS[mine.ko] ?? mine.ko}). Tonton sisa ronde.`;
    else if (mine.terbalik) catatan = bisaBalik ? '🙃 Terbalik! Tekan E (atau tombol Balik) untuk berdiri lagi.' : `🙃 Terbalik tanpa pembalik: masih bisa jalan pelan${wpn === 'spinner_v' ? ', drum tetap bekerja 70%' : ', senjata mati'}.`;
    else if (mine.diam >= 4) catatan = `⚠️ Robotmu diam ${Math.floor(mine.diam)} dtk — 10 dtk tidak bergerak = KO!`;
    else if (mine.energi <= 0) catatan = '🪫 Energi habis: hanya bisa merangkak pelan.';
  }

  return (
    <div className="game-grid rt">
      <div className="panel rt-main">
        <div className="row">
          <b>Ronde {v.ronde}/{v.ronde_total}</b>
          <span className="tag-mini">{v.arena} m</span>
          {adaLubang && v.fase === 'tarung' && (v.lubang_dalam ?? 0) > 0 && <span className="tag-mini">🕳️ lubang buka {Math.ceil(v.lubang_dalam)} dtk</span>}
          {adaLubang && v.fase === 'tarung' && (v.lubang_dalam ?? 0) <= 0 && <span className="tag-mini nobot">🕳️ lubang terbuka</span>}
          <span className="spacer" />
          {v.fase === 'tarung' && <span className={`ul-clock ${sisa <= 15 ? 'low' : ''}`}>⏱ {Math.floor(sisa / 60)}:{String(sisa % 60).padStart(2, '0')}</span>}
        </div>
        <TurnNote canAct={canAct && !!mine?.hidup} acted={false} replay={replay} me={me}>
          {touchScreen ? 'Joystick kiri untuk jalan, tombol kanan untuk senjata.' : 'WASD/panah untuk jalan, Spasi untuk senjata, E untuk berdiri lagi.'}
        </TurnNote>
        {catatan && <div className={`turn-note ${mine?.ko ? '' : 'warn'}`}>{catatan}</div>}
        <div ref={stage} className={`rt-stage ${penuh ? 'penuh' : ''} ${tampilKendali ? 'sentuh' : ''}`}>
          <div ref={host} className="rt-host">{!gl && <canvas ref={cv2d} className="rt-2d" />}</div>
          <div className="rt-hud">
            {sayaDulu.map((x) => <KartuRobot key={x.n} nama={x.n} idx={x.i} r={x.r} saya={x.n === myName} />)}
          </div>
          {hitungMundur != null && <div key={hitungMundur} className="rt-count">{hitungMundur}</div>}
          {kilat && <div key={kilat.id} className={`rt-flash ${kilat.kelas}`}>{kilat.teks}</div>}
          <div className="rt-tools">
            {v.fase === 'tarung' && (tampilKendali || penuh) && <span className={`rt-jam ${sisa <= 15 ? 'low' : ''}`}>⏱ {Math.floor(sisa / 60)}:{String(sisa % 60).padStart(2, '0')}</span>}
            {gl && (
              <button type="button" className="btn small" onClick={(e) => { gantiKamera(); e.currentTarget.blur(); }} title="Ganti kamera (arena / dekat / ikuti robotmu)"
                aria-label={`Kamera: ${LABEL_KAMERA[modeKamera]}. Ganti kamera`}>
                🎥{tampilKendali ? '' : ` ${LABEL_KAMERA[modeKamera]}`}
              </button>
            )}
            <button type="button" className="btn small" onClick={(e) => { layarPenuh(); e.currentTarget.blur(); }}
              title={penuh ? 'Keluar layar penuh' : 'Layar penuh'} aria-label={penuh ? 'Keluar layar penuh' : 'Layar penuh'}>{penuh ? '✕' : '⛶'}</button>
          </div>
          {tampilKendali && (
            <>
              <div className="rt-joy" onPointerDown={(e) => {
                e.preventDefault();
                joyId.current = e.pointerId;
                e.currentTarget.setPointerCapture(e.pointerId);
                gerakJoy(e);
              }} onPointerMove={(e) => {
                if (joyId.current === e.pointerId) gerakJoy(e);
              }} onPointerUp={lepasJoy} onPointerCancel={lepasJoy} onContextMenu={(e) => e.preventDefault()}>
                <div ref={knob} className="rt-knob" />
              </div>
              <div className="rt-btns">
                {wpn !== 'tidak' && (
                  <button type="button" className={`rt-btn senjata ${aktifSenjata || tahan.current.senjata ? 'on' : ''}`}
                    onPointerDown={(e) => { e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); tombolLayar('senjata', true); }}
                    onPointerUp={() => tombolLayar('senjata', false)} onPointerCancel={() => tombolLayar('senjata', false)}
                    onContextMenu={(e) => e.preventDefault()}>
                    <span>{IKON[wpn]}</span><small>{labelSenjata}{SAKLAR.has(wpn) ? (aktifSenjata ? ' ON' : ' OFF') : ''}</small>
                  </button>
                )}
                {bisaBalik && (
                  <button type="button" className={`rt-btn balik ${mine?.terbalik ? 'perlu' : ''}`}
                    onPointerDown={(e) => { e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); tombolLayar('balik', true); }}
                    onPointerUp={() => tombolLayar('balik', false)} onPointerCancel={() => tombolLayar('balik', false)}
                    onContextMenu={(e) => e.preventDefault()}>
                    <span>↻</span><small>Balik</small>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
        {pemain && !touchScreen && (
          <p className="hint rt-keys">
            <kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> / panah: jalan & belok ·{' '}
            <kbd>Spasi</kbd>: {SAKLAR.has(wpn) ? 'nyalakan/matikan senjata' : wpn === 'tidak' ? '(tanpa senjata: seruduk dari depan)' : 'tahan untuk menyerang'}
            {bisaBalik && <> · <kbd>E</kbd>: berdiri lagi</>}
          </p>
        )}
      </div>
      <Papan view={v} names={names} me={me} />
    </div>
  );
}
