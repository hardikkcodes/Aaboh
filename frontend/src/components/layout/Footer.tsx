import { Link } from "react-router-dom";

const sourceLinks = [
  { href: "https://open-meteo.com/", label: "Open-Meteo" },
  { href: "https://mausam.imd.gov.in/", label: "India Meteorological Department" },
  { href: "https://cpcb.nic.in/", label: "CPCB" },
  { href: "https://www.usgs.gov/landsat-missions", label: "USGS Landsat" },
  { href: "https://www.openstreetmap.org/copyright", label: "OpenStreetMap" },
];

export function Footer() {
  return (
    <footer className="mt-20 border-t border-ink-100 bg-white">
      <div className="shell grid gap-10 py-12 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <p className="font-display text-xl text-ink-950">ClimateSense Kolkata</p>
          <p className="prose-civic mt-3 max-w-sm">
            A civic climate-intelligence prototype for Kolkata. It shows the source, time, units and
            quality of every environmental record, and leaves gaps visible when verified data is not
            available.
          </p>
          <p className="mt-4 text-xs leading-5 text-ink-500">
            Not an official warning service. For emergencies call 112. Follow instructions from IMD,
            KMC and emergency services.
          </p>
        </div>
        <div>
          <p className="eyebrow">Explore</p>
          <ul className="mt-3 space-y-2 text-sm text-ink-600">
            <li><Link className="hover:text-ink-900" to="/weather">Weather forecast</Link></li>
            <li><Link className="hover:text-ink-900" to="/alerts">Official alerts</Link></li>
            <li><Link className="hover:text-ink-900" to="/heat">Heat &amp; environment</Link></li>
            <li><Link className="hover:text-ink-900" to="/reports">Community reports</Link></li>
            <li><Link className="hover:text-ink-900" to="/insights">Local insights</Link></li>
          </ul>
        </div>
        <div>
          <p className="eyebrow">Platform</p>
          <ul className="mt-3 space-y-2 text-sm text-ink-600">
            <li><Link className="hover:text-ink-900" to="/methodology">Methodology &amp; limits</Link></li>
            <li><Link className="hover:text-ink-900" to="/methodology#data-status">Data availability</Link></li>
            <li><a className="hover:text-ink-900" href="/api/docs/" target="_blank" rel="noreferrer">API reference</a></li>
            <li><a className="hover:text-ink-900" href="/api/schema/" target="_blank" rel="noreferrer">OpenAPI schema</a></li>
            <li><Link className="hover:text-ink-900" to="/account">Your account</Link></li>
          </ul>
        </div>
        <div>
          <p className="eyebrow">Primary sources</p>
          <ul className="mt-3 space-y-2 text-sm text-ink-600">
            {sourceLinks.map((source) => (
              <li key={source.label}>
                <a className="hover:text-ink-900" href={source.href} target="_blank" rel="noreferrer">
                  {source.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-ink-100">
        <div className="shell flex flex-col gap-2 py-5 text-xs text-ink-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Community data is user-submitted and independently moderated. Provider data is not official.</p>
          <p>Map data © OpenStreetMap contributors · Built for public-interest use.</p>
        </div>
      </div>
    </footer>
  );
}
