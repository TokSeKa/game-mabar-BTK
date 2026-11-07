import { useState, type ComponentType } from 'react';
import { TurnNote, type RenderProps } from './common';
import { RKapal } from './kapal';
import { RKartu } from './kartu';
import { RPoker } from './poker';
import { RRobot } from './robot';
import { RBlotto, RDuaPertiga, RFarol, RKasDesa, RLelang, RSuit } from './simple';
import { RTycoon } from './tycoon';

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
      if (e.hasil === 'ranjau') return `💥 ${e.penembak} menembak ranjau di (${e.baris},${e.kolom})! Giliran berikutnya dilewati`;
      if (e.hasil) return `${e.penembak} → (${e.baris},${e.kolom}): ${e.hasil}${e.ukuran ? ` kapal ${e.ukuran}` : ''}`;
      return `${e.pemain} menembak ${e.arah}${e.kena ? `, kena ${e.kena}` : ''}`;
    case 'hancur': return e.badai ? `💥 ${e.pemain} hancur ditelan badai` : `💥 ${e.pemain} hancur (oleh ${e.oleh.join(', ')})`;
    case 'kristal': return `◆ ${e.pemain} mengambil kristal`;
    case 'powerup': return `${({ senjata: '⚡', perisai: '🛡️', nyawa: '❤️' } as Record<string, string>)[e.powerup] ?? '?'} ${e.pemain} mengambil power-up ${e.powerup}`;
    case 'perisai': return `🛡️ Perisai ${e.pemain} menahan tembakan ${e.oleh?.join(', ') ?? ''}`;
    case 'badai': return `🌀 ${e.pemain} terkena badai di luar zona (−1 nyawa)`;
    case 'zona': return `🌀 Zona aman menyempit: baris/kolom ${e.zona[0]}–${e.zona[1]}`;
    case 'bangkit': return `${e.pemain} bangkit lagi`;
    case 'kemajuan': return `${e.pemain}: lantai ${e.lantai}, ${e.fase} (skor ${e.skor})`;
    case 'giliran': return null;
    default: return null;
  }
}
