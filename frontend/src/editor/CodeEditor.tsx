import { useEffect, useRef } from 'react';
import { basicSetup } from 'codemirror';
import { EditorView, keymap } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { python, pythonLanguage } from '@codemirror/lang-python';
import { HighlightStyle, indentUnit, syntaxHighlighting } from '@codemirror/language';
import { indentWithTab } from '@codemirror/commands';
import { lintGutter, setDiagnostics, type Diagnostic } from '@codemirror/lint';
import type { CompletionContext, CompletionResult } from '@codemirror/autocomplete';
import { tags as t } from '@lezer/highlight';
import type { BotErrorInfo, LibDoc } from '../types';

const theme = EditorView.theme(
  {
    '&': { backgroundColor: 'var(--screen)', color: 'var(--fg)', fontSize: '14px' },
    '.cm-content': { fontFamily: 'var(--font-mono)', caretColor: 'var(--gold)' },
    '.cm-gutters': { backgroundColor: 'var(--panel)', color: 'var(--muted)', border: 'none' },
    '.cm-activeLine': { backgroundColor: '#ffffff08' },
    '.cm-activeLineGutter': { backgroundColor: '#ffffff10' },
    '&.cm-focused .cm-cursor': { borderLeftColor: 'var(--gold)' },
    '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: '#5a4fa060 !important' },
    '.cm-tooltip': { backgroundColor: 'var(--panel-2)', border: '1px solid var(--line)', color: 'var(--fg)' },
    '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: 'var(--line)', color: 'var(--fg)' },
    '.cm-completionDetail': { color: 'var(--gold)', fontStyle: 'normal', marginLeft: '8px' },
    '.cm-completionInfo': { maxWidth: '320px', fontFamily: 'var(--font-body)' },
    '.cm-diagnostic-error': { borderLeftColor: 'var(--bad)' },
    '.cm-lintRange-error': { backgroundImage: 'none', textDecoration: 'underline wavy var(--bad)' },
  },
  { dark: true },
);

const highlight = HighlightStyle.define([
  { tag: t.keyword, color: '#c29bff', fontWeight: '700' },
  { tag: [t.string, t.special(t.string)], color: '#6ee7a8' },
  { tag: t.number, color: '#ffb86b' },
  { tag: t.bool, color: '#ffb86b' },
  { tag: t.null, color: '#ffb86b' },
  { tag: t.comment, color: '#8a84b5', fontStyle: 'italic' },
  { tag: [t.function(t.variableName), t.function(t.propertyName)], color: '#7aa2ff' },
  { tag: t.definition(t.variableName), color: '#ffd166' },
  { tag: t.operator, color: '#f37aa5' },
  { tag: t.variableName, color: '#f3efff' },
  { tag: t.className, color: '#ffd166' },
]);

function libraryCompletion(docs: LibDoc[]) {
  const options = docs.map((d) => ({
    label: d.nama,
    type: d.jenis === 'konstanta' ? 'constant' : 'function',
    detail: d.tanda,
    info: d.ket,
    apply: d.jenis === 'fungsi' && d.tanda.endsWith('()') ? `${d.nama}()` : d.nama,
    boost: 5,
  }));
  return (ctx: CompletionContext): CompletionResult | null => {
    const word = ctx.matchBefore(/\w*/);
    if (!word || (word.from === word.to && !ctx.explicit)) return null;
    return { from: word.from, options, validFor: /^\w*$/ };
  };
}

interface Props {
  value: string;
  onChange: (code: string) => void;
  docs: LibDoc[];
  error: BotErrorInfo | null;
}

export function CodeEditor({ value, onChange, docs, error }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!host.current) return;
    const v = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          keymap.of([indentWithTab]),
          indentUnit.of('    '),
          python(),
          pythonLanguage.data.of({ autocomplete: libraryCompletion(docs) }),
          syntaxHighlighting(highlight),
          theme,
          lintGutter(),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) onChangeRef.current(u.state.doc.toString());
          }),
          EditorView.contentAttributes.of({ 'aria-label': 'Kode bot (Python)' }),
        ],
      }),
    });
    view.current = v;
    return () => {
      v.destroy();
      view.current = null;
    };
    // docs hanya dipakai saat editor dibuat
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs]);

  // nilai dari luar (misalnya memilih template)
  useEffect(() => {
    const v = view.current;
    if (v && v.state.doc.toString() !== value) {
      v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: value } });
    }
  }, [value]);

  useEffect(() => {
    const v = view.current;
    if (!v) return;
    const diags: Diagnostic[] = [];
    if (error) {
      const lineNo = Math.min(Math.max(error.baris ?? 1, 1), v.state.doc.lines);
      const line = v.state.doc.line(lineNo);
      diags.push({ from: line.from, to: Math.max(line.to, line.from), severity: 'error', message: error.pesan });
    }
    v.dispatch(setDiagnostics(v.state, diags));
  }, [error, value]);

  return <div className="cm-host" ref={host} />;
}
