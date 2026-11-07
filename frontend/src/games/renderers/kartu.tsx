import { useState } from 'react';
import { fmt, seatColor } from '../hubApi';
import { TurnNote, type RenderProps } from './common';

interface CardDef {
  id: string;
  nama: string;
  biaya: number;
  ket: string;
  serang?: number;
  blok?: number;
  racun?: number;
  lemah?: number;
  serang_semua?: number;
  lemah_semua?: number;
}

const FASE_LABEL: Record<string, string> = { tarung: 'bertarung', hadiah: 'memilih hadiah', istirahat: 'istirahat', selesai: 'selesai' };

function needsTarget(c: CardDef | undefined): boolean {
  return !!c && !!(c.serang || c.racun || c.lemah);
}

function GameCard({ c, onClick, disabled, selected, small }: { c: CardDef | undefined; onClick?: () => void; disabled?: boolean; selected?: boolean; small?: boolean }) {
  if (!c) return null;
  const kind = (c as any).kutukan ? 'curse' : c.serang || c.serang_semua ? 'atk' : c.blok ? 'def' : 'skill';
  return (
    <button type="button" className={`gcard ${kind} ${selected ? 'sel' : ''} ${small ? 'small' : ''}`} onClick={onClick} disabled={disabled || !onClick}>
      <span className="gc-cost">{(c as any).kutukan ? '✕' : c.biaya}</span>
      <b>{c.nama}</b>
      <span className="gc-ket">{c.ket}</span>
    </button>
  );
}

function Bar({ hp, max, block }: { hp: number; max: number; block?: number }) {
  return (
    <div className="hpbar-s big">
      <i style={{ width: `${Math.max(0, (hp / Math.max(max, 1)) * 100)}%` }} />
      <span>{hp}/{max}{block ? ` · 🛡${block}` : ''}</span>
    </div>
  );
}

function Status({ o }: { o: { racun?: number; lemah?: number; kuat?: number } }) {
  return (
    <span className="statuses">
      {o.kuat ? <span title="kuat">💪{o.kuat}</span> : null}
      {o.racun ? <span title="racun">☠{o.racun}</span> : null}
      {o.lemah ? <span title="lemah">🌀{o.lemah}</span> : null}
    </span>
  );
}

export function RKartu({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const [sel, setSel] = useState<number | null>(null);
  const [buang, setBuang] = useState(false);
  const myName = me != null ? names[me] : null;
  const kat: Record<string, CardDef> = v.katalog ?? {};
  const race = Object.entries(v.pemain ?? {}) as [string, any][];
  race.sort((a, b) => b[1].skor - a[1].skor);
  const mine = myName && v.fase != null;
  const alive = (v.musuh ?? []).map((m: any, k: number) => (m.hidup ? k : -1)).filter((k: number) => k >= 0);

  const playCard = (i: number) => {
    const c = kat[v.tangan[i]];
    if (needsTarget(c) && alive.length > 1) {
      setSel(sel === i ? null : i);
      return;
    }
    setSel(null);
    act({ main: i, target: alive[0] ?? 0 });
  };

  return (
    <div className="game-grid">
      <div className="panel kartu">
        {!mine && <p className="hint">Setiap pemain menempuh {v.lantai_total} lantai sendiri-sendiri dengan musuh yang sama. Papan kanan menunjukkan kemajuan semua orang.</p>}
        {(v.berkah_teks || v.kesulitan > 0 || (v.niat_musuh && v.niat_musuh !== 'terlihat')) && (
          <p className="hint">
            {v.berkah_teks ? `✨ Berkah: ${v.berkah_teks}. ` : ''}
            {v.kesulitan > 0 ? `💀 Kesulitan ${v.kesulitan} (musuh +${v.kesulitan * 15}%). ` : ''}
            {v.niat_musuh === 'jenis' ? '🌫️ Niat musuh hanya terlihat jenisnya.' : v.niat_musuh === 'rahasia' ? '🌫️ Niat musuh rahasia.' : ''}
          </p>
        )}
        {mine && (
          <>
            <div className="row">
              <b>Lantai {v.lantai}/{v.lantai_total}</b>
              <span className="tag-mini">{FASE_LABEL[v.fase] ?? v.fase}</span>
              {v.fase === 'tarung' && <span className="tag-mini">giliran {v.giliran}</span>}
              <span className="spacer" />
              <span className="hint">skor {fmt(v.skor)}</span>
            </div>
            <div className="hero-row">
              <div className="me-box">
                <b>{myName}</b> <Status o={v} />
                <Bar hp={v.hp} max={v.hp_maks} block={v.blok} />
                {v.fase === 'tarung' && (
                  <div className="energy" aria-label={`energi ${v.energi}`}>
                    {Array.from({ length: Math.max(v.energi, 0) }, (_, k) => <i key={k} />)}
                    <span className="hint">energi {v.energi}</span>
                  </div>
                )}
              </div>
              {v.fase === 'tarung' && (
                <div className="enemies">
                  {v.musuh.map((m: any, k: number) => (
                    <button key={k} type="button" className={`enemy ${m.hidup ? '' : 'dead'} ${sel != null && m.hidup ? 'targetable' : ''}`}
                      disabled={!(canAct && sel != null && m.hidup)}
                      onClick={() => {
                        if (sel == null) return;
                        act({ main: sel, target: k });
                        setSel(null);
                      }}>
                      <b>{m.nama}</b> <Status o={m} />
                      <Bar hp={m.hp} max={m.hp_maks} block={m.blok} />
                      {m.hidup && <span className="intent">niat: {m.niat_teks || '–'}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
              {v.fase === 'tarung' ? (sel != null ? 'Pilih musuh yang diserang.' : 'Mainkan kartu, lalu akhiri giliran.') : ''}
            </TurnNote>
            {v.fase === 'tarung' && (
              <>
                <div className="hand">
                  {v.tangan.map((cid: string, i: number) => (
                    <GameCard key={`${cid}-${i}`} c={kat[cid]} selected={sel === i}
                      disabled={!canAct || (kat[cid]?.biaya ?? 9) > v.energi}
                      onClick={canAct ? () => playCard(i) : undefined} />
                  ))}
                </div>
                <div className="row">
                  <span className="hint">tumpukan ambil {v.tarik} · buang {v.buang.length} · hilang {v.habis.length}</span>
                  <span className="spacer" />
                  {canAct && <button type="button" className="btn primary" onClick={() => { setSel(null); act('akhiri'); }}>Akhiri giliran</button>}
                </div>
              </>
            )}
            {v.fase === 'hadiah' && (
              <>
                <p>Menang! Pilih satu kartu untuk dekmu:</p>
                <div className="hand">
                  {v.pilihan.map((cid: string, i: number) => <GameCard key={cid} c={kat[cid]} onClick={canAct ? () => act({ pilih: i }) : undefined} />)}
                </div>
                {canAct && <button type="button" className="btn" onClick={() => act('lewati')}>Lewati</button>}
              </>
            )}
            {v.fase === 'istirahat' && (
              <>
                <p>Tempat istirahat. Pulihkan HP atau buang satu kartu dari dek.</p>
                {canAct && (
                  <div className="row">
                    <button type="button" className="btn good" onClick={() => act('pulihkan')}>Pulihkan +{Math.floor((v.hp_maks * 35) / 100)} HP</button>
                    <button type="button" className={`btn ${buang ? 'primary' : ''}`} onClick={() => setBuang(!buang)}>Buang kartu…</button>
                  </div>
                )}
                {buang && canAct && (
                  <div className="hand">
                    {v.dek.map((cid: string, i: number) => <GameCard key={`${cid}-${i}`} c={kat[cid]} small onClick={() => { setBuang(false); act({ buang: i }); }} />)}
                  </div>
                )}
              </>
            )}
            {v.fase === 'selesai' && <p className="gold">Petualanganmu selesai dengan skor {fmt(v.skor)}.</p>}
            <ol className="hist small">
              {(v.log ?? []).slice().reverse().map((l: string, k: number) => <li key={k}>{l}</li>)}
            </ol>
          </>
        )}
      </div>
      <div className="panel">
        <h3>Balapan</h3>
        <ol className="board">
          {race.map(([nm, r], k) => (
            <li key={nm} className={`${nm === myName ? 'me' : ''} ${r.fase === 'selesai' && !r.menang ? 'out' : ''}`}>
              <span className="rk">{k + 1}</span>
              <span className="dot" style={{ ['--c' as string]: seatColor(names.indexOf(nm)) }} />
              <span className="nm">{nm} <small>{r.menang ? '🏆' : FASE_LABEL[r.fase]}</small></span>
              <span className="v">{fmt(r.skor)}<small>lantai {r.lantai} · ❤ {r.hp}</small></span>
            </li>
          ))}
        </ol>
        {!mine && race.map(([nm, r]) => (r.musuh?.length ? (
          <p key={nm} className="hint">{nm}: {r.musuh.map((m: any) => `${m[0]} ${m[1]}/${m[2]}`).join(', ')} {r.log?.length ? `— ${r.log[r.log.length - 1]}` : ''}</p>
        ) : null))}
      </div>
    </div>
  );
}
