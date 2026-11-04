import { useState } from 'react';
import { NameChip } from './renderers/common';
import { Grid } from './renderers/kapal';
import { Card } from './renderers/poker';

async function sha256Hex(text: string): Promise<string | null> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch {
    return null;
  }
}

function PokerReveal({ reveal, names }: { reveal: any; names: string[] }) {
  const [cek, setCek] = useState<string | null>(null);
  return (
    <div className="panel">
      <h3>Keadilan dek</h3>
      <p className="hint">
        Seed match: <code>{reveal.seed}</code> · hash yang diumumkan sejak awal: <code>{reveal.hash_dek}</code>.
        {' '}Rumus: {reveal.cara_cek}.
      </p>
      <div className="row">
        <button type="button" className="btn small" onClick={async () => {
          const h = await sha256Hex(`poker|${reveal.seed}`);
          setCek(h == null ? 'Browser ini tidak bisa menghitung SHA-256 (butuh HTTPS).' : h.slice(0, 16) === reveal.hash_dek ? '✓ Cocok: dek tidak diubah selama permainan.' : '✗ Tidak cocok!');
        }}>Cek sendiri di browser</button>
        {cek && <span className={cek.startsWith('✓') ? 'good' : 'bad'}>{cek}</span>}
      </div>
      <details>
        <summary>Semua kartu tertutup ({reveal.kartu_semua?.length ?? 0} tangan terakhir)</summary>
        <div className="reveal-hands">
          {(reveal.kartu_semua ?? []).map((h: any) => (
            <div key={h.no} className="row">
              <b>#{h.no}</b>
              {Object.entries(h.kartu).map(([n, cs]: [string, any]) => (
                <span key={n} className="row-inline"><NameChip name={n} idx={names.indexOf(n)} />{cs.map((c: string) => <Card key={c} c={c} />)}</span>
              ))}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}

/** Informasi rahasia yang dibuka setelah match selesai (khusus game tertentu). */
export function Reveal({ gid, reveal, names }: { gid: string; reveal: any; names: string[] }) {
  if (!reveal || !Object.keys(reveal).length) return null;
  if (gid === 'poker') return <PokerReveal reveal={reveal} names={names} />;
  if (gid === 'kapal' && reveal.papan) {
    return (
      <div className="panel">
        <h3>Susunan armada</h3>
        <div className="seas">
          {Object.entries(reveal.papan).map(([n, rows]: [string, any]) => (
            <div key={n}>
              <h3 className="sub-h">{n}</h3>
              <Grid rows={rows} label={`Papan ${n}`} />
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (gid === 'kartu' && reveal.dek_akhir) {
    return (
      <div className="panel">
        <h3>Dek akhir</h3>
        {Object.entries(reveal.dek_akhir).map(([n, dek]: [string, any]) => (
          <p key={n}><NameChip name={n} idx={names.indexOf(n)} /> {dek.join(', ')}</p>
        ))}
      </div>
    );
  }
  return null;
}
