import { lazy, Suspense } from 'react';
import type { RenderProps } from './common';

// Three.js cukup besar: diunduh hanya saat Robot Tarung dibuka
const Impl = lazy(() => import('../robot3d/RobotTarung'));

export function RRobotTarung(p: RenderProps) {
  return (
    <Suspense fallback={<div className="panel running-banner"><div className="spinner" /> Memuat arena 3D…</div>}>
      <Impl {...p} />
    </Suspense>
  );
}
