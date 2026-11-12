import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";

export const MIN_ZOOM = 0.1;
export const MAX_ZOOM = 30;
const ZOOM_STEP = 1.25;

export function clampZoom(value: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

export function nextZoom(current: number, direction: 1 | -1): number {
  const next = direction === 1 ? current * ZOOM_STEP : current / ZOOM_STEP;
  // Land exactly on 100% when stepping across it, so reset and steps agree.
  if ((current < 1 && next > 1) || (current > 1 && next < 1)) return 1;
  return clampZoom(Math.round(next * 1000) / 1000);
}

/** Zoom about the centre of the visible canvas, using only documented scene/app-state APIs. */
export function zoomTo(api: ExcalidrawImperativeAPI, value: number): void {
  const { zoom, scrollX, scrollY, width, height } = api.getAppState();
  const target = clampZoom(value);
  const cx = width / 2;
  const cy = height / 2;
  const sceneX = cx / zoom.value - scrollX;
  const sceneY = cy / zoom.value - scrollY;
  api.updateScene({
    appState: {
      zoom: { value: target as typeof zoom.value },
      scrollX: cx / target - sceneX,
      scrollY: cy / target - sceneY,
    },
  });
}

/** Fit all drawn content in view. A no-op on an empty Board. */
export function fitToContent(api: ExcalidrawImperativeAPI): void {
  const elements = api.getSceneElements();
  if (elements.length === 0) return;
  api.scrollToContent(elements, { fitToViewport: true, viewportZoomFactor: 0.9, animate: false });
}
