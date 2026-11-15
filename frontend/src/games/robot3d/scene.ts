/**
 * Tampilan 3D Robot Tarung (Three.js). Fisika ada di server (2D, dilihat dari atas); di sini robot dirakit dari
 * komponennya dan digambar 3D: terlempar/terbalik sebagai animasi, percikan saat benturan, asap kalau rangka hampir habis.
 *
 * Koordinat server: x ke kanan, y ke bawah, sudut searah jarum jam. Di Three.js: x → x, y → z, tinggi = y.
 * Robot menghadap +X; rotasi Y = -sudut.
 */
import * as THREE from 'three';

export type Desain = {
  nama: string; sasis: 'kotak' | 'baji' | 'kubah'; penggerak: string; baterai: string;
  senjata: 'tidak' | 'spinner_h' | 'spinner_v' | 'flipper' | 'palu' | 'gergaji'; pembalik: boolean;
  armor: Record<'depan' | 'kanan' | 'belakang' | 'kiri', number>;
};

const METAL = 0x9aa3b4;
const DARK = 0x2a2c35;
const STEEL = 0xd7dbe4;

function mat(color: number | string, opts: Partial<THREE.MeshStandardMaterialParameters> = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.35, ...opts });
}

/** Bentuk baji: profil samping (x maju, y naik) diekstrusi selebar robot. */
function wedgeGeometry(len: number, hBack: number, hFront: number, width: number) {
  const sh = new THREE.Shape();
  sh.moveTo(-len / 2, 0);
  sh.lineTo(len / 2, 0);
  sh.lineTo(len / 2, hFront);
  sh.lineTo(-len / 2 + len * 0.28, hBack);
  sh.lineTo(-len / 2, hBack);
  sh.lineTo(-len / 2, 0);
  const g = new THREE.ExtrudeGeometry(sh, { depth: width, bevelEnabled: false });
  g.translate(0, 0, -width / 2);
  return g;
}

export const BODY_H = 0.3;

/**
 * Rakit robot 3D dari desain. Grup punya anak bernama: "badan" (untuk warna rusak), "senjata" (diputar/diayun),
 * "roda" (diputar sesuai laju). Titik asal = tengah robot di lantai.
 */
export function buildRobot(d: Desain, color: string): THREE.Group {
  const g = new THREE.Group();
  const bodyMat = mat(color, { roughness: 0.45, metalness: 0.25 });
  let body: THREE.Mesh;
  let top = BODY_H;
  if (d.sasis === 'baji') {
    body = new THREE.Mesh(wedgeGeometry(1.08, BODY_H + 0.02, 0.05, 0.84), bodyMat);
  } else if (d.sasis === 'kubah') {
    const geo = new THREE.SphereGeometry(0.6, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2);
    geo.scale(1, 0.62, 1);
    body = new THREE.Mesh(geo, bodyMat);
    top = 0.6 * 0.62;
  } else {
    body = new THREE.Mesh(new THREE.BoxGeometry(1.0, BODY_H, 0.82), bodyMat);
    body.position.y = BODY_H / 2;
  }
  body.name = 'badan';
  body.castShadow = true;
  g.add(body);
  if (d.sasis === 'kubah') {
    const skirt = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.08, 28), mat(DARK));
    skirt.position.y = 0.04;
    g.add(skirt);
  }

  // roda (4, di sisi kiri & kanan)
  const wheelGeo = new THREE.CylinderGeometry(0.15, 0.15, 0.11, 18);
  wheelGeo.rotateX(Math.PI / 2);
  const wheelMat = mat(0x16171d, { roughness: 0.9, metalness: 0 });
  const wheels = new THREE.Group();
  wheels.name = 'roda';
  const side = d.sasis === 'kubah' ? 0.47 : 0.47;
  for (const x of [-0.27, 0.25]) {
    for (const z of [-side, side]) {
      const w = new THREE.Mesh(wheelGeo, wheelMat);
      w.position.set(x, 0.15, z);
      w.castShadow = true;
      wheels.add(w);
    }
  }
  g.add(wheels);

  // armor: pelat di tiap sisi, makin tebal makin banyak tingkatnya
  const plate = mat(METAL, { roughness: 0.35, metalness: 0.75 });
  const A = d.armor;
  const thick = (n: number) => 0.015 + n * 0.011;
  if (d.sasis !== 'kubah') {
    if (A.depan > 0 && d.sasis !== 'baji') {
      const m = new THREE.Mesh(new THREE.BoxGeometry(thick(A.depan), BODY_H * 0.9, 0.8), plate);
      m.position.set(0.5 + thick(A.depan) / 2, BODY_H * 0.47, 0);
      g.add(m);
    }
    if (A.depan > 0 && d.sasis === 'baji') {
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.85, thick(A.depan), 0.82), plate);
      m.position.set(0.12, (BODY_H + 0.05) / 2 + 0.03, 0);
      m.rotation.z = -Math.atan2(BODY_H - 0.03, 0.78);
      g.add(m);
    }
    if (A.belakang > 0) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(thick(A.belakang), BODY_H * 0.9, 0.8), plate);
      m.position.set(-0.5 - thick(A.belakang) / 2 - (d.sasis === 'baji' ? 0.04 : 0), BODY_H * 0.47, 0);
      g.add(m);
    }
    for (const [k, sign] of [['kanan', 1], ['kiri', -1]] as const) {
      if (A[k] > 0) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(0.62, BODY_H * 0.55, thick(A[k])), plate);
        m.position.set(-0.02, BODY_H * 0.5, sign * (0.41 + 0.12 + thick(A[k]) / 2));
        g.add(m);
      }
    }
  } else {
    // kubah: cincin armor di pinggang, makin tebal makin tinggi
    const total = A.depan + A.kanan + A.belakang + A.kiri;
    if (total > 0) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.02 + total * 0.004, 8, 32), plate);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = 0.09;
      g.add(ring);
    }
  }

  // senjata
  const weapon = new THREE.Group();
  weapon.name = 'senjata';
  const steel = mat(STEEL, { roughness: 0.25, metalness: 0.9 });
  const darkSteel = mat(0x60646f, { roughness: 0.4, metalness: 0.8 });
  if (d.senjata === 'spinner_h') {
    weapon.position.set(0.05, top + 0.06, 0);
    const bar = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.05, 0.16), steel);
    const tipGeo = new THREE.BoxGeometry(0.12, 0.08, 0.2);
    for (const x of [-0.7, 0.7]) {
      const tip = new THREE.Mesh(tipGeo, darkSteel);
      tip.position.x = x;
      bar.add(tip);
    }
    bar.castShadow = true;
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.1, 16), darkSteel);
    weapon.add(bar, hub);
  } else if (d.senjata === 'spinner_v') {
    weapon.position.set(0.6, 0.17, 0);
    const drum = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.72, 20), steel);
    drum.rotation.x = Math.PI / 2;
    for (let k = 0; k < 2; k++) {
      const tooth = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.1, 0.72), darkSteel);
      const ang = k * Math.PI;
      tooth.position.set(Math.cos(ang) * 0.17, Math.sin(ang) * 0.17, 0);
      weapon.add(tooth);
    }
    drum.castShadow = true;
    weapon.add(drum);
    const arms = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.06, 0.06), darkSteel);
    arms.position.set(-0.12, 0, 0.38);
    const arms2 = arms.clone();
    arms2.position.z = -0.38;
    g.add(arms, arms2);
    arms.position.add(new THREE.Vector3(0.6, 0.17, 0));
    arms2.position.add(new THREE.Vector3(0.6, 0.17, 0));
  } else if (d.senjata === 'flipper') {
    weapon.position.set(-0.1, top + 0.02, 0);         // engsel di tengah atas
    const lid = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.03, 0.74), steel);
    lid.position.x = 0.36;
    lid.castShadow = true;
    weapon.add(lid);
  } else if (d.senjata === 'palu') {
    weapon.position.set(-0.3, top + 0.08, 0);         // poros di belakang
    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.06, 0.07), darkSteel);
    arm.position.x = 0.5;
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.2, 0.3), steel);
    head.position.set(1.0, -0.06, 0);
    head.castShadow = true;
    weapon.add(arm, head);
    weapon.rotation.z = Math.PI * 0.62;               // posisi siap: terangkat ke belakang
  } else if (d.senjata === 'gergaji') {
    weapon.position.set(0.58, 0.27, 0);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.02, 24), steel);
    disc.rotation.x = Math.PI / 2;
    const teeth = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.025, 4, 24), darkSteel);
    weapon.add(disc, teeth);
  } else {
    // penyeruduk: pelat ram di depan
    const ram = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.12, 0.9), mat(0xc9a227, { metalness: 0.7, roughness: 0.3 }));
    ram.position.set(d.sasis === 'baji' ? 0.56 : 0.56, 0.07, 0);
    g.add(ram);
  }
  g.add(weapon);

  if (d.pembalik) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.04, 0.1), darkSteel);
    arm.position.set(-0.42, top + 0.02, 0);
    g.add(arm);
  }
  return g;
}

/** Hapus geometri & material sebuah objek (supaya memori GPU tidak bocor). */
export function disposeObject(o: THREE.Object3D) {
  o.traverse((c) => {
    const m = c as THREE.Mesh;
    if (m.geometry) m.geometry.dispose();
    const mm = m.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(mm)) mm.forEach((x) => x.dispose());
    else mm?.dispose();
  });
}

function floorTexture(N: number) {
  const c = document.createElement('canvas');
  const px = 512;
  c.width = c.height = px;
  const g = c.getContext('2d')!;
  g.fillStyle = '#2b2e3a';
  g.fillRect(0, 0, px, px);
  const cell = px / N;
  g.strokeStyle = 'rgba(255,255,255,0.06)';
  g.lineWidth = 2;
  for (let i = 1; i < N; i++) {
    g.beginPath(); g.moveTo(i * cell, 0); g.lineTo(i * cell, px); g.stroke();
    g.beginPath(); g.moveTo(0, i * cell); g.lineTo(px, i * cell); g.stroke();
  }
  g.strokeStyle = 'rgba(255, 200, 60, 0.35)';
  g.lineWidth = 6;
  g.strokeRect(6, 6, px - 12, px - 12);
  g.fillStyle = 'rgba(255,255,255,0.05)';
  g.font = `bold ${Math.round(px / 9)}px sans-serif`;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText('ARENA MABAR', px / 2, px / 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

type Snap = { x: number; y: number; a: number };
type RobotObj = {
  group: THREE.Group; inner: THREE.Group; weapon: THREE.Object3D | null; wheels: THREE.Object3D | null;
  body: THREE.Mesh | null; baseColor: THREE.Color; key: string;
  prev: Snap; cur: Snap; spin: number; flipAnim: number; tumble: number; label: HTMLDivElement;
};

type Spark = { p: THREE.Vector3; v: THREE.Vector3; life: number };

export type ArenaOptions = { lowPower: boolean };

/** Satu arena 3D yang hidup selama komponen tampil. ``update(view)`` setiap ada data baru, render jalan sendiri. */
export class Arena3D {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
  root: HTMLElement;
  labels: HTMLDivElement;
  N = 14;
  robots = new Map<string, RobotObj>();
  hazards = new THREE.Group();
  hazardParts: { saw: THREE.Object3D[]; hammer: THREE.Object3D | null; hammerDown: number; hatch: THREE.Object3D | null; warn: THREE.Mesh | null } =
    { saw: [], hammer: null, hammerDown: -0.5, hatch: null, warn: null };
  arenaKey = '';
  view: any = null;
  recvAt = 0;
  tickMs = 50;
  raf = 0;
  last = performance.now();
  sparks: Spark[] = [];
  sparkPoints: THREE.Points;
  smoke: THREE.Mesh[] = [];
  /** arena = seluruh arena diam; dekat = membingkai robot yang masih hidup (gaya siaran TV); ikuti = di belakang robot ``follow`` */
  mode: 'arena' | 'dekat' | 'ikuti' = 'arena';
  follow: string | null = null;
  camLook = new THREE.Vector3(7, 0, 7);
  camInit = false;
  colors: (name: string) => string;
  lowPower: boolean;
  disposed = false;

  constructor(root: HTMLElement, colors: (name: string) => string, opts: ArenaOptions) {
    this.root = root;
    this.colors = colors;
    this.lowPower = opts.lowPower;
    this.renderer = new THREE.WebGLRenderer({ antialias: !opts.lowPower, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.lowPower ? 1.25 : 2));
    this.renderer.shadowMap.enabled = !opts.lowPower;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    root.appendChild(this.renderer.domElement);
    this.labels = document.createElement('div');
    this.labels.className = 'rt-labels';
    root.appendChild(this.labels);
    this.scene.background = new THREE.Color(0x12131c);
    this.scene.fog = new THREE.Fog(0x12131c, 30, 70);
    const hemi = new THREE.HemisphereLight(0xdfe6ff, 0x30303a, 0.9);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(6, 14, 4);
    sun.castShadow = !opts.lowPower;
    sun.shadow.mapSize.set(1024, 1024);
    this.scene.add(sun, sun.target);
    (this as any).sun = sun;
    this.scene.add(this.hazards);
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(300 * 3), 3));
    sg.setDrawRange(0, 0);
    this.sparkPoints = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffd36b, size: 0.09, transparent: true, opacity: 0.95 }));
    this.scene.add(this.sparkPoints);
    this.resize();
    this.loop = this.loop.bind(this);
    this.raf = requestAnimationFrame(this.loop);
  }

  resize() {
    const w = this.root.clientWidth || 600;
    const h = this.root.clientHeight || 400;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = `${w}px`;
    this.renderer.domElement.style.height = `${h}px`;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  buildArena(N: number, jebakan: any[], duri: boolean) {
    const key = `${N}|${JSON.stringify(jebakan)}|${duri}`;
    if (key === this.arenaKey) return;
    this.arenaKey = key;
    this.N = N;
    const old = this.scene.getObjectByName('arena');
    if (old) {
      this.scene.remove(old);
      disposeObject(old);
    }
    this.hazards.clear();
    this.hazardParts = { saw: [], hammer: null, hammerDown: -0.5, hatch: null, warn: null };
    const arena = new THREE.Group();
    arena.name = 'arena';
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(N, N), new THREE.MeshStandardMaterial({ map: floorTexture(N), roughness: 0.85, metalness: 0.1 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(N / 2, 0, N / 2);
    floor.receiveShadow = true;
    arena.add(floor);
    const wallMat = mat(0x3d4150, { metalness: 0.6, roughness: 0.4 });
    const glass = new THREE.MeshStandardMaterial({ color: 0x9fc7ff, transparent: true, opacity: 0.08, roughness: 0.1, metalness: 0 });
    const t = 0.3;
    for (const [x, z, w, d] of [[N / 2, -t / 2, N + 2 * t, t], [N / 2, N + t / 2, N + 2 * t, t], [-t / 2, N / 2, t, N], [N + t / 2, N / 2, t, N]]) {
      const wall = new THREE.Mesh(new THREE.BoxGeometry(w, 0.45, d), wallMat);
      wall.position.set(x, 0.225, z);
      wall.receiveShadow = true;
      const pane = new THREE.Mesh(new THREE.BoxGeometry(w, 1.6, d * 0.3), glass);
      pane.position.set(x, 1.25, z);
      arena.add(wall, pane);
    }
    if (duri) {
      const spike = new THREE.ConeGeometry(0.08, 0.25, 6);
      spike.rotateZ(-Math.PI / 2);
      const sm = mat(0xc9ccd6, { metalness: 0.9, roughness: 0.2 });
      for (let i = 0.5; i < N; i += 0.7) {
        for (const [x, z, rot] of [[i, 0.12, -Math.PI / 2], [i, N - 0.12, Math.PI / 2], [0.12, i, 0], [N - 0.12, i, Math.PI]] as const) {
          const m = new THREE.Mesh(spike, sm);
          m.position.set(x, 0.25, z);
          m.rotation.y = rot;
          arena.add(m);
        }
      }
    }
    this.scene.add(arena);
    for (const h of jebakan) {
      if (h.jenis === 'lubang') {
        const hole = new THREE.Mesh(new THREE.CircleGeometry(h.r, 32), new THREE.MeshBasicMaterial({ color: 0x050507 }));
        hole.rotation.x = -Math.PI / 2;
        hole.position.set(h.x, 0.005, h.y);
        const ring = new THREE.Mesh(new THREE.RingGeometry(h.r, h.r + 0.14, 32), new THREE.MeshBasicMaterial({ color: 0xf5c542 }));
        ring.rotation.x = -Math.PI / 2;
        ring.position.set(h.x, 0.006, h.y);
        const hatch = new THREE.Mesh(new THREE.CircleGeometry(h.r, 32), mat(0x55596a, { metalness: 0.7 }));
        hatch.rotation.x = -Math.PI / 2;
        hatch.position.set(h.x, 0.01, h.y);
        this.hazardParts.hatch = hatch;
        this.hazards.add(hole, ring, hatch);
      } else if (h.jenis === 'gergaji') {
        const saw = new THREE.Group();
        const disc = new THREE.Mesh(new THREE.CylinderGeometry(h.r, h.r, 0.04, 24), mat(0xe8ebf2, { metalness: 0.6, roughness: 0.25 }));
        const teeth = new THREE.Mesh(new THREE.TorusGeometry(h.r, 0.05, 4, 16), mat(0xff6b4a, { emissive: 0x882200 }));
        teeth.rotation.x = Math.PI / 2;
        const slot = new THREE.Mesh(new THREE.RingGeometry(h.r + 0.05, h.r + 0.16, 32), new THREE.MeshBasicMaterial({ color: 0x0a0a10 }));
        slot.rotation.x = -Math.PI / 2;
        slot.position.y = -0.035;
        saw.add(disc, teeth, slot);
        saw.position.set(h.x, 0.04, h.y);
        this.hazardParts.saw.push(saw);
        this.hazards.add(saw);
      } else if (h.jenis === 'palu') {
        const warn = new THREE.Mesh(new THREE.RingGeometry(h.r * 0.85, h.r, 32), new THREE.MeshBasicMaterial({ color: 0xff3b3b, transparent: true, opacity: 0.25 }));
        warn.rotation.x = -Math.PI / 2;
        warn.position.set(h.x, 0.01, h.y);
        this.hazardParts.warn = warn;
        // palu berporos di dinding belakang; posisi siap terangkat, saat memukul kepalanya menyentuh lantai di titik merah
        const L0 = N - h.y + 0.2;
        const pivot = new THREE.Group();
        pivot.position.set(h.x, 1.4, N + 0.2);
        const arm = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.16, L0), mat(0x3d4150));
        arm.position.z = -L0 / 2;
        const head = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.5), mat(0x8a1f1f, { metalness: 0.5 }));
        head.position.set(0, -0.1, -L0);
        head.castShadow = true;
        pivot.add(arm, head);
        pivot.rotation.x = 1.35;
        this.hazardParts.hammer = pivot;
        this.hazardParts.hammerDown = -Math.atan2(1.4 - 0.45, L0);
        this.hazards.add(warn, pivot);
      }
    }
  }

  /** Data baru dari server (atau frame replay). */
  update(view: any) {
    const now = performance.now();
    // lama interpolasi = jarak antar data yang sebenarnya (50 ms saat live, bisa lebih saat replay yang dirapatkan)
    if (this.recvAt) this.tickMs = Math.min(400, Math.max(30, now - this.recvAt));
    if (!view?.robot) {
      this.view = view;
      this.recvAt = now;
      return;
    }
    this.buildArena(view.arena, view.jebakan ?? [], !!view.dinding_duri);
    const seen = new Set<string>();
    for (const [name, r] of Object.entries<any>(view.robot)) {
      seen.add(name);
      const key = JSON.stringify(r.desain);
      let o = this.robots.get(name);
      if (o && o.key !== key) {
        this.scene.remove(o.group);
        disposeObject(o.group);
        o.label.remove();
        o = undefined;
      }
      const snap = { x: r.x, y: r.y, a: (r.a * Math.PI) / 180 };
      if (!o) {
        const inner = buildRobot(r.desain, this.colors(name));
        const group = new THREE.Group();
        group.add(inner);
        this.scene.add(group);
        const label = document.createElement('div');
        label.className = 'rt-label';
        this.labels.appendChild(label);
        const body = inner.getObjectByName('badan') as THREE.Mesh | null;
        o = {
          group, inner, weapon: inner.getObjectByName('senjata') ?? null, wheels: inner.getObjectByName('roda') ?? null, body,
          baseColor: (body?.material as THREE.MeshStandardMaterial | undefined)?.color.clone() ?? new THREE.Color(1, 1, 1),
          key, prev: snap, cur: snap, spin: 0, flipAnim: 0, tumble: 0, label,
        };
        this.robots.set(name, o);
      } else {
        const jump = Math.hypot(snap.x - o.cur.x, snap.y - o.cur.y) > 2.5;
        o.prev = jump ? snap : this.lerpSnap(o, Math.min(1, (now - this.recvAt) / this.tickMs));
        o.cur = snap;
      }
      o.label.textContent = `${name}${r.ko ? ' · KO' : ''}`;
      o.label.classList.toggle('ko', !!r.ko);
    }
    for (const [name, o] of this.robots) {
      if (!seen.has(name)) {
        this.scene.remove(o.group);
        disposeObject(o.group);
        o.label.remove();
        this.robots.delete(name);
      }
    }
    this.recvAt = now;
    this.view = view;
  }

  /** Kejadian dari server: percikan, lemparan, palu. */
  events(evs: any[]) {
    for (const e of evs) {
      if ((e.jenis === 'hantam' || e.jenis === 'benturan' || e.jenis === 'gerus') && e.x != null) {
        const n = e.jenis === 'gerus' ? 6 : Math.min(40, 8 + Math.round((e.kuat ?? 5) * 1.5));
        this.burst(e.x, e.y, n, e.jenis === 'gerus' ? 2 : 4);
      }
      if (e.jenis === 'palu_arena') this.burst(e.x, e.y, (e.kena ?? []).length ? 36 : 14, 5);
      if (e.jenis === 'ayun') {
        const o = this.robots.get(e.pemain);
        if (o) o.flipAnim = 1;
      }
      if (e.jenis === 'terbang') {
        const o = this.robots.get(e.pemain);
        if (o) o.tumble = e.balik ? 1 : 0.25;
      }
    }
  }

  burst(x: number, y: number, n: number, speed: number) {
    for (let i = 0; i < n && this.sparks.length < 300; i++) {
      const a = Math.random() * Math.PI * 2;
      const up = 1 + Math.random() * 3;
      this.sparks.push({
        p: new THREE.Vector3(x, 0.3, y),
        v: new THREE.Vector3(Math.cos(a) * speed * Math.random(), up, Math.sin(a) * speed * Math.random()),
        life: 0.3 + Math.random() * 0.35,
      });
    }
  }

  lerpSnap(o: RobotObj, t: number): Snap {
    let da = o.cur.a - o.prev.a;
    while (da > Math.PI) da -= 2 * Math.PI;
    while (da < -Math.PI) da += 2 * Math.PI;
    return { x: o.prev.x + (o.cur.x - o.prev.x) * t, y: o.prev.y + (o.cur.y - o.prev.y) * t, a: o.prev.a + da * t };
  }

  loop() {
    if (this.disposed) return;
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    const v = this.view;
    const N = this.N;
    const t = Math.min(1, (now - this.recvAt) / this.tickMs);
    // kamera
    const w = this.root.clientWidth || 1;
    const h = this.root.clientHeight || 1;
    const portrait = h > w;
    const followed = this.mode === 'ikuti' && this.follow ? this.robots.get(this.follow) : null;
    const posT = new THREE.Vector3();
    const lookT = new THREE.Vector3();
    if (followed && v?.robot?.[this.follow!]?.hidup) {
      const s = this.lerpSnap(followed, t);
      const back = 3.6;
      // kamera di belakang robot, agak tinggi; dijaga tetap dekat arena supaya dinding kaca tidak menghalangi
      posT.set(Math.min(N + 0.6, Math.max(-0.6, s.x - Math.cos(s.a) * back)), 4.6,
        Math.min(N + 0.6, Math.max(-0.6, s.y - Math.sin(s.a) * back)));
      lookT.set(s.x + Math.cos(s.a) * 1.8, 0, s.y + Math.sin(s.a) * 1.8);
    } else {
      // bingkai: seluruh arena, atau (mode dekat) kotak yang memuat semua robot hidup + ruang tepi
      let x0 = 0, x1 = N, z0 = 0, z1 = N;
      if (this.mode === 'dekat' && v?.robot) {
        const pts: Snap[] = [];
        for (const [name, o] of this.robots) if (v.robot[name]?.hidup) pts.push(this.lerpSnap(o, t));
        if (pts.length) {
          x0 = Math.min(...pts.map((p) => p.x)); x1 = Math.max(...pts.map((p) => p.x));
          z0 = Math.min(...pts.map((p) => p.y)); z1 = Math.max(...pts.map((p) => p.y));
          const minSpan = 7.5;
          const pad = 2.2;
          const grow = (a: number, b: number) => {
            const c = (a + b) / 2;
            const half = Math.max(minSpan, b - a + 2 * pad) / 2;
            const lo = Math.max(-0.4, Math.min(N + 0.4 - 2 * half, c - half));
            return [lo, Math.min(N + 0.4, lo + 2 * half)];
          };
          [x0, x1] = grow(x0, x1);
          [z0, z1] = grow(z0, z1);
        }
      }
      const cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
      const vf = (this.camera.fov * Math.PI) / 180;
      const hf = 2 * Math.atan(Math.tan(vf / 2) * this.camera.aspect);
      // jarak supaya lebar (x) dan kedalaman (z, dipendekkan oleh sudut pandang miring) sama-sama muat
      const dist = Math.max((x1 - x0) / 2 / Math.tan(hf / 2), ((z1 - z0) * 0.78) / 2 / Math.tan(vf / 2)) * 1.08 + 1.2;
      const dir = new THREE.Vector3(0, 0.8, 0.6).normalize();
      posT.set(cx, 0, cz).addScaledVector(dir, dist);
      lookT.set(cx, 0, cz + (portrait ? 0.1 : 0.25));
    }
    if (!this.camInit) {
      this.camera.position.copy(posT);
      this.camLook.copy(lookT);
      this.camInit = true;
    } else {
      const k = Math.min(1, dt * (this.mode === 'arena' && !followed ? 6 : 3));
      this.camera.position.lerp(posT, k);
      this.camLook.lerp(lookT, k);
    }
    this.camera.lookAt(this.camLook);
    // robot
    for (const [name, o] of this.robots) {
      const r = v?.robot?.[name];
      if (!r) continue;
      const s = this.lerpSnap(o, t);
      o.group.position.set(s.x, 0, s.y);
      o.group.rotation.y = -s.a;
      // terlempar: lengkung naik-turun; terbalik: putar 180° di sumbu maju
      const udara = r.udara_total > 0 ? 1 - Math.max(0, r.udara - (t * this.tickMs) / 1000) / r.udara_total : 0;
      const lift = r.udara > 0 ? Math.sin(Math.PI * Math.min(1, udara)) * (0.6 + r.udara_total) : 0;
      const flipped = r.terbalik ? Math.PI : 0;
      let roll = flipped;
      if (r.udara > 0 && o.tumble) roll = flipped + Math.PI * o.tumble * Math.min(1, udara) * (o.tumble >= 1 ? 1 : Math.sin(udara * Math.PI));
      if (r.membalik > 0) roll = flipped - Math.PI * (1 - r.membalik / 1.2);
      o.inner.rotation.x = roll;
      o.inner.position.y = lift + (Math.abs(Math.sin(roll)) > 0.01 || r.terbalik ? 0.32 * Math.abs(Math.sin(roll / 2)) : 0);
      if (r.angkat) o.inner.rotation.z = 0.12;
      else o.inner.rotation.z *= 0.8;
      if (r.ko === 'lubang') {
        o.group.position.y = -1.5;
      }
      // senjata
      const wpn = r.desain.senjata;
      if (o.weapon) {
        if (wpn === 'spinner_h') o.weapon.rotation.y += r.rpm * dt * 40;
        else if (wpn === 'spinner_v') o.weapon.rotation.z -= r.rpm * dt * 45;
        else if (wpn === 'gergaji') o.weapon.rotation.z -= (r.aktif && !r.terbalik ? 1 : 0) * dt * 40;
        else if (wpn === 'flipper') {
          o.flipAnim = Math.max(0, o.flipAnim - dt * 3.5);
          o.weapon.rotation.z = Math.sin(Math.min(1, o.flipAnim) * Math.PI) * 1.1;
        } else if (wpn === 'palu') {
          o.flipAnim = Math.max(0, o.flipAnim - dt * 2.8);
          const k = o.flipAnim > 0.6 ? (1 - o.flipAnim) / 0.4 : o.flipAnim / 0.6;
          o.weapon.rotation.z = Math.PI * 0.62 - (Math.PI * 0.62 + 0.15) * Math.max(0, Math.min(1, k));
        }
      }
      if (o.wheels) o.wheels.children.forEach((wh) => { wh.rotation.z -= r.v * dt * 6; });
      // warna menggelap sesuai kerusakan rangka; KO jadi abu-abu
      if (o.body) {
        const m = o.body.material as THREE.MeshStandardMaterial;
        const hp = Math.max(0, r.rangka / r.rangka_maks);
        m.color.copy(o.baseColor).multiplyScalar(r.ko ? 0.25 : 0.45 + 0.55 * hp);
      }
      if (!r.ko && r.rangka / r.rangka_maks < 0.35 && Math.random() < dt * 8) this.puff(s.x, s.y);
      // label nama di layar
      const p = new THREE.Vector3(s.x, 1.1 + lift, s.y).project(this.camera);
      o.label.style.transform = `translate(${((p.x + 1) / 2) * w}px, ${((1 - p.y) / 2) * h}px) translate(-50%, -100%)`;
      o.label.style.display = p.z < 1 && r.ko !== 'lubang' ? '' : 'none';
    }
    // jebakan
    for (const saw of this.hazardParts.saw) saw.rotation.y += dt * 14;
    if (this.hazardParts.hatch) this.hazardParts.hatch.visible = (v?.lubang_dalam ?? 0) > 0;
    if (this.hazardParts.hammer) {
      const left = v?.palu_dalam ?? 3;
      // 0 → 1 menjelang pukulan (detik terakhir), lalu kembali naik sesaat setelah memukul (palu_dalam baru diisi ulang ke 5)
      const k = left < 0.35 ? (0.35 - left) / 0.35 : left > 4.7 ? (left - 4.7) / 0.3 : 0;
      const down = this.hazardParts.hammerDown;
      this.hazardParts.hammer.rotation.x = 1.35 + (down - 1.35) * Math.min(1, Math.max(0, k));
      if (this.hazardParts.warn) (this.hazardParts.warn.material as THREE.MeshBasicMaterial).opacity = left < 1.5 ? 0.3 + 0.5 * Math.abs(Math.sin(now / 90)) : 0.18;
    }
    // percikan
    const pos = this.sparkPoints.geometry.getAttribute('position') as THREE.BufferAttribute;
    this.sparks = this.sparks.filter((sp) => (sp.life -= dt) > 0);
    this.sparks.forEach((sp, i) => {
      sp.v.y -= 9 * dt;
      sp.p.addScaledVector(sp.v, dt);
      if (sp.p.y < 0.02) { sp.p.y = 0.02; sp.v.y *= -0.3; }
      pos.setXYZ(i, sp.p.x, sp.p.y, sp.p.z);
    });
    pos.needsUpdate = true;
    this.sparkPoints.geometry.setDrawRange(0, this.sparks.length);
    // asap
    this.smoke = this.smoke.filter((m) => {
      m.position.y += dt * 0.6;
      m.scale.multiplyScalar(1 + dt * 0.8);
      const mm = m.material as THREE.MeshBasicMaterial;
      mm.opacity -= dt * 0.5;
      if (mm.opacity <= 0) {
        this.scene.remove(m);
        mm.dispose();
        return false;
      }
      return true;
    });
    this.renderer.render(this.scene, this.camera);
    this.raf = requestAnimationFrame(this.loop);
  }

  smokeGeo = new THREE.SphereGeometry(0.12, 6, 5);
  puff(x: number, y: number) {
    if (this.smoke.length > 60) return;
    const m = new THREE.Mesh(this.smokeGeo, new THREE.MeshBasicMaterial({ color: 0x555660, transparent: true, opacity: 0.55, depthWrite: false }));
    m.position.set(x + (Math.random() - 0.5) * 0.3, 0.45, y + (Math.random() - 0.5) * 0.3);
    this.scene.add(m);
    this.smoke.push(m);
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    disposeObject(this.scene);
    this.smokeGeo.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.labels.remove();
  }
}

/** Pratinjau kecil yang berputar (untuk garasi). */
export class Preview3D {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  robot: THREE.Group | null = null;
  raf = 0;
  root: HTMLElement;
  disposed = false;

  constructor(root: HTMLElement, lowPower: boolean) {
    this.root = root;
    this.renderer = new THREE.WebGLRenderer({ antialias: !lowPower, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    root.appendChild(this.renderer.domElement);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3a48, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.5);
    sun.position.set(3, 5, 2);
    this.scene.add(sun);
    const floor = new THREE.Mesh(new THREE.CircleGeometry(1.4, 40), new THREE.MeshStandardMaterial({ color: 0x2b2e3a, roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2;
    this.scene.add(floor);
    this.camera.position.set(2.2, 1.6, 2.4);
    this.camera.lookAt(0, 0.2, 0);
    this.resize();
    const loop = () => {
      if (this.disposed) return;
      if (this.robot) {
        this.robot.rotation.y += 0.008;
        const w = this.robot.getObjectByName('senjata');
        if (w && this.robot.userData.senjata === 'spinner_h') w.rotation.y += 0.25;
        if (w && (this.robot.userData.senjata === 'spinner_v' || this.robot.userData.senjata === 'gergaji')) w.rotation.z -= 0.25;
      }
      this.renderer.render(this.scene, this.camera);
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  resize() {
    const w = this.root.clientWidth || 300;
    const h = this.root.clientHeight || 220;
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = `${w}px`;
    this.renderer.domElement.style.height = `${h}px`;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  set(d: Desain, color: string) {
    if (this.robot) {
      this.scene.remove(this.robot);
      disposeObject(this.robot);
    }
    this.robot = buildRobot(d, color);
    this.robot.userData.senjata = d.senjata;
    this.robot.rotation.y = 0.6;
    this.scene.add(this.robot);
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    disposeObject(this.scene);
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}

/** Cek apakah browser bisa WebGL. */
export function webglOk(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}
