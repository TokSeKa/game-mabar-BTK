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

/** Teks singkat untuk satu kejadian (log live & replay). */
export function describeEvent(e: any): string | null {
  switch (e?.jenis) {
    case 'waktu_habis': return `⏰ Waktu habis: ${e.pemain.join(', ')} memakai aksi bawaan`;
    case 'ronde':
      if (e.target != null) return `Ronde ${e.ronde}: target ${fmtN(e.target)}, menang ${e.pemenang.join(', ') || '–'}`;
      if (e.bagian != null) return `Ronde ${e.ronde}: kas ${e.total}, tiap orang +${fmtN(e.bagian)}`;
      if (e.penguasa) return `Ronde ${e.ronde} selesai`;
      if (e.jumlah) return `Ronde ${e.ronde}: batu ${e.jumlah.batu}, gunting ${e.jumlah.gunting}, kertas ${e.jumlah.kertas}${e.gugur?.length ? ` · gugur ${e.gugur.join(', ')}` : ''}`;
      return `Ronde ${e.ronde}`;
    case 'malam': return `Malam ${e.malam}: ${e.jumlah} datang (${e.ramai ? 'sumpek' : 'nyaman'})`;
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
    case 'tembak':
      if (e.hasil) return `${e.penembak} → (${e.baris},${e.kolom}): ${e.hasil}${e.ukuran ? ` kapal ${e.ukuran}` : ''}`;
      return `${e.pemain} menembak ${e.arah}${e.kena ? `, kena ${e.kena}` : ''}`;
    case 'hancur': return `💥 ${e.pemain} hancur (oleh ${e.oleh.join(', ')})`;
    case 'kristal': return `◆ ${e.pemain} mengambil kristal`;
    case 'bangkit': return `${e.pemain} bangkit lagi`;
    case 'kemajuan': return `${e.pemain}: lantai ${e.lantai}, ${e.fase} (skor ${e.skor})`;
    case 'giliran': return null;
    default: return null;
  }
}
