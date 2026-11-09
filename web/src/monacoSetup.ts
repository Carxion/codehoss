import { loader } from "@monaco-editor/react";

// Monaco is large (~3 MB), so it loads only when a lesson opens, keeping the login and
// course pages quick. Always the bundled copy: the app must work fully self-hosted.
let ready: Promise<void> | null = null;

export function loadMonaco(): Promise<void> {
  ready ??= Promise.all([
    import("monaco-editor"),
    import("monaco-editor/editor/editor.worker?worker"),
  ]).then(([monaco, worker]) => {
    const EditorWorker = worker.default;
    self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
    loader.config({ monaco });
  });
  return ready;
}
