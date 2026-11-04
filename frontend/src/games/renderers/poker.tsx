import { fmt, seatColor } from '../hubApi';
import { NameChip, NumberPicker, ScoreBoard, TurnNote, idxOf, useResetState, type RenderProps } from './common';

const SUIT: Record<string, { s: string; red: boolean; label: string }> = {
  s: { s: '♠', red: false, label: 'sekop' },
  h: { s: '♥', red: true, label: 'hati' },
  d: { s: '♦', red: true, label: 'wajik' },
  c: { s: '♣', red: false, label: 'keriting' },
};
const RANK: Record<string, string> = { T: '10', J: 'J', Q: 'Q', K: 'K', A: 'A' };

export function Card({ c, big, hidden }: { c?: string | null; big?: boolean; hidden?: boolean }) {
  if (!c || hidden) return <span className={`pcard back ${big ? 'big' : ''}`} aria-label="kartu tertutup" />;
  const r = RANK[c[0]] ?? c[0];
  const su = SUIT[c[1]];
  return (
    <span className={`pcard ${su?.red ? 'red' : ''} ${big ? 'big' : ''}`} aria-label={`${r} ${su?.label ?? ''}`}>
      <b>{r}</b>
      <i>{su?.s}</i>
    </span>
  );
}

const STATUS_LABEL: Record<string, string> = { main: '', fold: 'fold', allin: 'ALL-IN', keluar: 'tersingkir' };
const AKSI_LABEL: Record<string, string> = { fold: 'fold', check: 'check', call: 'call', raise: 'raise', allin: 'all-in', 'small blind': 'SB', 'big blind': 'BB' };

export function RPoker({ view, names, me, canAct, acted, act, replay }: RenderProps) {
  const v = view;
  const myName = me != null ? names[me] : null;
  const valid: string[] = v.aksi_valid ?? [];
  const lo = v.min_raise_ke ?? 0;
  const hi = v.maks_raise_ke ?? 0;
  const [raiseTo, setRaiseTo] = useResetState<number>(lo, `${v.tangan}-${v.jalan}-${v.taruhan_tertinggi}-${canAct}`);
  const last = v.riwayat?.[v.riwayat.length - 1];
  const board: string[] = v.meja ?? [];
  const toCall = v.untuk_ikut ?? 0;
  const potAfterCall = (v.pot ?? 0) + toCall;
  const myBet = myName ? v.taruhan?.[myName] ?? 0 : 0;
  const quick = [
    { label: 'Min', to: lo },
    { label: '½ pot', to: Math.round(v.taruhan_tertinggi + potAfterCall / 2) },
    { label: 'Pot', to: Math.round(v.taruhan_tertinggi + potAfterCall) },
  ].filter((q) => q.to >= lo && q.to <= hi);
  return (
    <div className="game-grid">
      <div className="panel poker">
        <div className="row">
          <b>Tangan {v.tangan}/{v.tangan_maks}</b>
          <span className="tag-mini">blind {v.sb}/{v.bb}</span>
          <span className="tag-mini">{v.jalan}</span>
          <span className="spacer" />
          <span className="hint" title="sha256('poker|' + seed) — seed dibuka di akhir">hash dek {v.hash_dek}</span>
        </div>
        <div className="felt">
          <div className="board-cards">
            {[0, 1, 2, 3, 4].map((k) => <Card key={k} c={board[k]} big hidden={!board[k]} />)}
          </div>
          <div className="pot">Pot <b>{fmt(v.pot ?? 0)}</b></div>
        </div>
        <div className="poker-seats">
          {names.map((n, i) => {
            const st = v.status?.[n] ?? 'main';
            const turn = v.giliran === n;
            return (
              <div key={n} className={`pseat ${turn ? 'turn' : ''} ${st === 'fold' || st === 'keluar' ? 'out' : ''} ${n === myName ? 'me' : ''}`} style={{ ['--c' as string]: seatColor(i) }}>
                <div className="ps-top">
                  <b>{n}</b>
                  {v.dealer === n && <span className="dealer" title="dealer">D</span>}
                  {v.small_blind === n && <span className="tag-mini">SB</span>}
                  {v.big_blind === n && <span className="tag-mini">BB</span>}
                </div>
                <div className="ps-chip">{fmt(v.chip?.[n] ?? 0)} chip</div>
                <div className="ps-bet">{v.taruhan?.[n] ? `taruhan ${fmt(v.taruhan[n])}` : ' '}</div>
                {STATUS_LABEL[st] && <div className={`ps-st ${st}`}>{STATUS_LABEL[st]}</div>}
              </div>
            );
          })}
        </div>
        {myName && (v.kartu_saya?.length ?? 0) > 0 && (
          <div className="my-hand">
            <span className="hint">Kartumu</span>
            {v.kartu_saya.map((c: string) => <Card key={c} c={c} big />)}
          </div>
        )}
        <TurnNote canAct={canAct} acted={acted} replay={replay} me={me}>
          {toCall > 0 ? `Perlu ${fmt(toCall)} untuk call.` : 'Boleh check.'}
        </TurnNote>
        {canAct && (
          <div className="act-box">
            <div className="row">
              <button type="button" className="btn danger" onClick={() => act('fold')}>Fold</button>
              {valid.includes('check') && <button type="button" className="btn good" onClick={() => act('check')}>Check</button>}
              {valid.includes('call') && <button type="button" className="btn good" onClick={() => act('call')}>Call {fmt(toCall)}</button>}
              {valid.includes('allin') && <button type="button" className="btn" onClick={() => act('allin')}>All-in {fmt(hi - myBet)}</button>}
            </div>
            {valid.includes('raise') && lo < hi && (
              <div className="raise-box">
                <NumberPicker value={raiseTo} onChange={setRaiseTo} min={lo} max={hi} step={Math.max(1, v.sb)} label="Raise ke" />
                <div className="row">
                  {quick.map((q) => <button key={q.label} type="button" className="btn small" onClick={() => setRaiseTo(q.to)}>{q.label}</button>)}
                  <span className="spacer" />
                  <button type="button" className="btn primary" onClick={() => act({ aksi: 'raise', ke: raiseTo })}>Raise ke {fmt(raiseTo)}</button>
                </div>
              </div>
            )}
          </div>
        )}
        {(v.aksi_tangan?.length ?? 0) > 0 && (
          <div className="act-log">
            {v.aksi_tangan.slice(-14).map((a: any, k: number) => (
              <span key={k} className="chip" style={{ ['--c' as string]: seatColor(idxOf(names, a.pemain)) }}>
                {a.pemain} {AKSI_LABEL[a.aksi] ?? a.aksi}{a.jumlah ? ` ${fmt(a.jumlah)}` : ''}
              </span>
            ))}
          </div>
        )}
        {last && (
          <div className="last-hand">
            <h3 className="sub-h">Tangan #{last.no}</h3>
            <div className="row">
              <span className="hint">Meja</span>
              {last.meja.map((c: string) => <Card key={c} c={c} />)}
              <span className="spacer" />
              <span>pot {fmt(last.pot)}</span>
            </div>
            <div className="row">
              {Object.entries(last.menang).map(([n, x]) => <span key={n}><NameChip name={n} idx={idxOf(names, n)} /> +{fmt(Number(x))}</span>)}
            </div>
            {last.showdown && (
              <div className="showdown">
                {Object.entries(last.showdown).map(([n, sd]: [string, any]) => (
                  <div key={n} className="sd">
                    <NameChip name={n} idx={idxOf(names, n)} />
                    {sd.kartu.map((c: string) => <Card key={c} c={c} />)}
                    <span className="hint">{sd.tangan}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <ScoreBoard
        rows={names
          .map((n, i) => ({ name: n, idx: i, c: v.chip?.[n] ?? 0 }))
          .sort((a, b) => b.c - a.c)
          .map((r) => ({ name: r.name, idx: r.idx, value: fmt(r.c), dim: v.status?.[r.name] === 'keluar' }))}
        me={me}
        title="Chip"
      />
    </div>
  );
}
