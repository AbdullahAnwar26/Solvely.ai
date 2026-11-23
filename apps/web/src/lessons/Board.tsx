import { CaptureUpdateAction, Excalidraw, restoreElements } from "@excalidraw/excalidraw";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import "@excalidraw/excalidraw/index.css";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useResolvedTheme } from "../theme/useResolvedTheme";
import { fetchBoard, saveBoard } from "./boardApi";
import "./board.css";
import BoardControls from "./BoardControls";
import { contentToken, initialAppState, sceneFingerprint, serializeBoard, type BoardState } from "./boardSerialize";
import { clearDraft, evaluateDraft, readDraft, type DraftOffer } from "./draftStorage";
import { tagLearnerElements } from "./originTag";
import { ConflictAlert, DraftBanner, SaveStatus } from "./SaveStatus";
import { useAutosave, type Snapshot } from "./useAutosave";

// Self-host Excalidraw's fonts (committed under public/excalidraw-assets) so drawing text never
// calls a third-party CDN. Must be set before the library first loads a font.
(window as unknown as { EXCALIDRAW_ASSET_PATH?: string }).EXCALIDRAW_ASSET_PATH = "/excalidraw-assets/";

// Images are out of scope (nothing binary is saved), so the image tool is hidden.
const UI_OPTIONS = { tools: { image: false } } as const;

type Props = {
  lessonId: string;
  /** The signed-in Learner, or null: device drafts are kept per user and never without one. */
  userId: number | null;
  /** The latest saved revision, loaded before the Board mounts. */
  initial: BoardState;
  /** Header element the save status renders into (the Board header lives in LessonPage). */
  statusSlot: HTMLElement | null;
};

type InitialData = {
  elements: ReturnType<typeof restoreElements>;
  appState: ReturnType<typeof initialAppState>;
};

function restoreBoard(board: BoardState["board"]): InitialData {
  return {
    // Documented restore helper: fills defaults and repairs bindings; keeps `customData`.
    elements: restoreElements(board.elements as never, null, { repairBindings: true }),
    appState: initialAppState(board),
  };
}

/**
 * The Board: an Excalidraw canvas filling its region, with app-level view controls and autosave.
 *
 * This module is only reached through a lazy `import()` from LessonPage, so Excalidraw and its
 * CSS stay out of the main bundle. It mounts only after the latest revision was loaded, so
 * autosave can never run over an unloaded Board.
 */
export default function Board({ lessonId, userId, initial, statusSlot }: Props) {
  const theme = useResolvedTheme();
  const apiRef = useRef<ExcalidrawImperativeAPI | null>(null);
  const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null);
  const [zoom, setZoom] = useState(1);
  // Restored once: Excalidraw reads initialData only on mount.
  const [initialData] = useState(() => restoreBoard(initial.board));
  const [hasContent, setHasContent] = useState(() => initialData.elements.some((el) => !el.isDeleted));
  const surfaceRef = useRef<HTMLDivElement>(null);
  // A device draft left by an earlier session: offered back, never applied automatically.
  const [offer, setOffer] = useState<DraftOffer>(() =>
    userId === null
      ? { kind: "none" }
      : evaluateDraft(readDraft(userId, lessonId), { revision: initial.revision, elements: initial.board.elements }),
  );

  const snapshot = useCallback((): Snapshot | null => {
    const current = apiRef.current;
    if (!current) return null;
    const app = current.getAppState();
    // Not while the initial scene is loading or an element is mid-draw or mid-typing.
    if (app.isLoading || app.newElement || app.editingTextElement || app.multiElement) return null;
    const elements = current.getSceneElements();
    return {
      board: serializeBoard(elements, app),
      fingerprint: sceneFingerprint(elements),
      token: contentToken(elements),
    };
  }, []);

  const save = useCallback(
    (body: Parameters<typeof saveBoard>[1]) => saveBoard(lessonId, body),
    [lessonId],
  );

  const autosave = useAutosave({
    initialRevision: initial.revision,
    initialFingerprint: sceneFingerprint(initialData.elements),
    initialToken: contentToken(initialData.elements),
    draftScope: userId === null ? undefined : { userId, lessonId },
    save,
    snapshot,
  });
  const { notifyChange, holdDraft, markUnsaved, currentRevision } = autosave;

  // On open: a draft equal to the server content is dropped; an offered draft is held so autosave
  // can neither overwrite nor delete it until the Learner chooses.
  useEffect(() => {
    if (userId === null) return;
    if (offer.kind === "none") {
      if (offer.equal) clearDraft(userId, lessonId);
    } else {
      holdDraft(true);
    }
    // Runs once for the offer found on open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const closeOffer = useCallback(() => {
    holdDraft(false);
    setOffer({ kind: "none" });
    // The banner's buttons are gone: hand focus back to the Board instead of losing it.
    surfaceRef.current?.querySelector<HTMLElement>(".excalidraw")?.focus();
  }, [holdDraft]);

  const discardDraft = useCallback(() => {
    if (userId !== null) clearDraft(userId, lessonId);
    closeOffer();
  }, [userId, lessonId, closeOffer]);

  const restoreDraft = useCallback(() => {
    const current = apiRef.current;
    if (offer.kind !== "restore" || !current) return;
    // The Lesson moved on while the banner was open: restoring would overwrite newer work.
    if (currentRevision() !== offer.draft.base_revision) {
      setOffer({ kind: "stale", draft: offer.draft });
      return;
    }
    const restored = restoreBoard(offer.draft.board);
    current.updateScene({
      elements: restored.elements,
      appState: restored.appState as never,
      captureUpdate: CaptureUpdateAction.NEVER,
    });
    holdDraft(false, true);
    // Shown as unsaved; autosave persists it from the current base revision (409 still applies).
    markUnsaved();
    setOffer({ kind: "none" });
    current.history.clear();
    surfaceRef.current?.querySelector<HTMLElement>(".excalidraw")?.focus();
  }, [offer, currentRevision, holdDraft, markUnsaved]);

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
      appState: {
        zoom: { value: number };
        newElement: unknown;
        editingTextElement: unknown;
        multiElement: unknown;
        isLoading?: boolean;
      },
    ) => {
      setZoom((z) => (z === appState.zoom.value ? z : appState.zoom.value));
      const live = elements.some((el) => !el.isDeleted);
      setHasContent((h) => (h === live ? h : live));
      // Cheap: only re-arms the debounce timer; the scene is read when it fires.
      if (!appState.isLoading) notifyChange(contentToken(elements));

      const current = apiRef.current;
      // Wait until the element being drawn or typed is committed before touching the scene.
      if (!current || appState.newElement || appState.editingTextElement || appState.multiElement) return;
      const tagged = tagLearnerElements(elements);
      // Same array back means nothing needed tagging: this is the loop guard.
      if (tagged === elements) return;
      current.updateScene({ elements: tagged, captureUpdate: CaptureUpdateAction.NEVER });
    },
    [notifyChange],
  );

  const { reloadWith } = autosave;
  const reloadLatest = useCallback(async () => {
    const current = apiRef.current;
    if (!current) return false;
    let latest: BoardState;
    try {
      latest = await fetchBoard(lessonId);
    } catch {
      return false;
    }
    reloadWith(() => {
      const restored = restoreBoard(latest.board);
      current.updateScene({
        elements: restored.elements,
        appState: restored.appState as never,
        captureUpdate: CaptureUpdateAction.NEVER,
      });
      // Undo must not bring back the discarded local changes.
      current.history.clear();
      return {
        revision: latest.revision,
        fingerprint: sceneFingerprint(restored.elements),
        token: contentToken(restored.elements),
      };
    });
    return true;
  }, [lessonId, reloadWith]);

  return (
    <div className="board-canvas">
      {statusSlot &&
        createPortal(
          <SaveStatus status={autosave.status} retrying={autosave.retrying} onRetry={autosave.retry} />,
          statusSlot,
        )}
      {autosave.status === "conflict" && <ConflictAlert onReload={reloadLatest} />}
      {(offer.kind === "restore" || offer.kind === "stale") && (
        <DraftBanner kind={offer.kind} onRestore={restoreDraft} onDiscard={discardDraft} />
      )}
      <BoardControls api={api} zoom={zoom} hasContent={hasContent} />
      <div className="board-surface" ref={surfaceRef}>
        <Excalidraw
          excalidrawAPI={handleApi}
          onChange={handleChange}
          theme={theme}
          UIOptions={UI_OPTIONS}
          initialData={initialData as never}
        />
      </div>
    </div>
  );
}
