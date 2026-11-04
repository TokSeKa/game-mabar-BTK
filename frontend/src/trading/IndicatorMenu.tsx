import type { IndicatorConfig } from './indicators';

interface Props {
  cfg: IndicatorConfig;
  onChange: (c: IndicatorConfig) => void;
}

function Num({ id, value, onChange, min = 1, max = 500 }: { id: string; value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <input id={id} className="num" type="number" min={min} max={max} value={value}
      onChange={(e) => { const v = Number(e.target.value); if (v >= min && v <= max) onChange(v); }} />
  );
}

export function IndicatorMenu({ cfg, onChange }: Props) {
  const set = <K extends keyof IndicatorConfig>(k: K, v: Partial<IndicatorConfig[K]>) => onChange({ ...cfg, [k]: { ...cfg[k], ...v } });
  return (
    <details className="ind-menu">
      <summary className="btn small">Indikator</summary>
      <div className="ind-pop">
        <div className="ind-row">
          <label htmlFor="i-ma"><input id="i-ma" type="checkbox" checked={cfg.ma.on} onChange={(e) => set('ma', { on: e.target.checked })} /> Moving average</label>
          <select aria-label="Jenis MA" value={cfg.ma.type} onChange={(e) => set('ma', { type: e.target.value as 'sma' | 'ema' })}>
            <option value="ema">EMA</option><option value="sma">SMA</option>
          </select>
          <input aria-label="Periode MA" className="txt" value={cfg.ma.periods.join(',')}
            onChange={(e) => {
              const ps = e.target.value.split(',').map((x) => Number(x.trim())).filter((x) => x >= 1 && x <= 500).slice(0, 5);
              if (ps.length) set('ma', { periods: ps });
            }} />
        </div>
        <div className="ind-row">
          <label htmlFor="i-bb"><input id="i-bb" type="checkbox" checked={cfg.bb.on} onChange={(e) => set('bb', { on: e.target.checked })} /> Bollinger Bands</label>
          <Num id="i-bbn" value={cfg.bb.n} onChange={(n) => set('bb', { n })} />
          <Num id="i-bbm" value={cfg.bb.mult} min={1} max={5} onChange={(mult) => set('bb', { mult })} />
        </div>
        <div className="ind-row">
          <label htmlFor="i-vw"><input id="i-vw" type="checkbox" checked={cfg.vwap.on} onChange={(e) => set('vwap', { on: e.target.checked })} /> VWAP harian (intraday)</label>
        </div>
        <div className="ind-row">
          <label htmlFor="i-vol"><input id="i-vol" type="checkbox" checked={cfg.volume.on} onChange={(e) => set('volume', { on: e.target.checked })} /> Volume</label>
        </div>
        <div className="ind-row">
          <label htmlFor="i-rsi"><input id="i-rsi" type="checkbox" checked={cfg.rsi.on} onChange={(e) => set('rsi', { on: e.target.checked })} /> RSI</label>
          <Num id="i-rsin" value={cfg.rsi.n} onChange={(n) => set('rsi', { n })} />
        </div>
        <div className="ind-row">
          <label htmlFor="i-macd"><input id="i-macd" type="checkbox" checked={cfg.macd.on} onChange={(e) => set('macd', { on: e.target.checked })} /> MACD</label>
          <Num id="i-mf" value={cfg.macd.fast} onChange={(fast) => set('macd', { fast })} />
          <Num id="i-ms" value={cfg.macd.slow} onChange={(slow) => set('macd', { slow })} />
          <Num id="i-mg" value={cfg.macd.signal} onChange={(signal) => set('macd', { signal })} />
        </div>
        <div className="ind-row">
          <label htmlFor="i-st"><input id="i-st" type="checkbox" checked={cfg.stoch.on} onChange={(e) => set('stoch', { on: e.target.checked })} /> Stochastic</label>
          <Num id="i-stn" value={cfg.stoch.n} onChange={(n) => set('stoch', { n })} />
          <Num id="i-stk" value={cfg.stoch.k} onChange={(k) => set('stoch', { k })} />
          <Num id="i-std" value={cfg.stoch.d} onChange={(d) => set('stoch', { d })} />
        </div>
        <div className="ind-row">
          <label htmlFor="i-atr"><input id="i-atr" type="checkbox" checked={cfg.atr.on} onChange={(e) => set('atr', { on: e.target.checked })} /> ATR</label>
          <Num id="i-atrn" value={cfg.atr.n} onChange={(n) => set('atr', { n })} />
        </div>
      </div>
    </details>
  );
}
