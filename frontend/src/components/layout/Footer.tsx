import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="mt-10 border-t border-ink-100">
      <div className="shell flex flex-col gap-2 py-5 text-xs leading-5 text-ink-500 sm:flex-row sm:items-center sm:justify-between">
        <p>Not an official warning service. For emergencies, call 112.</p>
        <nav className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Footer">
          <Link className="hover:text-ink-900" to="/methodology">How it works</Link>
          <a className="hover:text-ink-900" href="/api/v1/incidents/export/">Open data</a>
          <a className="hover:text-ink-900" href="/api/docs/" target="_blank" rel="noreferrer">API</a>
          <a className="hover:text-ink-900" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap</a>
        </nav>
      </div>
    </footer>
  );
}
