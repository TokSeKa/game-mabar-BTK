import { useEffect, useRef, useState } from 'react';
import { getUser, pasarApi, type SessionInfo } from './api';
import { PasarConn } from './conn';
import { fmtPct } from './format';
import { TradeScreen } from './TradeScreen';

interface Props {
  toast: (m: string, err?: boolean) => void;
  goAccount: () => void;
}

export function Daily({ toast, goAccount }: Props) {
  const [info, setInfo] = useState<any>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [conn, setConn] = useState<PasarConn | null>(null);
  const connRef = useRef<PasarConn | null>(null);
  const user = getUser();

  const refresh = () => pasarApi.harian().then(setInfo).catch((e) => toast((e as Error).message, true));
  useEffect(() => {
    refresh();
    return () => connRef.current?.close();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const begin = (hello: Record<string, any>) => {
    connRef.current?.close();
    let s: SessionInfo | null = null;
    const c = new PasarConn(() => (s?.id ? { type: 'solo_resume', id: s.id, secret: s.secret } : hello));
    c.on((m) => {
      if (m.type === 'session') {
        s = m as SessionInfo;
        setSession(s);
      } else if (m.type === 'summary') refresh();
      else if (m.type === 'error' && !s) {
        toast(m.message, true);
        c.close();
        setConn(null);
      }
    });
    connRef.current = c;
    setConn(c);
  };

  const exit = () => {
    connRef.current?.close();
    connRef.current = null;
    setConn(null);
    setSession(null);
    refresh();
  };

  if (session && conn) return <TradeScreen key={session.id} conn={conn} session={session} toast={toast} onExit={exit} />;
  if (!info) return <div className="spinner" />;
  const me = info.me;
  const done = me?.status === 'done';
  return (
    <div className="daily">
      <div className="panel daily-card">
        <span className="badge">{info.date}</span>
        <h2>Tantangan harian</h2>
        {info.error ? (
          <p className="err-box">{info.error}</p>
        ) : (
          <>
            <p>
              Semua pemain mendapat potongan chart yang sama hari ini: <b>{info.pasar}</b>, timeframe <b>{info.tf_label}</b>, {info.langkah} candle.
              Aset dan tanggalnya rahasia. Modal dan fee sama untuk semua. Skor = return akhir.
            </p>
            <p className="hint">
              Hanya percobaan pertama yang masuk papan peringkat. Percobaan berikutnya tetap bisa dimainkan sebagai latihan.
              Kalau keluar di tengah jalan, sesinya tetap berjalan dan bisa dilanjutkan dari sini.
            </p>
            {!user && <p className="hint">Kamu belum masuk akun, jadi hasilmu tidak masuk papan peringkat. <button className="btn small" type="button" onClick={goAccount}>Masuk / daftar</button></p>}
            {me?.resume ? (
              <button className="btn primary big" type="button" onClick={() => begin({ type: 'solo_resume', id: me.resume.id, secret: me.resume.secret })}>Lanjutkan tantangan</button>
            ) : (
              <button className="btn primary big" type="button" onClick={() => begin({ type: 'daily_start' })}>
                {done ? 'Main lagi (latihan, tidak dinilai)' : user ? 'Mulai tantangan (dinilai)' : 'Mulai (tidak dinilai)'}
              </button>
            )}
            {done && <p className="ok-box">Skormu hari ini {fmtPct(me.return_pct)} · peringkat #{me.rank}</p>}
          </>
        )}
      </div>
      <div className="panel">
        <h3>Papan peringkat hari ini</h3>
        {!info.board?.length && <p className="hint">Belum ada yang menyelesaikan tantangan hari ini. Jadilah yang pertama.</p>}
        <ol className="leader">
          {info.board?.map((b: any) => (
            <li key={b.rank} className={user && b.username === user.username ? 'me' : ''}>
              <span className="rk">{b.rank}</span>
              <span className="nm">{b.username}</span>
              <span className="hint">{b.n_trades ?? 0} transaksi · DD {fmtPct(-(b.max_dd_pct ?? 0), 1)}</span>
              <b className={b.return_pct >= 0 ? 'up' : 'down'}>{fmtPct(b.return_pct)}</b>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
