import { useEffect, useRef } from 'react';
import type { MatchData } from '../types';
import { ReplayArena } from './ReplayArena';

interface Props {
  match: MatchData;
  myIndex?: number;
  autoplay?: boolean;
  startAtEnd?: boolean;
}

export function Replay({ match, myIndex, autoplay = true, startAtEnd = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const arena = new ReplayArena(ref.current, match, { myIndex, autoplay, startAtEnd });
    return () => arena.destroy();
  }, [match, myIndex, autoplay, startAtEnd]);
  return <div ref={ref} />;
}
