import { lazy } from "react";
import type { RouteObject } from "react-router";
import { RedirectIfSignedIn, RequireAuth, SessionRoot, WaitForSession } from "../auth/guards";
import { AppShell } from "./AppShell";

// Route components are lazy-loaded so each page ships as its own chunk.
const HomePage = lazy(() => import("../pages/HomePage"));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage"));
const SettingsPage = lazy(() => import("../pages/SettingsPage"));
const SignUpPage = lazy(() => import("../auth/SignUpPage"));
const SignInPage = lazy(() => import("../auth/SignInPage"));
const ForgotPasswordPage = lazy(() => import("../auth/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("../auth/ResetPasswordPage"));

export const routes: RouteObject[] = [
  {
    // Session bootstrap (`GET /auth/me/`) wraps every route.
    element: <SessionRoot />,
    children: [
      {
        element: <RedirectIfSignedIn />,
        children: [
          { path: "sign-up", element: <SignUpPage /> },
          { path: "sign-in", element: <SignInPage /> },
          { path: "forgot-password", element: <ForgotPasswordPage /> },
        ],
      },
      {
        element: <WaitForSession />,
        children: [{ path: "reset-password", element: <ResetPasswordPage /> }],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <AppShell />,
            children: [
              { index: true, element: <HomePage /> },
              { path: "settings", element: <SettingsPage /> },
              { path: "*", element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
];
