import { useEffect, useRef } from 'react';
import { Blockly, STARTER_WORKSPACE, TOOLBOX, defineBlocks, getTheme, pythonGenerator } from './blocks';

interface Props {
  initial: unknown | null;
  onChange: (code: string, state: unknown) => void;
}

const MEDIA = import.meta.env.DEV ? '/node_modules/blockly/media/' : 'blockly-media/';

export function BlockEditor({ initial, onChange }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!host.current) return;
    defineBlocks();
    const ws = Blockly.inject(host.current, {
      toolbox: TOOLBOX,
      theme: getTheme(),
      renderer: 'zelos',
      media: MEDIA,
      sounds: false,
      trashcan: true,
      grid: { spacing: 28, length: 2, colour: '#2c2752', snap: true },
      zoom: { controls: true, wheel: false, startScale: 0.8, maxScale: 1.6, minScale: 0.4, scaleSpeed: 1.15 },
      move: { scrollbars: true, drag: true, wheel: true },
      maxInstances: { sba_pilih: 1 },
    });

    const load = (state: unknown) => Blockly.serialization.workspaces.load(state as object, ws);
    try {
      load(initial ?? STARTER_WORKSPACE);
    } catch {
      ws.clear();
      load(STARTER_WORKSPACE);
    }
    if (!ws.getBlocksByType('sba_pilih', false).length) {
      const root = ws.newBlock('sba_pilih');
      root.setDeletable(false);
      root.initSvg();
      root.render();
      root.moveBy(24, 24);
    }

    const emit = () => {
      const code = pythonGenerator.workspaceToCode(ws);
      onChangeRef.current(code, Blockly.serialization.workspaces.save(ws));
    };
    emit();
    ws.addChangeListener((e: Blockly.Events.Abstract) => {
      if (e.isUiEvent || ws.isDragging()) return;
      emit();
    });

    const ro = new ResizeObserver(() => Blockly.svgResize(ws));
    ro.observe(host.current);
    return () => {
      ro.disconnect();
      ws.dispose();
    };
    // workspace hanya dibuat sekali; perubahan initial dari luar ditangani dengan remount (key)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div className="blockly-host" ref={host} />;
}
