import { CaptureUpdateAction, Excalidraw } from "@excalidraw/excalidraw";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import "@excalidraw/excalidraw/index.css";
import { useCallback, useEffect, useRef, useState } from "react";
import { useResolvedTheme } from "../theme/useResolvedTheme";
import BoardControls from "./BoardControls";
import { tagLearnerElements } from "./originTag";

// Self-host Excalidraw's fonts (committed under public/excalidraw-assets) so drawing text never
// calls a third-party CDN. Must be set before the library first loads a font.
(window as unknown as { EXCALIDRAW_ASSET_PATH?: string }).EXCALIDRAW_ASSET_PATH = "/excalidraw-assets/";

/**
 * The Board: an Excalidraw canvas filling its region, with app-level view controls. Edits are
 * not saved in this story (autosave arrives with revisions), so nothing here implies saving.
 *
 * This module is only reached through a lazy `import()` from LessonPage, so Excalidraw and its
 * CSS stay out of the main bundle.
 */
export default function Board() {
  const theme = useResolvedTheme();
  const apiRef = useRef<ExcalidrawImperativeAPI | null>(null);
  const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null);
  const [zoom, setZoom] = useState(1);
  const [hasContent, setHasContent] = useState(false);

  useEffect(
    () => () => {
      // Excalidraw tears down its own canvas on unmount; drop the undo history we can reach
      // and the API handle so nothing from this Lesson outlives the page.
      apiRef.current?.history.clear();
      apiRef.current = null;
    },
    [],
  );

  const handleApi = useCallback((next: ExcalidrawImperativeAPI) => {
    apiRef.current = next;
    setApi(next);
  }, []);

  const handleChange = useCallback(
    (
      elements: Parameters<typeof tagLearnerElements>[0],
      appState: { zoom: { value: number }; newElement: unknown; editingTextElement: unknown; multiElement: unknown },
    ) => {
      setZoom((z) => (z === appState.zoom.value ? z : appState.zoom.value));
      const live = elements.some((el) => !el.isDeleted);
      setHasContent((h) => (h === live ? h : live));

      const current = apiRef.current;
      // Wait until the element being drawn or typed is committed before touching the scene.
      if (!current || appState.newElement || appState.editingTextElement || appState.multiElement) return;
      const tagged = tagLearnerElements(elements);
      // Same array back means nothing needed tagging: this is the loop guard.
      if (tagged === elements) return;
      current.updateScene({ elements: tagged, captureUpdate: CaptureUpdateAction.NEVER });
    },
    [],
  );

  return (
    <div className="board-canvas">
      <BoardControls api={api} zoom={zoom} hasContent={hasContent} />
      <div className="board-surface">
        <Excalidraw
          excalidrawAPI={handleApi}
          onChange={handleChange}
          theme={theme}
          // Transparent so the page's `--color-board` token is the Board background in both themes.
          initialData={{ appState: { viewBackgroundColor: "transparent" } }}
        />
      </div>
    </div>
  );
}
