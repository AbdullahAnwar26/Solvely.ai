import type { ReactNode } from "react";

export function AuthLayout({ title, lead, children }: { title: string; lead?: string; children: ReactNode }) {
  return (
    <main className="auth-page" id="main">
      <title>{`${title} · Whiteboard Tutor`}</title>
      <div className="auth-card">
        <p className="auth-brand">Whiteboard Tutor</p>
        <h1>{title}</h1>
        {lead && <p className="auth-lead">{lead}</p>}
        {children}
      </div>
    </main>
  );
}
