import type { GameMeta } from './hubApi';

export function defaultSettings(meta: GameMeta): Record<string, any> {
  return Object.fromEntries(meta.settings.map((s) => [s.id, s.default]));
}

/** Form pengaturan game (diambil dari meta.settings di server). */
export function SettingsForm({ meta, values, onChange, disabled }: {
  meta: GameMeta; values: Record<string, any>; onChange: (v: Record<string, any>) => void; disabled?: boolean;
}) {
  if (!meta.settings.length) return <p className="hint">Game ini tidak punya pengaturan.</p>;
  return (
    <div className="fields">
      {meta.settings.map((st) => {
        const val = values[st.id] ?? st.default;
        return (
          <label key={st.id} className="field" title={st.ket || undefined}>
            {st.label}
            {st.jenis === 'bool' ? (
              <select className="input" value={val ? '1' : '0'} disabled={disabled} onChange={(e) => onChange({ ...values, [st.id]: e.target.value === '1' })}>
                <option value="1">Ya</option>
                <option value="0">Tidak</option>
              </select>
            ) : st.jenis === 'pilihan' ? (
              <select className="input" value={String(val)} disabled={disabled} onChange={(e) => onChange({ ...values, [st.id]: e.target.value })}>
                {(st.pilihan ?? []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            ) : (
              <input type="number" value={val} disabled={disabled} min={st.min ?? undefined} max={st.max ?? undefined}
                step={st.jenis === 'float' ? 0.01 : 1}
                onChange={(e) => onChange({ ...values, [st.id]: e.target.value === '' ? '' : Number(e.target.value) })} />
            )}
          </label>
        );
      })}
    </div>
  );
}

/** Ringkasan pengaturan yang sedang dipakai (untuk non-host). */
export function SettingsSummary({ meta, values }: { meta: GameMeta; values: Record<string, any> }) {
  return (
    <ul className="settings-sum">
      {meta.settings.map((st) => {
        const v = values[st.id] ?? st.default;
        const shown = st.jenis === 'bool' ? (v ? 'ya' : 'tidak') : st.jenis === 'pilihan' ? (st.pilihan?.find((p) => p[0] === v)?.[1] ?? v) : String(v);
        return <li key={st.id}><span>{st.label}</span><b>{shown}</b></li>;
      })}
    </ul>
  );
}
