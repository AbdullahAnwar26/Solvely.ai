import { Excalidraw } from "@excalidraw/excalidraw";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import "@excalidraw/excalidraw/index.css";
import { useEffect, useRef } from "react";
import { useResolvedTheme } from "../theme/useResolvedTheme";

/**
 * The Board: an Excalidraw canvas filling its region. Edits are not saved in this story
 * (autosave arrives with revisions), so nothing here implies saving.
 *
 * This module is only reached through a lazy `import()` from LessonPage, so Excalidraw and its
 * CSS stay out of the main bundle.
 */
export default function Board() {
  const theme = useResolvedTheme();
  const apiRef = useRef<ExcalidrawImperativeAPI | null>(null);

  useEffect(
    () => () => {
      // Excalidraw tears down its own canvas on unmount; drop the undo history we can reach
      // and the API handle so nothing from this Lesson outlives the page.
      apiRef.current?.history.clear();
      apiRef.current = null;
    },
    [],
  );

  return (
    <div className="board-canvas">
      <Excalidraw
        excalidrawAPI={(api) => {
          apiRef.current = api;
        }}
        theme={theme}
        // Transparent so the page's `--color-board` token is the Board background in both themes.
        initialData={{ appState: { viewBackgroundColor: "transparent" } }}
      />
    </div>
  );
}
