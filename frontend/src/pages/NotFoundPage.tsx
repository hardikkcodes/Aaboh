import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="shell max-w-3xl py-20">
      <div className="panel p-8 text-center sm:p-12">
        <p className="eyebrow">404 · Not found</p>
        <h1 className="display-title mt-2">This page does not exist</h1>
        <p className="prose-civic mx-auto mt-3 max-w-xl">
          The address may be mistyped, or the record may no longer be public. Nothing has been
          substituted to fill the gap.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/" className="btn-primary">Back to overview</Link>
          <Link to="/reports" className="btn-secondary">Community reports</Link>
          <Link to="/methodology" className="btn-ghost">Methodology</Link>
        </div>
      </div>
    </div>
  );
}
