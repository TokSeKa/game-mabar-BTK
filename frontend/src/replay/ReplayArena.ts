/**
 * Replay match di arena melingkar. Diport dari prototipe visual (prototype/arena.html).
 * Kelas ini memegang DOM-nya sendiri; React hanya menyediakan elemen root.
 */
import type { MatchData, RoundData, Senjata } from '../types';
import { load, save } from '../storage';
import { BEATS, ICON, LABEL, ROBOT, SENJATA, escapeHtml } from './assets';

interface BotView {
  id: number;
  name: string;
  color: string;
  el: HTMLDivElement;
}

interface Rect { x: number; y: number; w: number; h: number }

let arenaSeq = 0;
const PLAY_SVG = '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M4 2v12l10-6z"/></svg>';
const PAUSE_SVG = '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 2h4v12H3zM9 2h4v12H9z"/></svg>';

export interface ReplayOptions {
  myIndex?: number;
  autoplay?: boolean;
  startAtEnd?: boolean;
  /** dipanggil setiap ronde yang ditampilkan berubah (nomor ronde, mulai 1) */
  onRound?: (ronde: number) => void;
}

export class ReplayArena {
  private root: HTMLElement;
  private match: MatchData;
  private rounds: RoundData[];
  private players: BotView[] = [];
  private hpStart: number;
  private hpShown: number[];
  private speed: number;
  private paused = false;
  private token = 0;
  private running = false;
  private cur = 0;
  private mode: 'circle' | 'boxes' = 'circle';
  private geo = { W: 0, H: 0, bs: 0, bw: 0, R: 0, cs: 0, boxes: {} as Record<Senjata, Rect> };
  private ro: ResizeObserver;
  private destroyed = false;
  private myIndex: number | undefined;
  private onRound: ((ronde: number) => void) | undefined;
  private timers = new Set<number>();
  private stage!: HTMLDivElement;
  private uid = `a${++arenaSeq}`; // id unik untuk marker SVG

  constructor(root: HTMLElement, match: MatchData, opts: ReplayOptions = {}) {
    this.root = root;
    this.match = match;
    this.rounds = match.rounds;
    this.myIndex = opts.myIndex;
    this.onRound = opts.onRound;
    this.hpStart = match.settings.hp_awal;
    this.hpShown = match.players.map(() => this.hpStart);
    this.speed = load<number>('sba-speed', 1);
    if (![1, 2, 4, 8].includes(this.speed)) this.speed = 1;
    this.buildDom();
    this.applySpeed();
    this.ro = new ResizeObserver(() => this.onResize());
    this.ro.observe(this.stage);
    this.measure();
    if (opts.startAtEnd) {
      this.paused = true;
      this.jumpTo(this.rounds.length, true);
    } else {
      this.jumpTo(0, true);
      if (opts.autoplay !== false) this.playFrom(0);
      else this.paused = true;
    }
    this.renderPlay();
  }

  destroy(): void {
    this.destroyed = true;
    this.token++;
    this.ro.disconnect();
    this.timers.forEach((t) => clearTimeout(t));
    this.root.innerHTML = '';
  }

  // ------------------------------------------------------------ DOM
  private q<T extends Element = HTMLElement>(sel: string): T {
    return this.root.querySelector(sel) as T;
  }

  private buildDom(): void {
    const s = this.match.settings;
    this.root.innerHTML = `
      <div class="replay">
        <section class="rp-main" aria-label="Arena">
          <div class="hud">
            <div class="hud-stats">
              <span>Ronde <b data-k="round">1</b> / <b>${s.ronde_maks}</b></span>
              <span>Hidup <b data-k="alive"></b></span>
              <span>Total HP <b data-k="total"></b></span>
              <span>Ingatan bot <b>${s.ingatan}</b> ronde</span>
              ${this.match.event && this.match.event.id !== 'normal'
                ? `<span class="ev-badge" title="${escapeHtml(this.match.event.ket)}">⚡ ${escapeHtml(this.match.event.nama)}${this.match.event.kejutan ? ' (kejutan)' : ''}</span>`
                : ''}
            </div>
            <ol class="phases">
              <li data-p="think">Berpikir</li><li data-p="reveal">Pilih</li><li data-p="gather">Kumpul</li><li data-p="resolve">Bagi poin</li>
            </ol>
          </div>
          <div class="stage">
            <svg class="arrows"></svg>
            ${SENJATA.map((w) => `<div class="box ${w}" data-box="${w}"><div class="box-head"></div><div class="box-foot"></div></div>`).join('')}
            <div class="center"><div class="lbl">Ronde</div><div class="num" data-k="cnum">1</div><div class="ph" data-k="cph">Bersiap…</div></div>
            <div class="bots"></div>
            <div class="end" hidden></div>
          </div>
          <div class="controls">
            <button class="btn primary" type="button" data-a="play"></button>
            <button class="btn" type="button" data-a="prev" aria-label="Ronde sebelumnya"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 2h2v12H3zM14 2v12L6 8z"/></svg>Mundur</button>
            <button class="btn" type="button" data-a="next" aria-label="Ronde berikutnya">Maju<svg viewBox="0 0 16 16" fill="currentColor"><path d="M11 2h2v12h-2zM2 2v12l8-6z"/></svg></button>
            <div class="seg" role="group" aria-label="Kecepatan">
              ${[1, 2, 4, 8].map((v) => `<button type="button" data-s="${v}" aria-pressed="${v === this.speed}">${v}×</button>`).join('')}
            </div>
            <button class="btn" type="button" data-a="end">Lewati ke akhir</button>
            <label class="scrub"><input type="range" min="1" max="${Math.max(1, this.rounds.length)}" value="1" aria-label="Pilih ronde"><output>R1</output></label>
          </div>
          <div class="ledger" aria-live="polite"></div>
        </section>
        <aside class="rp-side" aria-label="Klasemen">
          <div class="panel"><h3>Klasemen</h3><ol class="board"></ol></div>
          <div class="panel chart"><h3>HP per ronde</h3><div class="chart-box"></div></div>
        </aside>
      </div>`;
    this.stage = this.q<HTMLDivElement>('.stage');
    const botsEl = this.q('.bots');
    this.players = this.match.players.map((p) => {
      const el = document.createElement('div');
      el.className = 'bot' + (p.index === this.myIndex ? ' me' : '');
      el.style.setProperty('--c', p.color);
      el.innerHTML = `<div class="bubble"><i></i><i></i><i></i><b>!</b></div>
        <div class="card"><div class="card-inner"><div class="card-face card-back">?</div><div class="card-face card-front"></div></div></div>
        <div class="avatar">${ROBOT}<div class="float"></div></div>
        <div class="bname">${escapeHtml(p.name)}</div>
        <div class="hpbar"><div class="ghost"></div><div class="fill"></div></div>
        <div class="hpnum">${this.hpStart}</div>`;
      botsEl.appendChild(el);
      return { id: p.index, name: p.name, color: p.color, el };
    });
    this.resetLedger();

    this.q('[data-a="play"]').addEventListener('click', () => this.togglePlay());
    this.q('[data-a="prev"]').addEventListener('click', () => this.jumpTo(Math.max(0, this.cur - 1)));
    this.q('[data-a="next"]').addEventListener('click', () => this.jumpTo(this.cur + 1));
    this.q('[data-a="end"]').addEventListener('click', () => this.jumpTo(this.rounds.length));
    const scrub = this.q<HTMLInputElement>('.scrub input');
    scrub.addEventListener('input', () => {
      const v = +scrub.value;
      this.q('.scrub output').textContent = 'R' + (this.rounds[v - 1]?.r ?? v);
    });
    scrub.addEventListener('change', () => this.jumpTo(+scrub.value - 1));
    this.root.querySelectorAll<HTMLButtonElement>('.seg button').forEach((b) =>
      b.addEventListener('click', () => {
        this.speed = +b.dataset.s!;
        save('sba-speed', this.speed);
        this.applySpeed();
        this.root.querySelectorAll('.seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      }),
    );
  }

  private onResize(): void {
    if (this.destroyed) return;
    this.stage.classList.add('no-anim');
    this.measure();
    const R = this.rounds[this.cur];
    if (this.mode === 'boxes' && R) this.layoutBoxes(R);
    else this.layoutCircle();
    void this.stage.offsetWidth;
    this.stage.classList.remove('no-anim');
  }

  // ------------------------------------------------------------ geometri
  private measure(): void {
    const W = this.stage.clientWidth, H = this.stage.clientHeight;
    const m = Math.min(W, H);
    const bs = Math.max(32, Math.min(64, m * 0.095));
    const bw = bs * 1.75;
    const R = m * 0.37;
    this.geo = { W, H, bs, bw, R, cs: bs * 0.85, boxes: this.geo.boxes };
    this.stage.style.setProperty('--bs', bs + 'px');
    this.stage.style.setProperty('--bw', bw + 'px');
    this.stage.style.setProperty('--cs', bs * 0.85 + 'px');
    this.stage.style.setProperty('--ring', ((R * 2) / Math.max(W, 1)) * 100 + '%');
    const bwx = W * 0.39, bhx = H * 0.34;
    this.geo.boxes = {
      batu: { x: W * 0.5 - bwx / 2, y: H * 0.04, w: bwx, h: bhx },
      gunting: { x: W * 0.975 - bwx, y: H * 0.6, w: bwx, h: bhx },
      kertas: { x: W * 0.025, y: H * 0.6, w: bwx, h: bhx },
    };
    for (const w of SENJATA) {
      const b = this.geo.boxes[w];
      const el = this.q<HTMLDivElement>(`[data-box="${w}"]`);
      Object.assign(el.style, { left: b.x + 'px', top: b.y + 'px', width: b.w + 'px', height: b.h + 'px' });
    }
    this.drawArrows();
  }

  private place(p: BotView, cx: number, cy: number, k: number): void {
    const { bw, bs } = this.geo;
    p.el.style.transformOrigin = `${bw / 2}px ${bs / 2}px`;
    p.el.style.transform = `translate(${cx - bw / 2}px, ${cy - bs / 2}px) scale(${k})`;
  }

  private seat(i: number) {
    const n = this.players.length, a = -Math.PI / 2 + (2 * Math.PI * i) / n;
    return { x: this.geo.W / 2 + this.geo.R * Math.cos(a), y: this.geo.H / 2 + this.geo.R * Math.sin(a), a };
  }

  private layoutCircle(): void {
    this.mode = 'circle';
    this.stage.classList.remove('boxes');
    const { bs, bw, cs } = this.geo;
    for (const p of this.players) {
      const s = this.seat(p.id);
      this.place(p, s.x, s.y, 1);
      const dx = -Math.cos(s.a) * bs * 1.7, dy = -Math.sin(s.a) * bs * 1.7;
      const card = p.el.querySelector<HTMLElement>('.card')!;
      card.style.left = bw / 2 + dx - cs / 2 + 'px';
      card.style.top = bs / 2 + dy - cs / 2 + 'px';
      const bub = p.el.querySelector<HTMLElement>('.bubble')!;
      bub.style.left = bw / 2 + bs * 0.32 + 'px';
      bub.style.top = -bs * 0.42 + 'px';
    }
  }

  private layoutBoxes(R: RoundData): void {
    this.mode = 'boxes';
    this.stage.classList.add('boxes');
    const { bs, bw } = this.geo;
    for (const w of SENJATA) {
      const b = this.geo.boxes[w], ids = R.groups[w];
      const head = Math.max(30, b.h * 0.17), foot = 22;
      const n = ids.length, cols = Math.min(4, Math.max(1, n)), rows = n > 4 ? 2 : 1;
      // makin sedikit bot di kotak, makin besar ukurannya
      const slotW = b.w / Math.max(cols, 2), areaH = b.h - head - foot, slotH = areaH / rows;
      const k = Math.min(0.95, (slotW * 0.92) / bw, slotH / (bs * 2.05));
      const offX = (b.w - cols * slotW) / 2;
      const visH = bs * 1.95 * k; // tinggi avatar + nama + HP setelah diskala
      ids.forEach((id, j) => {
        const c = j % 4, r = Math.floor(j / 4);
        const top = b.y + head + slotH * r + (slotH - visH) / 2;
        this.place(this.players[id], b.x + offX + slotW * (c + 0.5), top + (bs * k) / 2, k);
      });
    }
    for (const p of this.players) {
      if (!R.alive.includes(p.id)) {
        const s = this.seat(p.id);
        this.place(p, s.x, s.y, 0.85);
      }
    }
  }

  private boxCenter(w: Senjata) {
    const b = this.geo.boxes[w];
    return { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  }

  private boxEdge(b: Rect, tx: number, ty: number) {
    const cx = b.x + b.w / 2, cy = b.y + b.h / 2, dx = tx - cx, dy = ty - cy;
    const t = Math.min((b.w / 2 + 6) / Math.abs(dx || 1e-6), (b.h / 2 + 6) / Math.abs(dy || 1e-6));
    return { x: cx + dx * t, y: cy + dy * t };
  }

  private drawArrows(): void {
    const { W, H } = this.geo;
    const svg = this.q<SVGSVGElement>('.arrows');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const mid = { x: W / 2, y: H * 0.56 };
    const uid = this.uid;
    let s = '<defs>';
    for (const w of SENJATA)
      s += `<marker id="m-${uid}-${w}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--${w})"/></marker>`;
    s += '</defs>';
    for (const w2 of SENJATA) {
      const L = BEATS[w2], a = this.boxCenter(w2), b = this.boxCenter(L);
      const p1 = this.boxEdge(this.geo.boxes[w2], b.x, b.y), p2 = this.boxEdge(this.geo.boxes[L], a.x, a.y);
      const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
      const ox = mx - mid.x, oy = my - mid.y, ol = Math.hypot(ox, oy) || 1;
      const bend = Math.min(W, H) * 0.06;
      const c = { x: mx + (ox / ol) * bend, y: my + (oy / ol) * bend };
      s += `<path class="a" data-ar="${w2}" d="M${p1.x} ${p1.y} Q${c.x} ${c.y} ${p2.x} ${p2.y}" stroke="var(--${w2})" marker-end="url(#m-${uid}-${w2})"/>`;
      const tx = mx * 0.5 + c.x * 0.5 + (ox / ol) * 24, ty = my * 0.5 + c.y * 0.5 + (oy / ol) * 24;
      s += `<text data-at="${w2}" x="${tx}" y="${ty}" text-anchor="middle" dominant-baseline="middle" fill="var(--${w2})"></text>`;
    }
    svg.innerHTML = s;
  }

  // ------------------------------------------------------------ render helper
  private setHp(p: BotView, hp: number, animate: boolean): void {
    const fill = p.el.querySelector<HTMLElement>('.fill')!, ghost = p.el.querySelector<HTMLElement>('.ghost')!;
    const pct = Math.max(0, Math.min(1, hp / this.hpStart)) * 100;
    const prev = this.hpShown[p.id];
    const instant = !animate || hp >= prev;
    if (instant) ghost.style.transition = 'none';
    fill.style.width = pct + '%';
    ghost.style.width = pct + '%';
    if (instant) {
      void ghost.offsetWidth;
      ghost.style.transition = '';
    }
    p.el.querySelector('.hpnum')!.textContent = String(hp);
    p.el.classList.toggle('over', hp > this.hpStart);
    this.hpShown[p.id] = hp;
  }

  private clearBotState(): void {
    for (const p of this.players) p.el.classList.remove('thinking', 'decided', 'carded', 'revealed', 'hit', 'gain');
  }

  private setPhase(ph: string, text?: string): void {
    this.root.querySelectorAll<HTMLElement>('.phases li').forEach((li) => li.classList.toggle('on', li.dataset.p === ph));
    if (text != null) this.q('[data-k="cph"]').textContent = text;
  }

  private setRoundUI(idx: number): void {
    const R = this.rounds[idx];
    const rn = R ? R.r : this.rounds.length ? this.rounds[this.rounds.length - 1].r : 1;
    this.q('[data-k="cnum"]').textContent = String(rn);
    this.q('[data-k="round"]').textContent = String(rn);
    this.q<HTMLInputElement>('.scrub input').value = String(Math.min(idx + 1, this.rounds.length));
    this.q('.scrub output').textContent = 'R' + rn;
    this.onRound?.(rn);
  }

  private updateHud(): void {
    this.q('[data-k="alive"]').textContent = this.hpShown.filter((h) => h > 0).length + '/' + this.players.length;
    this.q('[data-k="total"]').textContent = String(this.hpShown.reduce((a, b) => a + b, 0));
  }

  private chip(id: number): string {
    const p = this.players[id];
    return `<span class="chip" style="--c:${p.color}">${escapeHtml(p.name)}</span>`;
  }

  private renderLedger(R: RoundData): void {
    const loss = this.match.settings.hp_kalah;
    let h = `<h3>Pembagian poin · Ronde ${R.r}</h3>`;
    if (!R.pairs.length) {
      const only = SENJATA.filter((w) => R.counts[w]);
      h += `<div class="empty-note">Semua bot memilih <b>${LABEL[only[0]]}</b>. Seri, tidak ada HP yang berpindah.</div>`;
    } else {
      for (const pr of R.pairs) {
        const capped = pr.losers.filter((l) => l.amt < loss);
        h += `<div class="pair"><div class="vs">${ICON[pr.win]}<span class="gt">&gt;</span>${ICON[pr.lose]}</div>
          <div class="eq">${pr.losers.map((l) => this.chip(l.id)).join(' ')} <b class="m">−${loss}</b>${pr.losers.length > 1 ? ' per bot' : ''} = <b>${pr.pool} HP</b>
          → diserap ${pr.winners.map((i) => this.chip(i)).join(' ')} <b class="p">+${pr.share}</b>${pr.winners.length > 1 ? ' per bot' : ''}</div>
          ${capped.length ? `<div class="cap">${capped.map((l) => `${escapeHtml(this.players[l.id].name)} hanya punya ${l.amt} HP`).join(', ')}, jadi hanya itu yang terambil.</div>` : ''}
          ${pr.rem_ids.length ? `<div class="rem">Sisa ${pr.rem_ids.length} HP dibagi ke HP terendah: ${pr.rem_ids.map((i) => `+1 ${escapeHtml(this.players[i].name)}`).join(', ')}</div>` : ''}
        </div>`;
      }
    }
    h += `<div class="net">Hasil bersih: ${R.alive
      .map((i) => {
        const d = R.delta[i], p = this.players[i];
        return `<span class="chip" style="--c:${p.color}">${escapeHtml(p.name)} <b class="${d > 0 ? 'p' : d < 0 ? 'm' : 'z'}">${d > 0 ? '+' : ''}${d}</b></span>`;
      })
      .join(' ')}</div>`;
    if (R.elim.length) h += `<div class="rem">Gugur ronde ini: ${R.elim.map((i) => escapeHtml(this.players[i].name)).join(', ')}</div>`;
    this.q('.ledger').innerHTML = h;
  }

  private resetLedger(): void {
    this.q('.ledger').innerHTML =
      '<h3>Pembagian poin</h3><div class="empty-note">Rincian siapa kehilangan HP dan siapa menyerapnya muncul di sini setiap ronde.</div>';
  }

  private elimRound(id: number): number | null {
    return this.match.elim_round[String(id)] ?? null;
  }

  private rankOrder(hp: number[], uptoRound: number): number[] {
    const alive = (id: number) => {
      if (hp[id] > 0) return Infinity;
      const er = this.elimRound(id);
      return er != null && er <= uptoRound ? er : 0;
    };
    return this.players.map((p) => p.id).sort((a, b) => hp[b] - hp[a] || alive(b) - alive(a) || a - b);
  }

  private renderBoard(uptoRound: number): void {
    const order = this.rankOrder(this.hpShown, uptoRound);
    this.q('.board').innerHTML = order
      .map((id, k) => {
        const p = this.players[id], hp = this.hpShown[id], out = hp <= 0;
        return `<li class="${out ? 'out' : ''}${id === this.myIndex ? ' me' : ''}" style="--c:${p.color}"><span class="rk">${k + 1}</span><span class="dot"></span>
          <span class="nm">${escapeHtml(p.name)}${id === this.myIndex ? ' <small>(kamu)</small>' : ''}</span>
          <span class="v">${hp}${out ? `<small>gugur R${this.elimRound(id) ?? '?'}</small>` : ''}</span></li>`;
      })
      .join('');
  }

  private renderChart(upto: number): void {
    const Wc = 300, Hc = 150, pl = 34, pr = 8, pt = 8, pb = 18;
    const total = Math.max(1, this.rounds.length);
    let maxHp = this.hpStart;
    for (const R of this.rounds) for (const h of R.after) if (h > maxHp) maxHp = h;
    const step = maxHp > 40000 ? 20000 : maxHp > 8000 ? 5000 : maxHp > 4000 ? 2000 : maxHp > 2000 ? 1000 : maxHp > 1000 ? 500 : 250;
    const yMax = Math.ceil(maxHp / step) * step;
    const x = (r: number) => pl + ((Wc - pl - pr) * r) / total;
    const y = (h: number) => pt + (Hc - pt - pb) * (1 - h / yMax);
    let s = `<svg viewBox="0 0 ${Wc} ${Hc}" role="img" aria-label="Grafik HP tiap bot per ronde">`;
    for (const v of [0, yMax / 2, yMax])
      s += `<line class="ax" x1="${pl}" x2="${Wc - pr}" y1="${y(v)}" y2="${y(v)}"/><text class="tk" x="${pl - 4}" y="${y(v) + 3}" text-anchor="end">${v}</text>`;
    s += `<text class="tk" x="${pl}" y="${Hc - 4}">R0</text><text class="tk" x="${Wc - pr}" y="${Hc - 4}" text-anchor="end">R${total}</text>`;
    for (const p of this.players) {
      const pts: [number, number][] = [[0, this.hpStart]];
      for (let k = 0; k < upto; k++) {
        pts.push([this.rounds[k].r, this.rounds[k].after[p.id]]);
        if (this.rounds[k].after[p.id] <= 0) break;
      }
      s += `<polyline stroke="${p.color}" stroke-width="${p.id === this.myIndex ? 3 : 1.8}" points="${pts.map(([r, h]) => `${x(r).toFixed(1)},${y(h).toFixed(1)}`).join(' ')}"/>`;
    }
    this.q('.chart-box').innerHTML = s + '</svg>';
  }

  private renderBoxes(R: RoundData, resolved: boolean): void {
    for (const w of SENJATA) {
      const el = this.q<HTMLDivElement>(`[data-box="${w}"]`);
      el.querySelector('.box-head')!.innerHTML = `${ICON[w]}<span>${LABEL[w]}</span><span class="cnt">${R.counts[w]}</span>`;
      el.classList.toggle('empty', !R.counts[w]);
      el.classList.toggle('resolved', resolved);
      const gain = R.pairs.find((p) => p.win === w), lose = R.pairs.find((p) => p.lose === w);
      const wide = this.geo.boxes[w].w >= 230;
      el.querySelector('.box-foot')!.innerHTML =
        (gain ? `<span class="in">+${gain.pool}${wide ? ' dari ' + LABEL[gain.lose].toLowerCase() : ''}</span>` : '') +
        (lose ? `<span class="out">−${lose.pool}${wide ? ' ke ' + LABEL[lose.win].toLowerCase() : ''}</span>` : '');
    }
  }

  private setArrows(R: RoundData | null, labels: boolean): void {
    for (const w of SENJATA) {
      const pr = R?.pairs.find((p) => p.win === w);
      this.root.querySelector(`[data-ar="${w}"]`)?.classList.toggle('on', !!pr);
      const t = this.root.querySelector(`[data-at="${w}"]`);
      if (t) {
        t.classList.toggle('on', !!pr && labels);
        t.textContent = pr ? `${pr.pool} HP` : '';
      }
    }
  }

  private particles(R: RoundData, dur: number): void {
    for (const pr of R.pairs) {
      const from = this.boxCenter(pr.lose), to = this.boxCenter(pr.win);
      const n = Math.min(10, 3 + pr.losers.length * 2);
      for (let k = 0; k < n; k++) {
        const d = document.createElement('div');
        d.className = 'particle';
        d.style.color = `var(--${pr.lose})`;
        this.stage.appendChild(d);
        const jx = ((k * 37) % 21) - 10, jy = ((k * 53) % 21) - 10;
        const anim = d.animate(
          [
            { transform: `translate(${from.x + jx}px, ${from.y + jy}px) scale(.6)`, opacity: 0 },
            { opacity: 1, offset: 0.2 },
            { transform: `translate(${to.x - jx}px, ${to.y - jy}px) scale(1)`, opacity: 0 },
          ],
          { duration: dur, delay: k * dur * 0.06, easing: 'cubic-bezier(.5,0,.3,1)', fill: 'both' },
        );
        anim.onfinish = () => d.remove();
        const t = window.setTimeout(() => d.remove(), dur * 2 + 500);
        this.timers.add(t);
      }
    }
  }

  private pop(p: BotView, d: number): void {
    const f = p.el.querySelector<HTMLElement>('.float')!;
    f.textContent = (d > 0 ? '+' : '') + d;
    f.className = 'float ' + (d > 0 ? 'pos' : 'neg');
    void f.offsetWidth;
    f.classList.add('pop');
    p.el.classList.remove('hit', 'gain');
    void p.el.offsetWidth;
    p.el.classList.add(d > 0 ? 'gain' : 'hit');
  }

  // ------------------------------------------------------------ timeline
  private applySpeed(): void {
    const st = this.root.style;
    st.setProperty('--move', Math.round(850 / this.speed) + 'ms');
    st.setProperty('--flip', Math.round(600 / this.speed) + 'ms');
    st.setProperty('--hp', Math.round(900 / this.speed) + 'ms');
  }

  private wait(ms: number, tk: number): Promise<boolean> {
    return new Promise((res) => {
      let el = 0, last = performance.now();
      const f = (now: number) => {
        if (tk !== this.token) return res(false);
        if (!this.paused) el += (now - last) * this.speed;
        last = now;
        if (el >= ms) return res(true);
        requestAnimationFrame(f);
      };
      requestAnimationFrame(f);
    });
  }

  private thinkOrder(R: RoundData): number[] {
    return [...R.alive].sort((a, b) => ((a * 7 + R.r * 3) % 11) - ((b * 7 + R.r * 3) % 11) || a - b);
  }

  private async playRound(idx: number, tk: number): Promise<boolean> {
    const R = this.rounds[idx];
    this.cur = idx;
    this.setRoundUI(idx);
    this.clearBotState();
    this.q('.end').hidden = true;
    if (this.mode !== 'circle') this.layoutCircle();
    // 1. berpikir
    this.setPhase('think', 'Bot sedang berpikir…');
    for (const i of R.alive) {
      const el = this.players[i].el;
      el.classList.add('thinking');
      el.querySelector('.card-front')!.innerHTML = ICON[R.choices[i] ?? 'batu'];
    }
    if (!(await this.wait(450, tk))) return false;
    const order = this.thinkOrder(R), per = Math.max(110, 1300 / order.length);
    for (const i of order) {
      if (!(await this.wait(per, tk))) return false;
      this.players[i].el.classList.remove('thinking');
      this.players[i].el.classList.add('decided', 'carded');
    }
    if (!(await this.wait(350, tk))) return false;
    // 2. buka kartu
    this.setPhase('reveal', 'Buka kartu!');
    for (const i of R.alive) this.players[i].el.classList.remove('decided');
    for (const i of R.alive) {
      this.players[i].el.classList.add('revealed');
      if (!(await this.wait(45, tk))) return false;
    }
    if (!(await this.wait(1100, tk))) return false;
    // 3. kumpul
    this.setPhase('gather', '');
    this.renderBoxes(R, false);
    this.setArrows(null, false);
    this.layoutBoxes(R);
    if (!(await this.wait(950, tk))) return false;
    this.setArrows(R, false);
    if (!(await this.wait(650, tk))) return false;
    // 4. bagi poin
    this.setPhase('resolve', '');
    this.renderLedger(R);
    this.setArrows(R, true);
    this.renderBoxes(R, true);
    if (R.pairs.length) {
      this.particles(R, Math.round(800 / this.speed));
      if (!(await this.wait(650, tk))) return false;
      for (const i of R.alive) {
        if (R.delta[i]) this.pop(this.players[i], R.delta[i]);
        this.setHp(this.players[i], R.after[i], true);
      }
    } else {
      for (const i of R.alive) this.setHp(this.players[i], R.after[i], true);
    }
    this.renderBoard(R.r);
    this.renderChart(idx + 1);
    this.updateHud();
    if (!(await this.wait(R.pairs.length ? 1700 : 900, tk))) return false;
    if (R.elim.length) {
      for (const i of R.elim) this.players[i].el.classList.add('out');
      if (!(await this.wait(600, tk))) return false;
    }
    // 5. kembali ke lingkaran
    this.clearBotState();
    this.layoutCircle();
    this.setPhase('', 'Ronde berikutnya…');
    return this.wait(800, tk);
  }

  private async playFrom(idx: number): Promise<void> {
    const tk = ++this.token;
    this.running = true;
    this.renderPlay();
    for (let i = idx; i < this.rounds.length; i++) {
      const ok = await this.playRound(i, tk);
      if (!ok) {
        if (tk === this.token) this.running = false;
        return;
      }
    }
    if (tk !== this.token) return;
    this.running = false;
    this.cur = this.rounds.length;
    this.showEnd();
  }

  private jumpTo(idx: number, silent = false): void {
    if (this.destroyed) return;
    this.token++;
    this.running = false;
    idx = Math.max(0, Math.min(idx, this.rounds.length));
    this.cur = idx;
    this.stage.classList.add('no-anim');
    this.clearBotState();
    const hp = idx === 0 ? this.players.map(() => this.hpStart) : this.rounds[idx - 1].after;
    const upto = idx === 0 ? 0 : this.rounds[idx - 1].r;
    for (const p of this.players) {
      this.setHp(p, hp[p.id], false);
      p.el.classList.toggle('out', hp[p.id] <= 0);
    }
    this.layoutCircle();
    this.setArrows(null, false);
    this.setRoundUI(Math.min(idx, this.rounds.length - 1));
    this.setPhase('', idx >= this.rounds.length ? 'Match selesai' : idx === 0 ? 'Bersiap…' : 'Siap');
    if (idx > 0) this.renderLedger(this.rounds[idx - 1]);
    else this.resetLedger();
    this.renderBoard(upto);
    this.renderChart(idx);
    this.updateHud();
    this.q('.end').hidden = true;
    void this.stage.offsetWidth;
    this.stage.classList.remove('no-anim');
    if (idx >= this.rounds.length) {
      this.showEnd();
      return;
    }
    if (!silent && !this.paused) this.playFrom(idx);
    this.renderPlay();
  }

  private showEnd(): void {
    this.setPhase('', 'Match selesai');
    const m = this.match;
    const fin = m.final_hp;
    const order = m.ranking;
    const last = this.rounds[this.rounds.length - 1];
    const name = (i: number) => escapeHtml(this.players[i].name);
    let title: string, why: string;
    if (m.reason === 'last_standing') {
      title = `${name(m.winners[0])} juara!`;
      why = `Bertahan sendirian setelah ${last?.r ?? 0} ronde. Semua lawan kehabisan HP.`;
    } else if (m.winners.length > 1) {
      title = 'Seri!';
      why = `Batas ${m.settings.ronde_maks} ronde tercapai dan ${m.winners.map(name).join(' & ')} sama-sama punya ${fin[m.winners[0]]} HP.`;
    } else {
      title = `${name(order[0])} juara!`;
      why = `Batas ${last?.r ?? m.settings.ronde_maks} ronde tercapai. HP terbanyak yang menang.`;
    }
    if (this.myIndex != null) {
      const myRank = order.indexOf(this.myIndex) + 1;
      why += ` Botmu peringkat ${myRank} dari ${order.length}.`;
    }
    const slot = (rank: number, id: number | undefined) =>
      id == null
        ? ''
        : `<div class="pod p${rank}" style="--c:${this.players[id].color}"><div class="av">${ROBOT}</div><div class="nm">${name(id)}</div><div class="hp">${fin[id]} HP</div><div class="blk">${rank}</div></div>`;
    const end = this.q('.end');
    end.innerHTML = `<div class="end-card"><h2>${title}</h2><p>${why}</p>
      <div class="podium">${slot(2, order[1])}${slot(1, order[0])}${slot(3, order[2])}</div>
      <div class="end-actions"><button class="btn primary" type="button" data-a="again">Tonton lagi</button><button class="btn" type="button" data-a="close">Tutup</button></div></div>`;
    end.hidden = false;
    end.querySelector('[data-a="again"]')!.addEventListener('click', () => {
      this.paused = false;
      this.jumpTo(0);
    });
    end.querySelector('[data-a="close"]')!.addEventListener('click', () => {
      end.hidden = true;
    });
    this.renderPlay();
  }

  private togglePlay(): void {
    if (this.cur >= this.rounds.length && !this.running) {
      this.paused = false;
      this.jumpTo(0);
      return;
    }
    this.paused = !this.paused;
    if (!this.paused && !this.running) this.playFrom(this.cur);
    this.renderPlay();
  }

  private renderPlay(): void {
    const finished = this.cur >= this.rounds.length && !this.running;
    this.q('[data-a="play"]').innerHTML = finished ? `${PLAY_SVG}Ulang` : this.paused ? `${PLAY_SVG}Putar` : `${PAUSE_SVG}Jeda`;
  }
}
