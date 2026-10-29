import { Suspense, useEffect, useRef, useState, type MouseEvent } from "react";
import { NavLink, Outlet } from "react-router";
import "./AppShell.css";
import { useSession } from "../auth/SessionContext";
import { CloseIcon, HomeIcon, MenuIcon, SettingsIcon, SidebarIcon, SignOutIcon } from "./icons";
import { useLayoutMode, type LayoutMode } from "./layoutMode";
import { readSidebarCollapsed, writeSidebarCollapsed } from "./sidebarPreference";

const NAV_ITEMS = [
  { to: "/", label: "Home", Icon: HomeIcon, end: true },
  { to: "/settings", label: "Settings", Icon: SettingsIcon, end: false },
] as const;

type SidebarState = "expanded" | "collapsed" | "hidden";

export function AppShell() {
  const mode = useLayoutMode();
  const [collapsed, setCollapsed] = useState(readSidebarCollapsed);
  // The sheet/drawer is open only for the layout it was opened in, so a resize closes it.
  const [overlayFor, setOverlayFor] = useState<LayoutMode | null>(null);
  const overlay = mode !== "docked" && overlayFor === mode;

  const { state, signOut } = useSession();
  const email = state.status === "signedIn" ? state.user.email : null;
  const [signOutPending, setSignOutPending] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);

  const onSignOut = async () => {
    if (signOutPending) return;
    setSignOutPending(true);
    setSignOutError(null);
    setOverlayFor(null);
    try {
      // On success the route guard redirects to /sign-in, which unmounts the shell.
      await signOut();
    } catch {
      setSignOutError("Could not sign out. Check your connection and try again.");
      setSignOutPending(false);
    }
  };

  const toggleRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const mainRef = useRef<HTMLElement>(null);

  let sidebar: SidebarState;
  if (mode === "docked") sidebar = collapsed ? "collapsed" : "expanded";
  else if (overlay) sidebar = "expanded";
  else sidebar = mode === "rail" ? "collapsed" : "hidden";

  const closeOverlay = (restoreFocus: boolean) => {
    setOverlayFor(null);
    if (restoreFocus) toggleRef.current?.focus();
  };

  const onToggle = () => {
    if (mode === "docked") {
      const next = !collapsed;
      setCollapsed(next);
      writeSidebarCollapsed(next);
    } else if (overlay) {
      closeOverlay(false);
    } else {
      setOverlayFor(mode);
    }
  };

  useEffect(() => {
    if (!overlay) return;
    navRef.current?.querySelector<HTMLElement>("a[href]")?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOverlayFor(null);
        toggleRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [overlay]);

  const onSkip = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    mainRef.current?.focus();
  };

  const expanded = sidebar === "expanded";
  let toggleLabel: string;
  if (mode === "docked") toggleLabel = collapsed ? "Expand sidebar" : "Collapse sidebar";
  else if (mode === "rail") toggleLabel = overlay ? "Close navigation" : "Open navigation";
  else toggleLabel = overlay ? "Close menu" : "Open menu";

  const toggle = (
    <button
      ref={toggleRef}
      type="button"
      className="icon-button"
      aria-label={toggleLabel}
      aria-expanded={expanded}
      aria-controls="sidebar"
      onClick={onToggle}
    >
      {mode === "drawer" ? overlay ? <CloseIcon /> : <MenuIcon /> : <SidebarIcon />}
    </button>
  );

  return (
    <div
      className="shell"
      data-layout={mode}
      data-sidebar={sidebar}
      data-overlay={overlay ? "" : undefined}
    >
      <a className="skip-link" href="#main" onClick={onSkip}>
        Skip to main content
      </a>

      {mode === "drawer" && (
        <header className="topbar">
          {toggle}
          <span className="brand">Whiteboard Tutor</span>
        </header>
      )}

      <nav
        ref={navRef}
        id="sidebar"
        className="sidebar"
        aria-label="Main"
        inert={sidebar === "hidden"}
      >
        {mode !== "drawer" && (
          <div className="sidebar-head">
            {toggle}
            {expanded && <span className="brand">Whiteboard Tutor</span>}
          </div>
        )}
        <ul className="nav-list">
          {NAV_ITEMS.map(({ to, label, Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className="nav-link"
                title={expanded ? undefined : label}
                onClick={() => overlay && closeOverlay(false)}
              >
                <Icon />
                <span className={expanded ? "nav-label" : "visually-hidden"}>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="sidebar-account">
          {email && (
            <p className={expanded ? "account-email" : "visually-hidden"} title={email}>
              <span className="visually-hidden">Signed in as </span>
              {email}
            </p>
          )}
          <button
            type="button"
            className="nav-link nav-button"
            title={expanded ? undefined : "Sign out"}
            disabled={signOutPending}
            onClick={onSignOut}
          >
            <SignOutIcon />
            <span className={expanded ? "nav-label" : "visually-hidden"}>Sign out</span>
          </button>
        </div>
      </nav>

      {overlay && <div className="scrim" aria-hidden="true" onClick={() => closeOverlay(true)} />}

      <main ref={mainRef} id="main" className="content" tabIndex={-1} inert={overlay}>
        {signOutError && (
          <p role="alert" className="shell-alert">
            {signOutError}
          </p>
        )}
        <Suspense
          fallback={
            <p role="status" className="visually-hidden">
              Loading
            </p>
          }
        >
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}
