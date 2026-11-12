import { useEffect, useState } from 'react';
import { seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const WARNA: Record<string, string> = {
  coklat: '#8b5a2b', biru_muda: '#7cc7f2', merah_muda: '#e46fb0', oranye: '#f2933a', merah: '#e5484d', kuning: '#e2c12f',
  hijau: '#2fa84f', biru_tua: '#3657c9',
};
const IKON: Record<string, string> = {
  mulai: '🏁', dana: '💰', kesempatan: '❓', pajak: '🧾', transport: '🚉', utilitas: '💡', penjara: '🚔', parkir: '🅿️', ke_penjara: '👮',
};
const KALI = [1, 5, 14, 38, 50, 62];
const DADU = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];

function gridPos(i: number): [number, number] {
  if (i <= 10) return [11, 11 - i];
  if (i < 20) return [11 - (i - 10), 1];
  if (i <= 30) return [1, i - 19];
  return [i - 29, 11];
}

const short = (n: string) => n.replace('Pelabuhan ', 'Pel. ').replace('Bandara ', 'Bdr. ').replace('Stasiun ', 'St. ')
  .replace('Pajak Penghasilan', 'Pajak').replace('Pajak Barang Mewah', 'Pajak Mewah').replace('Masuk Penjara', 'Ke Penjara');

function rumah(h: number) {
  return h === 5 ? '🏨' : h > 0 ? '🏠'.repeat(h) : '';
}

export function RMonopoli({ view, names, me, canAct, acted, act, draft, replay }: RenderProps) {
  const v = view;
  const papan: any[] = v.papan ?? [];
  const myName = me != null ? names[me] : null;
  const my = myName ? v.pemain?.[myName] : null;
  const [sel, setSel] = useState<number | null>(null);
  const [panel, setPanel] = useState<'kelola' | 'tawar' | null>(null);
  const [bid, setBid] = useResetState<number>(0, `${v.lelang?.petak ?? -1}-${v.putaran}-${v.giliran}`);
  const [trade, setTrade] = useState<{ ke: string; beriU: number; mintaU: number; beri: number[]; minta: number[] }>({ ke: '', beriU: 0, mintaU: 0, beri: [], minta: [] });
  const lelangMine = v.fase === 'lelang' && canAct;
  useEffect(() => {
    if (lelangMine) draft?.({ lelang: bid });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lelangMine, v.lelang?.petak]);

  const tokens: Record<number, string[]> = {};
  for (const [n, p] of Object.entries(v.pemain ?? {}) as [string, any][]) {
    if (!p.bangkrut) (tokens[p.posisi] ??= []).push(n);
  }
  const sq = sel != null ? papan[sel] : null;
  const myTurn = canAct && v.giliran === myName && (v.fase === 'awal' || v.fase === 'akhir');
  const mineProps = papan.filter((p) => p.pemilik === myName);
  const groupHasHouses = (grp: string | null) => !!grp && papan.some((p) => p.kelompok === grp && p.rumah > 0);
  const tradable = (owner: string) => papan.filter((p) => p.pemilik === owner && !groupHasHouses(p.kelompok));
  const others = names.filter((n) => n !== myName && !v.pemain?.[n]?.bangkrut);

  const cells = papan.map((p, i) => {
    const [r, c] = gridPos(i);
    const owner = p.pemilik ? idxOf(names, p.pemilik) : -1;
    return (
      <button key={i} type="button" className={`mp-sq ${p.gadai ? 'gadai' : ''} ${sel === i ? 'sel' : ''} ${r === 11 || r === 1 ? 'h' : 'v'}`}
        style={{ gridRow: r, gridColumn: c, ['--own' as string]: owner >= 0 ? seatColor(owner) : 'transparent' }} onClick={() => setSel(i)}>
        {p.kelompok && WARNA[p.kelompok] && <span className="mp-strip" style={{ background: WARNA[p.kelompok] }} />}
        <span className="mp-name">{IKON[p.jenis] ?? ''}{short(p.nama)}</span>
        {p.harga > 0 && p.jenis !== 'pajak' && !p.pemilik && <span className="mp-price">{p.harga}</span>}
        {p.rumah > 0 && <span className="mp-house">{rumah(p.rumah)}</span>}
        {tokens[i] && <span className="mp-tokens">{tokens[i].map((n) => <i key={n} style={{ background: seatColor(idxOf(names, n)) }} title={n} />)}</span>}
      </button>
    );
  });

  const offer = v.tawaran;
  return (
    <div className="game-grid mp">
      <div className="panel">
        <div className="row"><b>Putaran {v.putaran}/{v.batas_putaran}</b><span className="spacer" />
          {v.jackpot > 0 && <span className="tag-mini">🅿️ jackpot {v.jackpot}</span>}</div>
        <div className="mp-board">
          {cells}
          <div className="mp-center">
            <div className="mp-dice">{v.dadu ? `${DADU[v.dadu[0]]}${DADU[v.dadu[1]]}` : '🎲'}</div>
            {v.giliran && <div>Giliran <NameChip name={v.giliran} idx={idxOf(names, v.giliran)} /></div>}
            {v.kartu_terakhir && <div className="mp-card">🃏 {v.kartu_terakhir}</div>}
            <ul className="mp-log">{(v.riwayat ?? []).slice(-4).reverse().map((e: any, k: number) => <li key={k}>{e.jenis === 'giliran' ? `— giliran ${e.pemain}` : e.jenis.replace('_', ' ')}{e.pemain && e.jenis !== 'giliran' ? ` · ${e.pemain}` : ''}{e.nama ? ` · ${e.nama}` : ''}{e.jumlah ? ` (${e.jumlah})` : ''}</li>)}</ul>
          </div>
        </div>
        {sq && (
          <div className="mp-detail">
            <div className="row">{sq.kelompok && WARNA[sq.kelompok] && <span className="mp-chip" style={{ background: WARNA[sq.kelompok] }} />}
              <b>{sq.nama}</b><span className="spacer" /><button type="button" className="btn small" onClick={() => setSel(null)}>✕</button></div>
            {sq.harga > 0 && <p className="hint">Harga {sq.harga}{sq.pemilik ? ` · milik ${sq.pemilik}` : ' · belum dimiliki'}{sq.gadai ? ' · DIGADAI' : ''}{sq.rumah ? ` · ${rumah(sq.rumah)}` : ''}</p>}
            {sq.jenis === 'kota' && (
              <p className="hint">Sewa: dasar {sq.sewa_dasar} (×2 kalau kelompok lengkap) · {KALI.slice(1).map((k, j) => `${j < 4 ? `${j + 1}🏠` : '🏨'} ${sq.sewa_dasar * k}`).join(' · ')} · rumah {sq.harga_rumah}</p>
            )}
            {sq.jenis === 'transport' && <p className="hint">Sewa 25 / 50 / 100 / 200 untuk 1–4 transportasi.</p>}
            {sq.jenis === 'utilitas' && <p className="hint">Sewa 4× dadu (10× kalau punya PLN dan PDAM).</p>}
          </div>
        )}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {v.fase === 'lelang' ? 'Lelang tertutup: kirim tawaranmu.' : v.fase === 'tawaran' ? `${offer?.dari} menawarkan tukar-menukar.` : v.fase === 'beli' ? 'Beli petak ini?' : v.fase === 'awal' ? 'Lempar dadu (atau kelola propertimu dulu).' : 'Kelola properti atau selesaikan giliran.'}
        </TurnNote>
        {canAct && v.fase === 'awal' && (
          <div className="row mp-actions">
            <button type="button" className="btn primary big" onClick={() => act('lempar')}>🎲 Lempar dadu</button>
            {my?.penjara && my.uang >= 50 && <button type="button" className="btn" onClick={() => act('bayar_penjara')}>Bayar 50, keluar penjara</button>}
            {my?.penjara && my.kartu_bebas > 0 && <button type="button" className="btn" onClick={() => act('kartu_bebas')}>Pakai kartu bebas</button>}
          </div>
        )}
        {canAct && v.fase === 'beli' && my && (
          <div className="row mp-actions">
            <b>{papan[my.posisi].nama}</b> <span className="hint">harga {papan[my.posisi].harga} · uangmu {my.uang}</span>
            <button type="button" className="btn primary" disabled={my.uang < papan[my.posisi].harga} onClick={() => act('beli')}>Beli</button>
            <button type="button" className="btn" onClick={() => act('tolak')}>Tolak{v.fase === 'beli' ? ' (dilelang)' : ''}</button>
          </div>
        )}
        {canAct && v.fase === 'akhir' && (
          <div className="row mp-actions"><button type="button" className="btn primary big" onClick={() => act('selesai')}>✅ Selesai giliran</button></div>
        )}
        {lelangMine && v.lelang && my && (
          <div className="mp-lelang">
            <b>🔨 Lelang {papan[v.lelang.petak].nama}</b> <span className="hint">(harga {v.lelang.harga}, tawaran rahasia, 0 = tidak ikut)</span>
            <NumberPicker value={bid} min={0} max={my.uang} step={5} onChange={(x) => { setBid(x); draft?.({ lelang: x }); }} />
            <button type="button" className="btn primary" onClick={() => act({ lelang: bid })}>Kirim tawaran {bid}</button>
          </div>
        )}
        {canAct && v.fase === 'tawaran' && offer && (
          <div className="mp-offer">
            <b>🤝 Tawaran dari {offer.dari}</b>
            <p>Kamu dapat: {offer.beri.uang ? `💰${offer.beri.uang} ` : ''}{offer.beri.properti.map((i: number) => papan[i].nama).join(', ') || (offer.beri.uang ? '' : '–')}</p>
            <p>Kamu beri: {offer.minta.uang ? `💰${offer.minta.uang} ` : ''}{offer.minta.properti.map((i: number) => papan[i].nama).join(', ') || (offer.minta.uang ? '' : '–')}</p>
            <div className="row"><button type="button" className="btn primary" onClick={() => act('terima')}>Terima</button>
              <button type="button" className="btn" onClick={() => act('tolak')}>Tolak</button></div>
          </div>
        )}
        {myTurn && (
          <div className="row mp-tabs">
            <button type="button" className={`btn small ${panel === 'kelola' ? 'primary' : ''}`} onClick={() => setPanel(panel === 'kelola' ? null : 'kelola')}>🏗️ Kelola properti</button>
            {v.boleh_tawar && others.length > 0 && (
              <button type="button" className={`btn small ${panel === 'tawar' ? 'primary' : ''}`} onClick={() => setPanel(panel === 'tawar' ? null : 'tawar')}>🤝 Tawar tukar</button>
            )}
          </div>
        )}
        {myTurn && panel === 'kelola' && (
          <ul className="mp-manage">
            {mineProps.length === 0 && <li className="hint">Belum punya properti.</li>}
            {mineProps.map((p) => {
              const grpMax = Math.max(...papan.filter((x) => x.kelompok === p.kelompok).map((x) => x.rumah));
              return (
                <li key={p.id}>
                  {p.kelompok && WARNA[p.kelompok] && <span className="mp-chip" style={{ background: WARNA[p.kelompok] }} />}
                  <span className="mp-mname">{p.nama} {rumah(p.rumah)}{p.gadai ? ' (gadai)' : ''}</span>
                  {(v.bisa_bangun ?? []).includes(p.id) && <button type="button" className="btn small" onClick={() => act({ bangun: p.id })}>+🏠 {p.harga_rumah}</button>}
                  {p.rumah > 0 && p.rumah === grpMax && <button type="button" className="btn small" onClick={() => act({ jual_rumah: p.id })}>−🏠</button>}
                  {!p.gadai && !groupHasHouses(p.kelompok) && <button type="button" className="btn small" onClick={() => act({ gadai: p.id })}>Gadai +{Math.floor(p.harga / 2)}</button>}
                  {p.gadai && <button type="button" className="btn small" disabled={(my?.uang ?? 0) < Math.floor(p.harga * 0.55)} onClick={() => act({ tebus: p.id })}>Tebus {Math.floor(p.harga * 0.55)}</button>}
                </li>
              );
            })}
          </ul>
        )}
        {myTurn && panel === 'tawar' && (
          <div className="mp-trade">
            <label className="field inline"><span>Tawar ke</span>
              <select className="input" value={trade.ke} onChange={(e) => setTrade({ ...trade, ke: e.target.value, minta: [] })}>
                <option value="">pilih pemain…</option>
                {others.map((n) => <option key={n} value={n}>{n}</option>)}
              </select></label>
            {trade.ke && (
              <div className="mp-trade-cols">
                <div><b>Kamu beri</b>
                  <label className="field inline"><span>Uang</span><input type="number" min={0} max={my?.uang ?? 0} value={trade.beriU} onChange={(e) => setTrade({ ...trade, beriU: Number(e.target.value) })} /></label>
                  {tradable(myName!).map((p) => (
                    <label key={p.id} className="mp-check"><input type="checkbox" checked={trade.beri.includes(p.id)}
                      onChange={(e) => setTrade({ ...trade, beri: e.target.checked ? [...trade.beri, p.id] : trade.beri.filter((x) => x !== p.id) })} /> {p.nama}</label>
                  ))}
                </div>
                <div><b>Kamu minta</b>
                  <label className="field inline"><span>Uang</span><input type="number" min={0} value={trade.mintaU} onChange={(e) => setTrade({ ...trade, mintaU: Number(e.target.value) })} /></label>
                  {tradable(trade.ke).map((p) => (
                    <label key={p.id} className="mp-check"><input type="checkbox" checked={trade.minta.includes(p.id)}
                      onChange={(e) => setTrade({ ...trade, minta: e.target.checked ? [...trade.minta, p.id] : trade.minta.filter((x) => x !== p.id) })} /> {p.nama}</label>
                  ))}
                </div>
              </div>
            )}
            {trade.ke && (
              <button type="button" className="btn primary" onClick={() => {
                act({ tawar: { ke: trade.ke, beri: { uang: trade.beriU, properti: trade.beri }, minta: { uang: trade.mintaU, properti: trade.minta } } });
                setTrade({ ke: '', beriU: 0, mintaU: 0, beri: [], minta: [] });
                setPanel(null);
              }}>Kirim tawaran</button>
            )}
          </div>
        )}
      </div>
      <ScoreBoard me={me} title={v.batas_putaran ? 'Kekayaan' : 'Skor'} rows={names.map((n, i) => {
        const p = v.pemain?.[n] ?? {};
        const props = papan.filter((x) => x.pemilik === n).length;
        return { name: n, idx: i, value: p.bangkrut ? 'bangkrut' : (p.kekayaan ?? '?'), sub: p.bangkrut ? undefined : `💰${p.uang ?? '?'} · ${props} properti${p.penjara ? ' · 🚔' : ''}`, dim: p.bangkrut,
          raw: p.bangkrut ? -1e9 : (p.kekayaan ?? 0) };
      }).sort((a, b) => b.raw - a.raw)} />
    </div>
  );
}
