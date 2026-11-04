/**
 * Blok-blok khusus Suit Bot Arena untuk mode visual (ala Scratch).
 * Setiap blok diterjemahkan ke kode Python yang sama dengan mode kode.
 */
import * as Blockly from 'blockly/core';
import 'blockly/blocks';
import * as Id from 'blockly/msg/id';
import { Order, pythonGenerator } from 'blockly/python';
import { iconDataUri } from '../replay/assets';

const C = {
  bot: '#c77a2a',
  senjata: '#b8457a',
  info: '#2f86b0',
  pemain: '#7357c2',
};

let defined = false;

export function defineBlocks(): void {
  if (defined) return;
  defined = true;
  Blockly.setLocale(Id as unknown as Record<string, string>);

  const weaponOptions = (['batu', 'gunting', 'kertas'] as const).map((w) => [
    { src: iconDataUri(w), width: 26, height: 26, alt: w.toUpperCase() },
    w.toUpperCase(),
  ]);
  const senjataIn = (name: string) => ({ type: 'input_value', name, check: ['Senjata', 'String'] });
  const pemainIn = (name: string) => ({ type: 'input_value', name, check: ['Pemain', 'String'] });

  Blockly.common.defineBlocksWithJsonArray([
    // ---------------- Bot
    {
      type: 'sba_pilih',
      message0: 'setiap ronde, bot memilih %1 %2',
      args0: [{ type: 'input_dummy' }, { type: 'input_statement', name: 'DO' }],
      colour: C.bot,
      tooltip: 'Blok utama. Isinya dijalankan setiap ronde sampai bertemu blok "pilih".',
    },
    {
      type: 'sba_return',
      message0: 'pilih %1',
      args0: [senjataIn('SENJATA')],
      previousStatement: null,
      colour: C.bot,
      tooltip: 'Pilih senjata untuk ronde ini. Blok di bawahnya tidak dijalankan lagi.',
    },
    {
      type: 'sba_print',
      message0: 'catat %1',
      args0: [{ type: 'input_value', name: 'X' }],
      previousStatement: null,
      nextStatement: null,
      colour: C.bot,
      tooltip: 'Tulis catatan ke log botmu. Hanya kamu yang bisa melihatnya.',
    },
    // ---------------- Senjata
    {
      type: 'sba_weapon',
      message0: '%1',
      args0: [{ type: 'field_dropdown', name: 'W', options: weaponOptions }],
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Batu mengalahkan gunting, gunting mengalahkan kertas, kertas mengalahkan batu.',
    },
    {
      type: 'sba_pengalah',
      message0: 'yang mengalahkan %1',
      args0: [senjataIn('X')],
      inputsInline: true,
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Senjata yang menang melawan senjata itu. Contoh: yang mengalahkan BATU = KERTAS.',
    },
    {
      type: 'sba_korban',
      message0: 'yang dikalahkan %1',
      args0: [senjataIn('X')],
      inputsInline: true,
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Senjata yang kalah melawan senjata itu. Contoh: yang dikalahkan BATU = GUNTING.',
    },
    { type: 'sba_terbanyak_lalu', message0: 'senjata terbanyak ronde lalu', output: 'Senjata', colour: C.senjata, tooltip: 'Senjata yang paling banyak dipilih di ronde sebelumnya.' },
    { type: 'sba_tersedikit_lalu', message0: 'senjata tersedikit ronde lalu', output: 'Senjata', colour: C.senjata, tooltip: 'Senjata yang paling sedikit dipilih di ronde sebelumnya.' },
    { type: 'sba_terbanyak_ingatan', message0: 'senjata terbanyak dalam ingatan', output: 'Senjata', colour: C.senjata, tooltip: 'Senjata yang paling sering dipilih selama ronde-ronde yang masih diingat.' },
    { type: 'sba_tersedikit_ingatan', message0: 'senjata tersedikit dalam ingatan', output: 'Senjata', colour: C.senjata, tooltip: 'Senjata yang paling jarang dipilih selama ronde-ronde yang masih diingat.' },
    {
      type: 'sba_pilihan_terakhir',
      message0: 'pilihan terakhir %1',
      args0: [pemainIn('P')],
      inputsInline: true,
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Senjata yang dipilih pemain itu di ronde lalu (BATU kalau belum ada).',
    },
    {
      type: 'sba_favorit',
      message0: 'senjata favorit %1',
      args0: [pemainIn('P')],
      inputsInline: true,
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Senjata yang paling sering dipilih pemain itu dalam ingatan.',
    },
    { type: 'sba_terbaik', message0: 'senjata paling untung kalau lawan mengulang', output: 'Senjata', colour: C.senjata, tooltip: 'Menghitung senjata terbaik untukmu kalau semua lawan memilih sama seperti ronde lalu.' },
    {
      type: 'sba_pola',
      message0: 'pola berulang %1 lalu %2 lalu %3',
      args0: [senjataIn('A'), senjataIn('B'), senjataIn('C')],
      inputsInline: true,
      output: 'Senjata',
      colour: C.senjata,
      tooltip: 'Ronde 1 pakai yang pertama, ronde 2 yang kedua, ronde 3 yang ketiga, lalu berulang.',
    },
    // ---------------- Info
    { type: 'sba_ronde', message0: 'ronde ke-', output: 'Number', colour: C.info, tooltip: 'Nomor ronde sekarang, mulai dari 1.' },
    { type: 'sba_ronde_maks', message0: 'batas ronde', output: 'Number', colour: C.info, tooltip: 'Jumlah ronde maksimal di match ini.' },
    { type: 'sba_hp_saya', message0: 'HP-ku', output: 'Number', colour: C.info, tooltip: 'HP botmu di awal ronde ini.' },
    { type: 'sba_hp_awal', message0: 'HP awal', output: 'Number', colour: C.info, tooltip: 'HP setiap pemain saat match dimulai.' },
    { type: 'sba_hp_kalah', message0: 'HP hilang saat kalah', output: 'Number', colour: C.info, tooltip: 'HP yang hilang setiap kali senjatamu dikalahkan.' },
    { type: 'sba_hp_of', message0: 'HP %1', args0: [pemainIn('P')], inputsInline: true, output: 'Number', colour: C.info, tooltip: 'HP pemain itu di awal ronde.' },
    { type: 'sba_perubahan', message0: 'perubahan HP %1 ronde lalu', args0: [pemainIn('P')], inputsInline: true, output: 'Number', colour: C.info, tooltip: 'Positif kalau untung, negatif kalau rugi.' },
    { type: 'sba_jumlah_lalu', message0: 'jumlah pemilih %1 ronde lalu', args0: [senjataIn('W')], inputsInline: true, output: 'Number', colour: C.info, tooltip: 'Berapa pemain yang memilih senjata itu di ronde lalu.' },
    { type: 'sba_jumlah_ingatan', message0: 'jumlah pemilih %1 dalam ingatan', args0: [senjataIn('W')], inputsInline: true, output: 'Number', colour: C.info, tooltip: 'Total pemilih senjata itu selama ronde-ronde yang masih diingat.' },
    { type: 'sba_jumlah_hidup', message0: 'jumlah pemain hidup', output: 'Number', colour: C.info, tooltip: 'Termasuk dirimu.' },
    // ---------------- Pemain
    { type: 'sba_aku', message0: 'aku', output: 'Pemain', colour: C.pemain, tooltip: 'Botmu sendiri.' },
    { type: 'sba_terkuat', message0: 'lawan terkuat', output: 'Pemain', colour: C.pemain, tooltip: 'Lawan dengan HP tertinggi.' },
    { type: 'sba_terlemah', message0: 'lawan terlemah', output: 'Pemain', colour: C.pemain, tooltip: 'Lawan dengan HP terendah.' },
    { type: 'sba_lawan', message0: 'daftar lawan', output: 'Array', colour: C.pemain, tooltip: 'Semua lawan yang masih hidup. Cocok dipakai di blok "untuk setiap".' },
  ]);

  const g = pythonGenerator;
  const v = (b: Blockly.Block, name: string, fallback: string, order = Order.NONE) => g.valueToCode(b, name, order) || fallback;
  const call = (code: string): [string, Order] => [code, Order.FUNCTION_CALL];

  g.forBlock['sba_pilih'] = (block) => {
    let body = g.statementToCode(block, 'DO');
    if (!body.trim()) body = g.INDENT + 'pass\n';
    return `def pilih():\n${body}${g.INDENT}return BATU  # cadangan kalau belum ada blok "pilih"\n`;
  };
  g.forBlock['sba_return'] = (block) => `return ${v(block, 'SENJATA', 'BATU')}\n`;
  g.forBlock['sba_print'] = (block) => `print(${v(block, 'X', "''")})\n`;
  g.forBlock['sba_weapon'] = (block) => [block.getFieldValue('W'), Order.ATOMIC];
  g.forBlock['sba_pengalah'] = (block) => call(`pengalah(${v(block, 'X', 'BATU')})`);
  g.forBlock['sba_korban'] = (block) => call(`korban(${v(block, 'X', 'BATU')})`);
  g.forBlock['sba_terbanyak_lalu'] = () => call('terbanyak(jumlah_terakhir())');
  g.forBlock['sba_tersedikit_lalu'] = () => call('tersedikit(jumlah_terakhir())');
  g.forBlock['sba_terbanyak_ingatan'] = () => call('terbanyak(total_jumlah(riwayat_jumlah()))');
  g.forBlock['sba_tersedikit_ingatan'] = () => call('tersedikit(total_jumlah(riwayat_jumlah()))');
  g.forBlock['sba_pilihan_terakhir'] = (block) => [`(pilihan_terakhir(${v(block, 'P', 'nama_saya()')}) or BATU)`, Order.ATOMIC];
  g.forBlock['sba_favorit'] = (block) => [`(terbanyak(riwayat_pilihan(${v(block, 'P', 'nama_saya()')})) or BATU)`, Order.ATOMIC];
  g.forBlock['sba_terbaik'] = () => call('senjata_terbaik()');
  g.forBlock['sba_pola'] = (block) =>
    [`[${v(block, 'A', 'BATU')}, ${v(block, 'B', 'KERTAS')}, ${v(block, 'C', 'GUNTING')}][(ronde() - 1) % 3]`, Order.MEMBER];
  g.forBlock['sba_ronde'] = () => call('ronde()');
  g.forBlock['sba_ronde_maks'] = () => call('ronde_maks()');
  g.forBlock['sba_hp_saya'] = () => call('hp_saya()');
  g.forBlock['sba_hp_awal'] = () => call('hp_awal()');
  g.forBlock['sba_hp_kalah'] = () => call('hp_kalah()');
  g.forBlock['sba_hp_of'] = (block) => call(`hp(${v(block, 'P', 'nama_saya()')})`);
  g.forBlock['sba_perubahan'] = (block) => call(`perubahan_terakhir(${v(block, 'P', 'nama_saya()')})`);
  g.forBlock['sba_jumlah_lalu'] = (block) => [`jumlah_terakhir()[${v(block, 'W', 'BATU')}]`, Order.MEMBER];
  g.forBlock['sba_jumlah_ingatan'] = (block) => [`total_jumlah(riwayat_jumlah())[${v(block, 'W', 'BATU')}]`, Order.MEMBER];
  g.forBlock['sba_jumlah_hidup'] = () => call('len(pemain_hidup())');
  g.forBlock['sba_aku'] = () => call('nama_saya()');
  g.forBlock['sba_terkuat'] = () => call('terkuat()');
  g.forBlock['sba_terlemah'] = () => call('terlemah()');
  g.forBlock['sba_lawan'] = () => call('lawan()');

  g.addReservedWords(
    'BATU,GUNTING,KERTAS,SENJATA,pilih,nama_saya,hp_saya,ronde,ronde_maks,hp_awal,hp_kalah,ingatan,' +
      'semua_pemain,pemain_hidup,lawan,hp,terkuat,terlemah,jumlah_terakhir,riwayat_jumlah,pilihan_terakhir,' +
      'riwayat_pilihan,perubahan_terakhir,riwayat_perubahan,riwayat,pengalah,korban,terbanyak,tersedikit,' +
      'hitung,total_jumlah,hitung_hasil,senjata_terbaik',
  );
}

export const THEME_NAME = 'suitbot';

export function getTheme(): Blockly.Theme {
  return Blockly.Theme.defineTheme(THEME_NAME, {
    name: THEME_NAME,
    base: Blockly.Themes.Classic,
    componentStyles: {
      workspaceBackgroundColour: '#1b1733',
      toolboxBackgroundColour: '#1e1a38',
      toolboxForegroundColour: '#f3efff',
      flyoutBackgroundColour: '#262046',
      flyoutForegroundColour: '#f3efff',
      flyoutOpacity: 0.97,
      scrollbarColour: '#3b3468',
      insertionMarkerColour: '#ffffff',
      insertionMarkerOpacity: 0.3,
      markerColour: '#ffd166',
      cursorColour: '#ffd166',
    },
    fontStyle: { family: 'Nunito, "Segoe UI", sans-serif', weight: '700', size: 12 },
  });
}

const W = (w: string) => ({ shadow: { type: 'sba_weapon', fields: { W: w } } });
const ME = { shadow: { type: 'sba_aku' } };

export const TOOLBOX = {
  kind: 'categoryToolbox',
  contents: [
    {
      kind: 'category', name: 'Bot', colour: C.bot,
      contents: [
        { kind: 'block', type: 'sba_return', inputs: { SENJATA: W('BATU') } },
        { kind: 'block', type: 'sba_print', inputs: { X: { shadow: { type: 'text', fields: { TEXT: 'halo' } } } } },
      ],
    },
    {
      kind: 'category', name: 'Senjata', colour: C.senjata,
      contents: [
        { kind: 'block', type: 'sba_weapon' },
        { kind: 'block', type: 'sba_pengalah', inputs: { X: W('BATU') } },
        { kind: 'block', type: 'sba_korban', inputs: { X: W('BATU') } },
        { kind: 'block', type: 'sba_terbanyak_lalu' },
        { kind: 'block', type: 'sba_tersedikit_lalu' },
        { kind: 'block', type: 'sba_terbanyak_ingatan' },
        { kind: 'block', type: 'sba_tersedikit_ingatan' },
        { kind: 'block', type: 'sba_pilihan_terakhir', inputs: { P: { shadow: { type: 'sba_terkuat' } } } },
        { kind: 'block', type: 'sba_favorit', inputs: { P: { shadow: { type: 'sba_terkuat' } } } },
        { kind: 'block', type: 'sba_pola', inputs: { A: W('BATU'), B: W('KERTAS'), C: W('GUNTING') } },
        { kind: 'block', type: 'sba_terbaik' },
      ],
    },
    {
      kind: 'category', name: 'Info', colour: C.info,
      contents: [
        { kind: 'block', type: 'sba_ronde' },
        { kind: 'block', type: 'sba_ronde_maks' },
        { kind: 'block', type: 'sba_hp_saya' },
        { kind: 'block', type: 'sba_hp_awal' },
        { kind: 'block', type: 'sba_hp_kalah' },
        { kind: 'block', type: 'sba_hp_of', inputs: { P: { shadow: { type: 'sba_terkuat' } } } },
        { kind: 'block', type: 'sba_perubahan', inputs: { P: ME } },
        { kind: 'block', type: 'sba_jumlah_lalu', inputs: { W: W('BATU') } },
        { kind: 'block', type: 'sba_jumlah_ingatan', inputs: { W: W('BATU') } },
        { kind: 'block', type: 'sba_jumlah_hidup' },
      ],
    },
    {
      kind: 'category', name: 'Pemain', colour: C.pemain,
      contents: [
        { kind: 'block', type: 'sba_aku' },
        { kind: 'block', type: 'sba_terkuat' },
        { kind: 'block', type: 'sba_terlemah' },
        { kind: 'block', type: 'sba_lawan' },
      ],
    },
    {
      kind: 'category', name: 'Logika', categorystyle: 'logic_category',
      contents: [
        { kind: 'block', type: 'controls_if' },
        { kind: 'block', type: 'controls_if', extraState: { hasElse: true } },
        { kind: 'block', type: 'logic_compare' },
        { kind: 'block', type: 'logic_operation' },
        { kind: 'block', type: 'logic_negate' },
        { kind: 'block', type: 'logic_boolean' },
      ],
    },
    {
      kind: 'category', name: 'Angka', categorystyle: 'math_category',
      contents: [
        { kind: 'block', type: 'math_number', fields: { NUM: 1 } },
        { kind: 'block', type: 'math_arithmetic' },
        { kind: 'block', type: 'math_modulo' },
      ],
    },
    {
      kind: 'category', name: 'Perulangan', categorystyle: 'loop_category',
      contents: [
        { kind: 'block', type: 'controls_repeat_ext', inputs: { TIMES: { shadow: { type: 'math_number', fields: { NUM: 3 } } } } },
        { kind: 'block', type: 'controls_forEach', inputs: { LIST: { block: { type: 'sba_lawan' } } } },
        { kind: 'block', type: 'controls_flow_statements' },
      ],
    },
    { kind: 'category', name: 'Variabel', categorystyle: 'variable_category', custom: 'VARIABLE' },
    {
      kind: 'category', name: 'Teks', categorystyle: 'text_category',
      contents: [{ kind: 'block', type: 'text' }, { kind: 'block', type: 'text_join' }],
    },
  ],
};

/** Contoh awal: ronde 1 pilih kertas, setelah itu lawan senjata terpopuler. */
export const STARTER_WORKSPACE = {
  blocks: {
    languageVersion: 0,
    blocks: [
      {
        type: 'sba_pilih', x: 24, y: 24, deletable: false,
        inputs: {
          DO: {
            block: {
              type: 'controls_if',
              inputs: {
                IF0: {
                  block: {
                    type: 'logic_compare', fields: { OP: 'EQ' },
                    inputs: { A: { block: { type: 'sba_ronde' } }, B: { block: { type: 'math_number', fields: { NUM: 1 } } } },
                  },
                },
                DO0: { block: { type: 'sba_return', inputs: { SENJATA: { block: { type: 'sba_weapon', fields: { W: 'KERTAS' } } } } } },
              },
              next: {
                block: {
                  type: 'sba_return',
                  inputs: { SENJATA: { block: { type: 'sba_pengalah', inputs: { X: { block: { type: 'sba_terbanyak_lalu' } } } } } },
                },
              },
            },
          },
        },
      },
    ],
  },
};

export { Blockly, pythonGenerator };
