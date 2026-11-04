import { useEffect, useRef } from 'react';
import type { MatchData } from '../types';
import { ReplayArena } from './ReplayArena';

interface Props {
  match: MatchData;
  myIndex?: number;
  autoplay?: boolean;
  startAtEnd?: boolean;
  onRound?: (ronde: number) => void;
}

export function Replay({ match, myIndex, autoplay = true, startAtEnd = false, onRound }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const cb = useRef(onRound);
  cb.current = onRound;
  useEffect(() => {
    if (!ref.current) return;
    const arena = new ReplayArena(ref.current, match, { myIndex, autoplay, startAtEnd, onRound: (r) => cb.current?.(r) });
    return () => arena.destroy();
  }, [match, myIndex, autoplay, startAtEnd]);
  return <div ref={ref} />;
}
