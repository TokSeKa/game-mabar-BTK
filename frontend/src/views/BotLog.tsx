import type { LogEntry } from '../types';

export function BotLog({ log }: { log: LogEntry[] }) {
  const errors = log.filter((e) => e.error).length;
  const prints = log.filter((e) => e.cetak?.length).length;
  const maxSteps = Math.max(0, ...log.map((e) => e.langkah ?? 0));
  return (
    <div className="panel">
      <h3>Log botku</h3>
      <p className="hint">
        Hanya kamu yang bisa melihat log ini. {errors ? `${errors} ronde error (otomatis BATU). ` : 'Tidak ada error. '}
        {prints ? `${prints} ronde punya catatan print(). ` : ''}Langkah terbanyak dalam satu ronde: {maxSteps}.
      </p>
      <ol className="botlog">
        {log.map((e, i) => (
          <li key={i} className={e.error ? 'err' : ''}>
            <span className="r">{e.ronde ? `R${e.ronde}` : 'awal'}</span>
            <span className={`w ${e.pilihan ?? ''}`}>{e.pilihan ? e.pilihan.toUpperCase() : '–'}</span>
            <span className="msg">
              {e.error && (
                <span className="e">
                  {e.error.baris ? `Baris ${e.error.baris}: ` : ''}
                  {e.error.pesan}
                </span>
              )}
              {e.catatan && <span className="n"> {e.catatan}</span>}
              {e.cetak?.map((c, j) => <code key={j}>{c}</code>)}
              {e.langkah != null && <span className="steps"> {e.langkah} langkah</span>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
