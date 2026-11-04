import { useState } from 'react';
import { ICON, ROBOT } from '../replay/assets';
import { KEYS, load, save, type Session } from '../storage';

interface Props {
  initialCode: string;
  session: Session | null;
  onCreate: (name: string) => void;
  onJoin: (name: string, code: string) => void;
  onRejoin: (s: Session) => void;
  onPractice: () => void;
  onGuide: () => void;
}

export function Home({ initialCode, session, onCreate, onJoin, onRejoin, onPractice, onGuide }: Props) {
  const [name, setName] = useState<string>(() => load<string>(KEYS.name, ''));
  const [code, setCode] = useState(initialCode);
  const [err, setErr] = useState('');

  const cleanName = () => {
    const n = name.trim().replace(/\s+/g, ' ');
    if (!n) {
      setErr('Isi namamu dulu.');
      return null;
    }
    if (!/^[\p{L}\p{N}_ .-]{1,16}$/u.test(n)) {
      setErr('Nama maksimal 16 karakter: huruf, angka, spasi, titik, - atau _.');
      return null;
    }
    save(KEYS.name, n);
    setErr('');
    return n;
  };

  return (
    <div className="hero">
      <div>
        <h1>
          Adu <span className="w1">otak</span> bot <span className="w2">batu</span> gunting <span className="w3">kertas</span>
        </h1>
        <p>
          Buat bot dengan blok atau kode Python, lalu adu dengan bot teman-temanmu (sampai 8 pemain) di satu room. Tidak ada yang acak:
          setiap ronde bot memilih senjata berdasarkan riwayat permainan. Bot yang kalah kehilangan HP, bot yang menang menyerapnya.
        </p>
        <div className="mascots" aria-hidden="true" style={{ justifyContent: 'flex-start', marginTop: 12 }}>
          {['#f0a24a', '#3fd0c9', '#f37aa5'].map((c) => (
            <span key={c} className="mini-bot" style={{ ['--c' as string]: c, width: 54, height: 54 }} dangerouslySetInnerHTML={{ __html: ROBOT }} />
          ))}
        </div>
        <div className="rules">
          <div className="rule">
            <span dangerouslySetInnerHTML={{ __html: ICON.batu }} style={{ width: 28, height: 28, display: 'block' }} />
            <b>Sirkular</b>Batu &gt; gunting &gt; kertas &gt; batu. Kalau ketiganya keluar, semua golongan menang dan kalah sekaligus.
          </div>
          <div className="rule">
            <span dangerouslySetInnerHTML={{ __html: ICON.gunting }} style={{ width: 28, height: 28, display: 'block' }} />
            <b>HP berpindah</b>Tiap pemain yang dikalahkan kehilangan 100 HP. Pemenang membagi rata HP itu. Golongan kecil dapat bagian besar.
          </div>
          <div className="rule">
            <span dangerouslySetInnerHTML={{ __html: ICON.kertas }} style={{ width: 28, height: 28, display: 'block' }} />
            <b>Bertahan</b>HP 0 berarti gugur. Yang terakhir hidup, atau HP terbanyak saat ronde habis, menang.
          </div>
        </div>
      </div>

      <div className="panel join-card">
        <h2>Main bareng</h2>
        {session && (
          <button className="btn primary" type="button" onClick={() => onRejoin(session)}>
            Kembali ke room {session.code}
          </button>
        )}
        <label className="field" htmlFor="home-name">
          Namamu
          <input id="home-name" className="input" maxLength={16} value={name} placeholder="misalnya Budi" onChange={(e) => setName(e.target.value)} />
        </label>
        <button
          className="btn primary big"
          type="button"
          onClick={() => {
            const n = cleanName();
            if (n) onCreate(n);
          }}
        >
          Buat room baru
        </button>
        <div className="or">ATAU GABUNG</div>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            const n = cleanName();
            if (!n) return;
            if (!/^[A-Za-z0-9]{5}$/.test(code.trim())) {
              setErr('Kode room terdiri dari 5 huruf/angka.');
              return;
            }
            onJoin(n, code.trim().toUpperCase());
          }}
        >
          <input
            id="home-code"
            aria-label="Kode room"
            className="input code-input"
            style={{ flex: '1 1 140px' }}
            maxLength={5}
            placeholder="KODE"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
          />
          <button className="btn big" type="submit">Gabung</button>
        </form>
        {err && <div className="err-box">{err}</div>}
        <div className="row">
          <button className="btn" type="button" onClick={onPractice}>Latihan sendiri dulu</button>
          <button className="btn" type="button" onClick={onGuide}>Baca panduan</button>
        </div>
      </div>
    </div>
  );
}
