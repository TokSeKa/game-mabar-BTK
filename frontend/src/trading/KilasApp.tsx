import './trading.css';
import { useUser, Akun, Riwayat } from './Akun';
import { Backtest } from './Backtest';
import { Daily } from './Daily';
import { PanduanPasar } from './Panduan';
import { Race } from './Race';
import { Solo } from './Solo';

export type KilasTab = 'main' | 'harian' | 'balapan' | 'backtest' | 'riwayat' | 'akun' | 'panduan';

interface Props {
  tab: KilasTab;
  setTab: (t: KilasTab) => void;
  toast: (m: string, err?: boolean) => void;
  raceCode?: string;
}

const TABS: { id: KilasTab; label: string }[] = [
  { id: 'main', label: 'Main sendiri' },
  { id: 'harian', label: 'Tantangan harian' },
  { id: 'balapan', label: 'Balapan' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'riwayat', label: 'Riwayat' },
  { id: 'panduan', label: 'Cara main' },
];

export default function KilasApp({ tab, setTab, toast, raceCode }: Props) {
  const user = useUser();
  return (
    <div className="kilas">
      <div className="kilas-nav">
        <nav className="tabs" aria-label="Kilas Pasar">
          {TABS.map((t) => (
            <button key={t.id} type="button" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </nav>
        <button className="btn small" type="button" onClick={() => setTab('akun')}>{user ? `Akun: ${user.username}` : 'Masuk / daftar'}</button>
      </div>
      {tab === 'main' && <Solo toast={toast} />}
      {tab === 'harian' && <Daily toast={toast} goAccount={() => setTab('akun')} />}
      {tab === 'balapan' && <Race toast={toast} initialCode={raceCode} />}
      {tab === 'backtest' && <Backtest toast={toast} />}
      {tab === 'riwayat' && <Riwayat goAccount={() => setTab('akun')} />}
      {tab === 'akun' && <Akun toast={toast} />}
      {tab === 'panduan' && <PanduanPasar />}
    </div>
  );
}
