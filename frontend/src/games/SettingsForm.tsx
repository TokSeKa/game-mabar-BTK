import { useState } from 'react';
import { load, save } from '../storage';
import type { GameMeta, PresetMeta, SettingMeta } from './hubApi';

const GRUP: [SettingMeta['grup'], string, string][] = [
  ['dasar', 'Dasar', ''],
  ['informasi', '🌫️ Informasi (kabut)', 'Apa yang boleh dilihat pemain. Semua rahasia dibuka di layar hasil & replay.'],
  ['aturan', '⚖️ Aturan', 'Variasi aturan yang mengubah strategi.'],
  ['kejutan', '🎲 Kejutan', 'Kejadian acak dari seed match (sama untuk semua pemain, bot tetap tanpa keacakan).'],
];

export function defaultSettings(meta: GameMeta): Record<string, any> {
  return Object.fromEntries(meta.settings.map((s) => [s.id, s.default]));
}

/** Setting tampil kalau semua syarat `jika` terpenuhi (misalnya batas faktor hanya untuk mode faktor acak). */
export function settingVisible(st: SettingMeta, values: Record<string, any>): boolean {
  if (!st.jika) return true;
  return Object.entries(st.jika).every(([k, want]) => {
    const v = values[k];
    return Array.isArray(want) ? want.includes(v) : v === want;
  });
}

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

/** Nilai setelah preset diterapkan: pengaturan "dasar" (jumlah ronde, modal, dst.) tidak disentuh. */
function applyPreset(meta: GameMeta, values: Record<string, any>, nilai: Record<string, any>): Record<string, any> {
  const next = { ...values };
  for (const st of meta.settings) if (st.grup !== 'dasar') next[st.id] = st.default;
  for (const [k, v] of Object.entries(nilai)) if (meta.settings.some((st) => st.id === k)) next[k] = v;
  return next;
}

function presetMatches(meta: GameMeta, values: Record<string, any>, nilai: Record<string, any>): boolean {
  const target = applyPreset(meta, values, nilai);
  return meta.settings.every((st) => st.grup === 'dasar' || same(values[st.id] ?? st.default, target[st.id]));
}

interface SavedPreset {
  nama: string;
  nilai: Record<string, any>;
}
const savedKey = (gid: string) => `mabar-preset-${gid}`;

export function matchingPreset(meta: GameMeta, values: Record<string, any>): string | null {
  const all: { nama: string; nilai: Record<string, any> }[] = [...(meta.presets ?? []), ...load<SavedPreset[]>(savedKey(meta.id), [])];
  return all.find((p) => presetMatches(meta, values, p.nilai))?.nama ?? null;
}

function shown(st: SettingMeta, v: any): string {
  if (st.jenis === 'bool') return v ? 'ya' : 'tidak';
  if (st.jenis === 'pilihan') return st.pilihan?.find((p) => p[0] === v)?.[1] ?? String(v);
  if (typeof v === 'number') return v.toLocaleString('id-ID', { maximumFractionDigits: 3 });
  return String(v);
}

function Field({ st, val, disabled, onChange }: { st: SettingMeta; val: any; disabled?: boolean; onChange: (v: any) => void }) {
  return (
    <label className={`field set-field ${val !== st.default ? 'changed' : ''}`}>
      <span>{st.label}</span>
      {st.jenis === 'bool' ? (
        <select className="input" value={val ? '1' : '0'} disabled={disabled} onChange={(e) => onChange(e.target.value === '1')}>
          <option value="1">Ya</option>
          <option value="0">Tidak</option>
        </select>
      ) : st.jenis === 'pilihan' ? (
        <select className="input" value={String(val)} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {(st.pilihan ?? []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      ) : (
        <input type="number" value={val} disabled={disabled} min={st.min ?? undefined} max={st.max ?? undefined}
          step={st.jenis === 'float' ? 0.01 : 1}
          onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))} />
      )}
      {st.ket && <small className="hint">{st.ket}</small>}
    </label>
  );
}

/** Form pengaturan game: preset cepat, lalu pengaturan dikelompokkan (Dasar, Informasi, Aturan, Kejutan). */
export function SettingsForm({ meta, values, onChange, disabled }: {
  meta: GameMeta; values: Record<string, any>; onChange: (v: Record<string, any>) => void; disabled?: boolean;
}) {
  const [saved, setSaved] = useState<SavedPreset[]>(() => load<SavedPreset[]>(savedKey(meta.id), []));
  if (!meta.settings.length) return <p className="hint">Game ini tidak punya pengaturan.</p>;
  const presets: PresetMeta[] = meta.presets ?? [];
  const persist = (list: SavedPreset[]) => {
    setSaved(list);
    save(savedKey(meta.id), list);
  };
  const saveCurrent = () => {
    const nama = window.prompt('Nama preset (disimpan di browser ini):', 'Aturanku')?.trim();
    if (!nama) return;
    const nilai = Object.fromEntries(meta.settings.filter((st) => st.grup !== 'dasar').map((st) => [st.id, values[st.id] ?? st.default]));
    persist([...saved.filter((p) => p.nama !== nama), { nama: nama.slice(0, 24), nilai }]);
  };
  const hasGroup = (g: string) => meta.settings.some((st) => st.grup === g);
  return (
    <div className="settings-form">
      {(presets.length > 1 || saved.length > 0) && (
        <div className="preset-row" role="group" aria-label="Preset aturan">
          {presets.map((p) => (
            <button key={p.id} type="button" className={`btn small ${presetMatches(meta, values, p.nilai) ? 'primary' : ''}`} disabled={disabled}
              title={p.ket} onClick={() => onChange(applyPreset(meta, values, p.nilai))}>{p.nama}</button>
          ))}
          {saved.map((p) => (
            <span key={p.nama} className="saved-preset">
              <button type="button" className={`btn small ${presetMatches(meta, values, p.nilai) ? 'primary' : ''}`} disabled={disabled}
                onClick={() => onChange(applyPreset(meta, values, p.nilai))}>⭐ {p.nama}</button>
              {!disabled && (
                <button type="button" className="btn small" aria-label={`Hapus preset ${p.nama}`}
                  onClick={() => persist(saved.filter((x) => x.nama !== p.nama))}>✕</button>
              )}
            </span>
          ))}
          {!disabled && <button type="button" className="btn small" onClick={saveCurrent}>💾 Simpan preset</button>}
        </div>
      )}
      {presets.find((p) => presetMatches(meta, values, p.nilai))?.ket && (
        <p className="hint">{presets.find((p) => presetMatches(meta, values, p.nilai))?.ket}</p>
      )}
      {GRUP.filter(([g]) => hasGroup(g)).map(([g, label, ket]) => {
        const list = meta.settings.filter((st) => st.grup === g && settingVisible(st, values));
        const changed = list.filter((st) => !same(values[st.id] ?? st.default, st.default)).length;
        return (
          <details key={g} className="set-group" open={g === 'dasar' || changed > 0}>
            <summary>{label}{changed > 0 && <span className="tag-mini host">{changed} diubah</span>}</summary>
            {ket && <p className="hint">{ket}</p>}
            <div className="fields">
              {list.map((st) => (
                <Field key={st.id} st={st} val={values[st.id] ?? st.default} disabled={disabled}
                  onChange={(v) => onChange({ ...values, [st.id]: v })} />
              ))}
            </div>
          </details>
        );
      })}
    </div>
  );
}

/** Ringkasan pengaturan yang sedang dipakai (untuk non-host). */
export function SettingsSummary({ meta, values }: { meta: GameMeta; values: Record<string, any> }) {
  return (
    <>
      <ActiveRules meta={meta} values={values} open />
      <ul className="settings-sum">
        {meta.settings.filter((st) => st.grup === 'dasar' && settingVisible(st, values)).map((st) => (
          <li key={st.id}><span>{st.label}</span><b>{shown(st, values[st.id] ?? st.default)}</b></li>
        ))}
      </ul>
    </>
  );
}

/** Chip aturan yang berbeda dari bawaan (informasi/aturan/kejutan), supaya semua pemain tahu variasi yang dipakai. */
export function ActiveRules({ meta, values, open }: { meta: GameMeta; values: Record<string, any>; open?: boolean }) {
  const list = meta.settings.filter((st) => st.grup !== 'dasar' && settingVisible(st, values) && !same(values[st.id] ?? st.default, st.default));
  const preset = matchingPreset(meta, values);
  if (!list.length) return <p className="hint active-rules-none">Aturan standar{preset && preset !== 'Standar' ? ` (${preset})` : ''}.</p>;
  const icon = (g: string) => (g === 'informasi' ? '🌫️' : g === 'kejutan' ? '🎲' : '⚖️');
  return (
    <details className="active-rules" open={open}>
      <summary>Aturan aktif{preset ? `: ${preset}` : ''} ({list.length})</summary>
      <ul>
        {list.map((st) => (
          <li key={st.id}>
            <span className="rule-chip">{icon(st.grup)} {st.label}: <b>{shown(st, values[st.id])}</b></span>
            {st.ket && <small className="hint">{st.ket}</small>}
          </li>
        ))}
      </ul>
    </details>
  );
}
