import { lazy } from "react";
import type { RouteObject } from "react-router";
import { AppShell } from "./AppShell";

// Route components are lazy-loaded so each page ships as its own chunk.
const HomePage = lazy(() => import("../pages/HomePage"));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage"));

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
