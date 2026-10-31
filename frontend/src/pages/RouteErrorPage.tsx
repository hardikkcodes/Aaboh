import { TriangleAlert } from "lucide-react";
import { useRouteError } from "react-router-dom";

import { NotFoundPage } from "./NotFoundPage";

/** Shown if a page crashes, or an old tab asks for files replaced by a new release. */
export function RouteErrorPage() {
  const error = useRouteError() as { status?: number } | undefined;
  if (error?.status === 404) return <NotFoundPage />;
  return (
    <div className="shell flex min-h-[60vh] flex-col items-center justify-center text-center">
      <span className="icon-tile"><TriangleAlert className="h-5 w-5" aria-hidden="true" /></span>
      <h1 className="display-title mt-4">Something went wrong</h1>
      <p className="prose-civic mt-2 max-w-md">Reloading usually fixes this. For emergencies, call 112.</p>
      <button type="button" className="btn-primary mt-5" onClick={() => window.location.reload()}>
        Reload the page
      </button>
    </div>
  );
}
