import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <div className="page">
      <title>Page not found · Whiteboard Tutor</title>
      <h1>We couldn't find that page.</h1>
      <p className="page-lead">The address may be mistyped, or the page may have moved.</p>
      <p>
        <Link to="/">Go to home</Link>
      </p>
    </div>
  );
}
