const ID = 'id-ID';

export function fmtNum(v: number | null | undefined, dec = 2): string {
  if (v == null || !Number.isFinite(v)) return '–';
  if (Math.abs(v) < 0.5 * Math.pow(10, -dec)) v = 0; // hindari "-0,00"
  return v.toLocaleString(ID, { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

export function fmtPrice(v: number | null | undefined, dec: number): string {
  return fmtNum(v, dec);
}

export function fmtMoney(v: number | null | undefined, currency: string): string {
  if (v == null || !Number.isFinite(v)) return '–';
  if (currency === 'IDR') return 'Rp ' + Math.round(v).toLocaleString(ID);
  if (currency === 'USD') return '$' + fmtNum(v, 2);
  return fmtNum(v, 2) + ' ' + currency;
}

export function fmtPct(v: number | null | undefined, dec = 2, sign = true): string {
  if (v == null || !Number.isFinite(v)) return '–';
  const z = Math.abs(v) < 0.5 * Math.pow(10, -dec);
  return (sign && v > 0 && !z ? '+' : '') + fmtNum(v, dec) + '%';
}

export function fmtQty(v: number, step: number): string {
  if (step >= 1) return Math.round(v).toLocaleString(ID);
  const dec = Math.min(8, Math.max(0, Math.ceil(-Math.log10(step))));
  return v.toLocaleString(ID, { maximumFractionDigits: dec });
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
const pad = (n: number) => String(n).padStart(2, '0');

/** Waktu tampilan dari server sudah berupa "jam dinding" bursa, jadi dibaca sebagai UTC. */
export function makeTimeFmt(blind: boolean, startTime: number) {
  const day0 = Math.floor(startTime / 86400);
  const relDay = (t: number) => {
    const d = Math.floor(t / 86400) - day0;
    return d >= 0 ? `H+${d}` : `H${d}`;
  };
  const hm = (d: Date) => `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
  return {
    full(t: number): string {
      const d = new Date(t * 1000);
      if (blind) return `${relDay(t)} ${hm(d)}`;
      return `${pad(d.getUTCDate())} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} ${hm(d)}`;
    },
    tick(t: number, type: number): string {
      const d = new Date(t * 1000);
      // 0 tahun, 1 bulan, 2 tanggal, 3 jam, 4 jam:detik
      if (type >= 3) return hm(d);
      if (blind) return relDay(t);
      if (type === 0) return String(d.getUTCFullYear());
      if (type === 1) return `${MONTHS[d.getUTCMonth()]} ${String(d.getUTCFullYear()).slice(2)}`;
      return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
    },
  };
}

export function durText(sec: number): string {
  if (sec < 3600) return `${Math.round(sec / 60)} menit`;
  if (sec < 86400 * 2) return `${fmtNum(sec / 3600, 1)} jam`;
  return `${fmtNum(sec / 86400, 1)} hari`;
}
