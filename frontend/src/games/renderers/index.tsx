import { useState, type ComponentType } from 'react';
import { TurnNote, type RenderProps } from './common';
import { REvolusi } from './evolusi';
import { RKapal } from './kapal';
import { RKartu } from './kartu';
import { RLabirin } from './labirin';
import { RMonopoli } from './monopoli';
import { RPoker } from './poker';
import { RRobot } from './robot';
import { RSatu } from './satu';
import { RBlotto, RDuaPertiga, RFarol, RKasDesa, RLelang, RSuit } from './simple';
import { RTycoon } from './tycoon';
import { RWordle } from './wordle';
import { RDomino } from './domino';
import { RUlar } from './ular';
import { RTembak } from './tembak';
import { RHitungUang } from './hitunguang';
import { RTebakGambar } from './tebakgambar';

export type { RenderProps } from './common';

/** Tampilan cadangan untuk game yang belum punya renderer khusus. */
function RGeneric({ view, canAct, acted, act, replay, me }: RenderProps) {
  const [raw, setRaw] = useState('');
  return (
    <div className="panel">
      <TurnNote canAct={canAct} acted={acted} replay={replay} me={me} />
      {canAct && (
        <div className="row">
          <input className="input" value={raw} onChange={(e) => setRaw(e.target.value)} placeholder='Aksi (JSON), misalnya "datang" atau [1, 2]' />
          <button type="button" className="btn primary" onClick={() => {
            try {
              act(JSON.parse(raw));
            } catch {
              act(raw);
            }
          }}>Kirim</button>
        </div>
      )}
      <pre className="code-preview">{JSON.stringify(view, null, 2)}</pre>
    </div>
  );
}

const RENDERERS: Record<string, ComponentType<RenderProps>> = {
  suit: RSuit,
  poker: RPoker,
  kapal: RKapal,
  robot: RRobot,
  kartu: RKartu,
  tycoon: RTycoon,
  lelang: RLelang,
  blotto: RBlotto,
  kasdesa: RKasDesa,
  duapertiga: RDuaPertiga,
  farol: RFarol,
  wordle: RWordle,
  labirin: RLabirin,
  satu: RSatu,
  evolusi: REvolusi,
  monopoli: RMonopoli,
  domino: RDomino,
  ular: RUlar,
  tembak: RTembak,
  hitunguang: RHitungUang,
  tebakgambar: RTebakGambar,
};

export function rendererFor(gid: string): ComponentType<RenderProps> {
  return RENDERERS[gid] ?? RGeneric;
}

const fmtN = (n: number) => (Number.isFinite(n) ? n.toLocaleString('id-ID', { maximumFractionDigits: 2 }) : String(n));

const KATA: Record<string, string> = {
  tutup: 'tutup lapak', datang: 'datang', rumah: 'di rumah', pasar: '🎡 Pasar Malam', konser: '🎤 Konser', bazar: '🍢 Bazar Kuliner', batu: '✊ BATU', gunting: '✌️ GUNTING', kertas: '✋ KERTAS',
  diam: 'diam', atas: 'jalan ↑', bawah: 'jalan ↓', kiri: 'jalan ←', kanan: 'jalan →',
};

/** Teks singkat untuk jawaban yang sudah dikirim (ditampilkan sebagai "Jawabanmu: …"). */
export function describeAction(a: any): string {
  if (a == null) return '–';
  if (typeof a === 'number') return fmtN(a);
  if (typeof a === 'string') {
    if (a.startsWith('tembak_')) return `tembak ${a.slice(7)}`;
    return KATA[a] ?? a;
  }
  if (Array.isArray(a)) {
    if (a.every((x) => typeof x === 'number')) return a.join(' · ');
    return 'susunan dikirim';
  }
  if (typeof a === 'object') {
    if (a.produk) return `${a.produk.replace('_', ' ')} ×${a.jumlah} @Rp${Number(a.harga).toLocaleString('id-ID')}${a.iklan ? ` + iklan Rp${Number(a.iklan).toLocaleString('id-ID')}` : ''}`;
    if (a.aksi) return a.aksi === 'raise' ? `raise ke ${fmtN(a.ke)}` : a.aksi;
    if (a.susun) return 'susunan armada';
    if (a.tembak) return `tembak (${a.tembak[0]},${a.tembak[1]})`;
    if (a.sonar) return `sonar (${a.sonar[0]},${a.sonar[1]})`;
    if (a.tempat) return a.tempat;
    if ('sanksi' in a || 'denda' in a || 'usir' in a) {
      const d = Object.entries(a.denda ?? {}).filter(([, x]) => Number(x) > 0).map(([n, x]) => `${n} ${x}`);
      const parts = [d.length ? `denda ${d.join(', ')}` : 'tanpa denda'];
      if (a.usir) parts.push(`usir ${a.usir}`);
      return parts.join(' · ');
    }
  }
  return JSON.stringify(a);
}

/** Teks singkat untuk satu kejadian (log live & replay). */
export function describeEvent(e: any): string | null {
  switch (e?.jenis) {
    case 'waktu_habis': {
      const parts: string[] = [];
      if (e.otomatis?.length) parts.push(`pilihan terakhir ${e.otomatis.join(', ')} dikirim otomatis`);
      if (e.pemain?.length) parts.push(`${e.pemain.join(', ')} memakai aksi bawaan`);
      return parts.length ? `⏰ Waktu habis: ${parts.join(' · ')}` : null;
    }
    case 'ronde':
      if (e.target != null && e.rata != null) {
        const ac = e.acuan === 'median' ? `median ${fmtN(e.median)}` : `rata ${fmtN(e.rata)}`;
        const f = e.faktor != null ? ` × ${fmtN(e.faktor)}` : '';
        const g = e.gugur?.length ? ` · gugur: ${e.gugur.join(', ')}` : '';
        const pts = Object.entries(e.poin ?? {});
        const p = pts.length > 1 ? ` (${pts.sort((x: any, y: any) => y[1] - x[1]).map(([n, x]) => `${n} +${x}`).join(', ')})` : '';
        return `Ronde ${e.ronde}: ${ac}${f} → target ${fmtN(e.target)}, menang ${e.pemenang.join(', ') || '–'}${p}${g}`;
      }
      if (e.bagian != null) {
        const t = e.target ? (e.tercapai ? ` · ✅ target ${e.target} tercapai, bonus +${e.bonus}` : ` · ❌ target ${e.target} gagal`) : '';
        return `Ronde ${e.ronde}: kas ${e.total}, tiap orang +${fmtN(e.bagian)}${t}`;
      }
      if (e.penguasa) {
        const pts = Object.entries(e.poin ?? {}).sort((x: any, y: any) => y[1] - x[1]).map(([n, x]) => `${n} +${fmtN(Number(x))}`).join(', ');
        return `Ronde ${e.ronde}: ${pts || 'selesai'}`;
      }
      if (e.jumlah) return `Ronde ${e.ronde}: batu ${e.jumlah.batu}, gunting ${e.jumlah.gunting}, kertas ${e.jumlah.kertas}${e.gugur?.length ? ` · gugur ${e.gugur.join(', ')}` : ''}`;
      return `Ronde ${e.ronde}`;
    case 'malam': {
      const sp = e.spesial === 'festival' ? ' 🎉' : e.spesial === 'hujan' ? ' 🌧️' : '';
      if (e.tempat?.length > 1) return `Malam ${e.malam}${sp}: ${e.tempat.map((t: any) => `${t.nama} ${t.jumlah ?? '?'}/${t.kapasitas ?? '?'} ${t.ramai ? 'sumpek' : 'nyaman'}`).join(' · ')}`;
      return `Malam ${e.malam}${sp}: ${e.jumlah ?? '?'} datang, kapasitas ${e.kapasitas ?? '?'} (${e.ramai ? 'sumpek' : 'nyaman'})`;
    }
    case 'sanksi': {
      const d = Object.entries(e.denda ?? {}).map(([a, t]: [string, any]) => `${a}→${Object.keys(t).join('/')}`);
      return `⚖️ Sanksi ronde ${e.ronde}: ${d.length ? `denda ${d.join(', ')}` : 'tanpa denda'}${e.diusir?.length ? ` · diusir ${e.diusir.join(', ')}` : ''}`;
    }
    case 'bencana': return `🌊 Banjir! Target kas gagal 2 ronde berturut-turut, semua kehilangan tabungan`;
    case 'dividen': {
      const b = Object.entries(e.bayar ?? {}).filter(([, x]) => Number(x) > 0).map(([n, x]) => `${n} +${x}`);
      return `💰 Dividen ${e.persen}% setelah ronde ${e.ronde}: ${b.join(', ') || 'belum ada yang dapat'}`;
    }
    case 'lelang': return e.pemenang ? `${e.nama} (${e.nilai}) → ${e.pemenang} seharga ${e.harga}` : `${e.nama}: ${e.hangus ? 'seri, hangus' : 'tidak laku'}`;
    case 'hari': return `Hari ${e.hari} (${e.cuaca}) selesai`;
    case 'tangan_baru': return `Tangan #${e.no}: dealer ${e.dealer}, blind ${e.sb}/${e.bb}`;
    case 'aksi': return `${e.pemain}: ${e.aksi}${e.jumlah ? ` ${fmtN(e.jumlah)}` : ''}`;
    case 'jalan': return `${e.jalan.toUpperCase()}: ${e.kartu.join(' ')}`;
    case 'kembali': return `${e.jumlah} chip dikembalikan ke ${e.pemain}`;
    case 'tangan_selesai': {
      const w = Object.entries(e.menang).map(([n, x]) => `${n} +${fmtN(Number(x))}`).join(', ');
      return `Tangan #${e.no} selesai: ${w}${e.tersingkir?.length ? ` · tersingkir ${e.tersingkir.join(', ')}` : ''}`;
    }
    case 'susun': return `${e.pemain.join(', ')} selesai menyusun armada`;
    case 'mulai_tembak': return `Perang dimulai! ${e.pertama} menembak duluan`;
    case 'sonar': return `📡 ${e.penembak} memakai sonar di (${e.sonar[0]},${e.sonar[1]}): ${e.jumlah} petak kapal`;
    case 'lewati': return `⏭️ Giliran ${e.pemain} dilewati (kena ranjau)`;
    case 'tembak':
      if (e.nomor != null) {
        if (e.sandera) return e.tahan ? `🧍 ${e.pemain} menahan tembakan ke sandera (+10)` : `😱 ${e.pemain} menembak sandera! (−30)`;
        if (e.meleset || !e.cincin) return e.ms == null ? null : `🎯 ${e.pemain} meleset${e.catatan ? ` (${e.catatan})` : ''}`;
        return `🎯 ${e.pemain}: cincin ${e.cincin} dalam ${e.ms} ms → +${e.poin}`;
      }
      if (e.hasil === 'ranjau') return `💥 ${e.penembak} menembak ranjau di (${e.baris},${e.kolom})! Giliran berikutnya dilewati`;
      if (e.hasil) return `${e.penembak} → (${e.baris},${e.kolom}): ${e.hasil}${e.ukuran ? ` kapal ${e.ukuran}` : ''}`;
      return `${e.pemain} menembak ${e.arah}${e.kena ? `, kena ${e.kena}` : ''}`;
    case 'hancur': return e.badai ? `💥 ${e.pemain} hancur ditelan badai` : `💥 ${e.pemain} hancur (oleh ${e.oleh.join(', ')})`;
    case 'kristal': return `◆ ${e.pemain} mengambil kristal`;
    case 'powerup': return `${({ senjata: '⚡', perisai: '🛡️', nyawa: '❤️' } as Record<string, string>)[e.powerup] ?? '?'} ${e.pemain} mengambil power-up ${e.powerup}`;
    case 'perisai': return `🛡️ Perisai ${e.pemain} menahan tembakan ${e.oleh?.join(', ') ?? ''}`;
    case 'badai': return `🌀 ${e.pemain} terkena badai di luar zona (−1 nyawa)`;
    case 'zona': return `🌀 Zona aman menyempit: baris/kolom ${e.zona[0]}–${e.zona[1]}`;
    case 'bangkit': return e.pemilik ? `🌱 Spesies ${e.pemilik} muncul lagi di sarangnya` : `${e.pemain} bangkit lagi`;
    case 'mulai': return e.desain ? `🧬 Desain: ${Object.entries(e.desain).map(([n, d]: [string, any]) => `${n} 👁️${d.pandangan} 🐾${d.kelincahan} 🦣${d.ukuran}`).join(' · ')}` : null;
    case 'lahir': return `🍼 ${e.pemilik}: ${e.nama} lahir dari ${e.induk}${e.mutasi ? ` (mutasi ${e.mutasi.sifat} ${e.mutasi.ubah > 0 ? '+1' : '−1'})` : ''}`;
    case 'mati': return e.sebab === 'dimangsa' ? null : `💀 ${e.nama} milik ${e.pemilik} mati ${e.sebab === 'lapar' ? 'kelaparan' : 'karena jebakan'}`;
    case 'mangsa': return `🦷 ${e.nama} (${e.pemilik}) memangsa ${e.korban} (${e.korban_pemilik})`;
    case 'pasang': return `${e.rintangan === 'batu' ? '🪨' : '🌵'} ${e.pemilik} memasang ${e.rintangan}`;
    case 'punah': return `☠️ Spesies ${e.pemilik} punah!`;
    case 'akhir': return `🏁 Selesai. Bertahan: ${Object.entries(e.hidup ?? {}).map(([n, x]) => `${n} ${x}`).join(', ')}`;
    case 'kemajuan': return `${e.pemain}: lantai ${e.lantai}, ${e.fase} (skor ${e.skor})`;
    case 'tebak': {
      if (e.tebakan != null) {
        if (e.benar) return `🎉 ${e.pemain} menebak "${e.tebakan}" — BENAR! Gambarnya ${e.gambar?.emoji ?? ''} ${e.gambar?.nama ?? ''} (+${e.poin})`;
        return e.kalah ? `💀 ${e.pemain} menebak "${e.tebakan}" — salah, kesempatan habis. Gambarnya ${e.gambar?.emoji ?? ''} ${e.gambar?.nama ?? ''}`
          : `❌ ${e.pemain} menebak "${e.tebakan}" — salah (sisa ${e.sisa} kesempatan)`;
      }
      if (e.lewat) return `${e.pemain}: baris ${e.baris} hangus`;
      const kotak = e.warna ? [...e.warna].map((c: string) => (c === 'H' ? '🟩' : c === 'K' ? '🟨' : c === '?' ? '❔' : '⬜')).join('') : '▫️▫️▫️▫️▫️';
      return `${e.pemain} menebak ${e.kata ? e.kata.toUpperCase() : '•••••'} ${kotak}${e.bantu ? ' (+1 huruf hijau baru)' : ''}`;
    }
    case 'benar': return `🎉 ${e.pemain} menebak benar di baris ${e.baris} (urutan ke-${e.urutan}, +${e.poin})`;
    case 'lewat': return e.ujung !== undefined ? `${e.pemain} lewat${e.ujung ? ` (ujung ${e.ujung[0]} | ${e.ujung[1]})` : ''}${e.denda ? `, denda −${e.denda}` : ''}` : `${e.pemain} melewati giliran`;
    case 'kata': {
      const jw = e.jawaban ? e.jawaban.toUpperCase() : Object.entries(e.jawaban_pemain ?? {}).map(([n, w]) => `${n}: ${String(w).toUpperCase()}`).join(', ');
      const m = Object.entries(e.hasil ?? {}).filter(([, h]: [string, any]) => h.menang).map(([n, h]: [string, any]) => `${n} +${h.poin}`);
      return `📖 Kata ${e.ronde}: ${jw} · ${m.length ? m.join(', ') : 'tidak ada yang menebak'}`;
    }
    case 'gerak': return null;
    case 'finis': return `🏁 ${e.pemain} keluar dari labirin! Urutan ke-${e.urutan} (+${e.poin}, ${e.langkah} langkah)`;
    case 'koin': return `🪙 ${e.pemain} mengambil koin`;
    case 'jebakan':
      if (e.rusak != null) return `${e.duri_milik ? '🌵' : '🕳️'} ${e.nama} milik ${e.pemilik} menginjak ${e.duri_milik ? `duri ${e.duri_milik}` : 'jebakan'} (−${e.rusak} HP)`;
      return `🕳️ ${e.pemain} terjebak di (${e.posisi[0]},${e.posisi[1]})! −${e.hukuman} jatah langkah`;
    case 'portal': return `🌀 ${e.pemain} masuk portal`;
    case 'tanda': return `📍 ${e.pemain} memberi tanda ${e.simbol} di (${e.posisi[0]},${e.posisi[1]})`;
    case 'tali': return e.habis ? `🧵 Tali ${e.pemain} habis` : `🧵 ${e.pemain} ${e.aktif ? 'menyalakan' : 'mematikan'} tali`;
    case 'suar': return `🔦 ${e.pemain} menyalakan suar`;
    case 'labirin': return `🧭 Labirin ${e.ronde} selesai: ${e.urutan.length ? e.urutan.map((n: string, k: number) => `#${k + 1} ${n}`).join(', ') : 'tidak ada yang keluar'} (jalur terpendek ${e.jalur_terpendek})`;
    case 'main': {
      if (!e.kartu) return null;
      const k = e.kartu;
      const ikon: Record<string, string> = { merah: '🟥', kuning: '🟨', hijau: '🟩', biru: '🟦', liar: '🌈' };
      return `${e.pemain} main ${ikon[k.warna] ?? ''}${k.teks}${k.warna === 'liar' ? ` → ${ikon[e.warna] ?? e.warna}` : ''}${e.target ? ` ke ${e.target}` : ''} (sisa ${e.sisa})`;
    }
    case 'ambil':
      if (e.sisa_tumpukan != null) return `${e.pemain} ${e.bom ? 'kena bom, ' : ''}mengambil kartu dari tumpukan (sisa ${e.sisa_tumpukan})`;
      return e.kena ? `${e.pemain} kena ${e.kena}: ambil ${e.jumlah ?? '?'} kartu` : `${e.pemain} mengambil ${e.jumlah ?? 'beberapa'} kartu${e.tumpukan ? ' (tumpukan)' : ''}`;
    case 'teriak': return `📢 ${e.pemain}: SATU!`;
    case 'lupa_satu': return `😅 ${e.pemain} lupa teriak SATU! Tarik ${e.jumlah} kartu`;
    case 'dilewati': return `⊘ ${e.pemain} dilewati`;
    case 'balik': return `⇄ Arah berbalik`;
    case 'tukar': return `🔄 ${e.pemain} bertukar kartu dengan ${e.dengan}${e.kartu ? ` (${e.kartu})` : ''}`;
    case 'putar': return `🌀 Semua kartu di tangan berpindah ke pemain berikutnya${e.kartu ? ` (${e.kartu})` : ''}`;
    case 'efek_tarik': return `✨ ${e.kartu}: ${e.pemain} menarik ${e.jumlah ?? 'beberapa'} kartu`;
    case 'efek_lewati': return `✨ ${e.kartu}: ${e.jumlah} pemain berikutnya dilewati`;
    case 'efek_lagi': return `✨ ${e.kartu}: ${e.pemain} main lagi`;
    case 'efek_warna': return `✨ ${e.kartu}: warna jadi ${e.warna}`;
    case 'efek_buang': return `✨ ${e.kartu}: ${e.pemain} membuang ${e.jumlah} kartu`;
    case 'efek_beri': return `✨ ${e.kartu}: ${e.dari} memberi ${e.jumlah} kartu ke ${e.ke}`;
    case 'efek_poin': return `✨ ${e.kartu}: ${e.pemain} ${e.poin >= 0 ? '+' : ''}${e.poin} poin`;
    case 'efek_pesan': return `💬 ${e.kartu}: ${e.teks}`;
    case 'efek_gagal': return `⚠️ Kartu ${e.kartu} error (tanpa efek): ${e.pesan}`;
    case 'menang_ronde': return `🏆 Ronde ${e.ronde}: ${e.pemenang} habis kartu, +${e.poin} poin`;
    case 'lempar': return `🎲 ${e.pemain} melempar ${e.dadu[0]} + ${e.dadu[1]}${e.dadu[0] === e.dadu[1] ? ' (kembar!)' : ''}`;
    case 'gaji': return `🏁 ${e.pemain} lewat Mulai, terima ${e.jumlah}`;
    case 'beli': return `🏷️ ${e.pemain} membeli ${e.nama} (${e.harga})`;
    case 'tolak_beli': return `${e.pemain} tidak membeli ${e.nama}`;
    case 'tawar_beli': return null;
    case 'sewa': return `💸 ${e.pemain} bayar sewa ${e.jumlah} ke ${e.ke} (${e.nama})`;
    case 'pajak': return `🧾 ${e.pemain} bayar ${e.nama} ${e.jumlah}`;
    case 'kartu': return `🃏 ${e.pemain} (${e.dek}): ${e.teks}`;
    case 'penjara': return `🚔 ${e.pemain} masuk penjara (${e.sebab})`;
    case 'keluar_penjara': return `🔓 ${e.pemain} keluar penjara (${e.cara})`;
    case 'lelang_hasil': return e.pemenang ? `🔨 Lelang ${e.nama}: ${e.pemenang} menang dengan ${e.harga}` : `🔨 Lelang ${e.nama}: tidak ada yang menawar`;
    case 'tawar': return `🤝 ${e.dari} menawarkan tukar-menukar ke ${e.ke}`;
    case 'tukar_diterima': return `🤝 ${e.ke} menerima tawaran ${e.dari}`;
    case 'tukar_ditolak': return `🙅 ${e.ke} menolak tawaran ${e.dari}`;
    case 'bangun': return `🏗️ ${e.pemain} membangun di ${e.nama} (${e.rumah === 5 ? 'hotel' : `${e.rumah} rumah`})`;
    case 'jual_rumah': return `${e.pemain} menjual rumah di ${e.nama}`;
    case 'gadai': return `🏦 ${e.pemain} menggadai ${e.nama}`;
    case 'tebus': return `🏦 ${e.pemain} menebus ${e.nama}`;
    case 'likuidasi': return `⚠️ ${e.pemain} kekurangan uang: ${e.rumah_dijual ? `${e.rumah_dijual} rumah dijual` : ''}${e.digadai?.length ? ` ${e.digadai.join(', ')} digadai` : ''}`;
    case 'bangkrut': return `💀 ${e.pemain} bangkrut${e.ke ? `, hartanya ke ${e.ke}` : ''}`;
    case 'jackpot': return `🅿️ ${e.pemain} dapat jackpot Parkir Bebas ${e.jumlah}`;
    case 'giliran': return null;
    case 'tempel': return `${e.pemain} menempel ${e.kartu[0]}-${e.kartu[1]} di ${e.sisi} → ujung ${e.ujung[0]} | ${e.ujung[1]}${e.sisa <= 1 ? ` (sisa ${e.sisa} kartu!)` : ''}`;
    case 'bom': return e.ambil ? `💣 ${e.pemain} menempel 0-0: ${e.korban} wajib ambil ${e.ambil} kartu` : `💣 ${e.pemain} menempel 0-0: ${e.korban} kena denda ${e.denda}`;
    case 'makan': return e.buah === 'apel' ? null : `${e.buah === 'emas' ? '⭐' : '🤢'} ${e.pemain} makan buah ${e.buah} (${e.poin > 0 ? '+' : ''}${e.poin})`;
    case 'tumbang': return `💥 ${e.pemain} tumbang${({ tepi: ' menabrak tepi', tembok: ' menabrak tembok', badan: '', adu_kepala: ' (adu kepala)' } as Record<string, string>)[e.sebab] ?? ''}${e.oleh ? ` — menabrak badan ${e.oleh} (+2 untuk ${e.oleh})` : ''}${e.keluar ? ', keluar dari ronde' : ''}`;
    case 'jawab':
      if (e.lewat) return `${e.pemain} menyerah untuk gepok ini`;
      return e.benar ? `💰 ${e.pemain} menghitung BENAR (urutan ke-${e.urutan}, +${e.poin})` : `❌ ${e.pemain} salah hitung (${e.poin})${e.habis ? ', kesempatan habis' : ''}`;
    case 'tanya': return `❓ ${e.pemain}: ${e.tanya}`;
    case 'dijawab': return `💬 Jawaban untuk ${e.pemain}: ${Object.entries(e.rangkum ?? {}).map(([w, k]) => `${String(w).replace('_', ' ')} ×${k}`).join(', ')}`;
    case 'habis_waktu': return `⌛ ${e.pemain} belum menebak — gambarnya ${e.gambar?.emoji ?? ''} ${e.gambar?.nama ?? ''}`;
    case 'ronde_selesai': {
      if (e.cara) return `🏁 Ronde ${e.ronde}: ${e.pemenang} menang (${e.cara === 'habis' ? 'kartu habis' : 'meja buntu'})${e.kali > 1 ? ' ×2 tutup balak!' : ''}`;
      if (e.total != null) return `💰 Gepok ${e.ronde}: totalnya Rp${Number(e.total).toLocaleString('id-ID')}${e.urut?.length ? ` · tercepat ${e.urut.slice(0, 3).join(', ')}` : ' · tidak ada yang benar'}`;
      if (e.rata_ms) return `🎯 Ronde ${e.ronde} selesai: ${Object.entries(e.poin ?? {}).sort((a: any, b: any) => b[1] - a[1]).map(([n, p]) => `${n} ${p}`).join(', ')}`;
      return `🐍 Ronde ${e.ronde} selesai${e.terpanjang ? `, terpanjang ${e.terpanjang} (+5)` : ''}`;
    }
    default: return null;
  }
}
