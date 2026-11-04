import { useEffect, useState } from 'react';
import { getUser, pasarApi, setAuth, type User } from './api';
import { fmtNum, fmtPct } from './format';

export function useUser(): User | null {
  const [u, setU] = useState<User | null>(() => getUser());
  useEffect(() => {
    const f = () => setU(getUser());
    window.addEventListener('kilas-auth', f);
    return () => window.removeEventListener('kilas-auth', f);
  }, []);
  return u;
}

export function Akun({ toast }: { toast: (m: string, err?: boolean) => void }) {
  const user = useUser();
  const [mode, setMode] = useState<'masuk' | 'daftar'>('masuk');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [profil, setProfil] = useState<any>(null);

  useEffect(() => {
    if (user) pasarApi.saya().then((r) => setProfil(r.profil)).catch(() => setProfil(null));
  }, [user]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = mode === 'masuk' ? await pasarApi.masuk(username, password) : await pasarApi.daftar(username, password);
      setAuth(r.token, r.user);
      toast(mode === 'masuk' ? `Selamat datang, ${r.user.username}!` : 'Akun dibuat. Selamat main!');
      setPassword('');
    } catch (err) {
      toast((err as Error).message, true);
    } finally {
      setBusy(false);
    }
  };

  if (user) {
    return (
      <div className="panel akun">
        <h2>Halo, {user.username}</h2>
        {profil && (
          <div className="sum-grid">
            <div><span>Sesi selesai</span><b>{profil.sesi}</b></div>
            <div><span>Rata-rata return</span><b>{fmtPct(profil.rata_return)}</b></div>
            <div><span>Return terbaik</span><b>{fmtPct(profil.terbaik)}</b></div>
            <div><span>Mengalahkan beli-tahan</span><b>{fmtNum(profil.kalahkan_buy_hold, 0)}×</b></div>
            <div><span>Tantangan harian</span><b>{profil.harian_selesai}</b></div>
          </div>
        )}
        <button className="btn" type="button" onClick={async () => { await pasarApi.keluar().catch(() => null); setAuth(null, null); }}>Keluar dari akun</button>
      </div>
    );
  }
  return (
    <form className="panel akun" onSubmit={submit}>
      <div className="seg" role="group">
        <button type="button" aria-pressed={mode === 'masuk'} onClick={() => setMode('masuk')}>Masuk</button>
        <button type="button" aria-pressed={mode === 'daftar'} onClick={() => setMode('daftar')}>Daftar</button>
      </div>
      <p className="hint">Akun dipakai untuk papan peringkat tantangan harian dan menyimpan riwayat hasil. Tanpa akun pun semua mode tetap bisa dimainkan.</p>
      <label className="field" htmlFor="a-user">Username<input id="a-user" className="input" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></label>
      <label className="field" htmlFor="a-pass">Password<input id="a-pass" className="input" type="password" autoComplete={mode === 'masuk' ? 'current-password' : 'new-password'} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {mode === 'daftar' && <p className="hint">Username 3–20 karakter (huruf, angka, _). Password minimal 6 karakter.</p>}
      <button className="btn primary" type="submit" disabled={busy || !username || !password}>{mode === 'masuk' ? 'Masuk' : 'Buat akun'}</button>
    </form>
  );
}

const MODE: Record<string, string> = { solo: 'Latihan', harian: 'Harian', 'harian-latihan': 'Harian (latihan)', balapan: 'Balapan' };

export function Riwayat({ goAccount }: { goAccount: () => void }) {
  const user = useUser();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    if (user) pasarApi.riwayat().then(setData).catch((e) => setErr((e as Error).message));
  }, [user]);
  if (!user) {
    return (
      <div className="panel">
        <p>Masuk ke akun untuk menyimpan dan melihat riwayat hasil sesi.</p>
        <button className="btn primary" type="button" onClick={goAccount}>Masuk / daftar</button>
      </div>
    );
  }
  if (err) return <div className="err-box">{err}</div>;
  if (!data) return <div className="spinner" />;
  return (
    <div className="panel">
      <h3>Riwayat sesi</h3>
      {!data.hasil.length && <p className="hint">Belum ada sesi yang selesai.</p>}
      {data.hasil.length > 0 && (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Tanggal main</th><th>Mode</th><th>Aset</th><th>TF</th><th>Return</th><th>Beli-tahan</th><th>Transaksi</th><th>Max DD</th></tr></thead>
            <tbody>
              {data.hasil.map((r: any) => (
                <tr key={r.id}>
                  <td>{new Date(r.created * 1000).toLocaleString('id-ID')}</td>
                  <td>{MODE[r.mode] ?? r.mode}</td>
                  <td>{r.asset}</td>
                  <td>{r.chart_tf}</td>
                  <td className={r.return_pct >= 0 ? 'up' : 'down'}>{fmtPct(r.return_pct)}</td>
                  <td>{fmtPct(r.bh_pct)}</td>
                  <td>{r.stats?.n_trades ?? '–'}</td>
                  <td>{fmtPct(-(r.stats?.max_dd_pct ?? 0), 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
