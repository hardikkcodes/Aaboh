import { Download } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/ui/PageHeader";

const DATASETS = [
  {
    title: "Resident reports",
    body: "Report type, hour, water depth, how passable it was and how well confirmed. Locations are rounded to about 110 m. Names, descriptions and photos are never included.",
    href: "/api/v1/incidents/export/",
    label: "Download CSV",
    licence: "CC BY 4.0",
  },
  {
    title: "Ground and elevation",
    body: "Elevation and water-gathering score for each 1 km square in Kolkata, from Copernicus GLO-30.",
    href: "/api/v1/environment/terrain/",
    label: "Download GeoJSON",
    licence: "CC BY 4.0, with Copernicus credit",
  },
  {
    title: "Ground heat",
    body: "The latest Landsat ground temperature for each 1 km square in Kolkata.",
    href: "/api/v1/environment/observations/?variable=lst_c",
    label: "Download GeoJSON",
    licence: "Public domain (USGS)",
  },
];

export function OpenDataPage() {
  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        title="Open data"
        description="Free to download for students, journalists and civic groups. Please credit Aaboh and keep the limits below in mind."
      />
      <section className="grid gap-4 md:grid-cols-3">
        {DATASETS.map((item) => (
          <article key={item.title} className="panel flex flex-col p-5">
            <h2 className="section-title">{item.title}</h2>
            <p className="prose-civic mt-2 flex-1">{item.body}</p>
            <p className="mt-3 text-xs text-ink-500">Licence: {item.licence}</p>
            <a href={item.href} className="btn-secondary mt-3 text-sm" download>
              <Download className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {item.label}
            </a>
          </article>
        ))}
      </section>
      <section className="panel-muted p-5 text-sm leading-6 text-ink-700">
        <h2 className="section-title">Before you use it</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Reports are what residents saw. No report does not mean nothing happened.</li>
          <li>Places with more users send more reports, so counts aren't a fair ranking of areas.</li>
          <li>This isn't official data.</li>
        </ul>
        <p className="mt-3">
          Building something? See the <a className="link" href="/api/docs/">API documentation</a> or read{" "}
          <Link className="link" to="/methodology">how Aaboh works</Link>.
        </p>
      </section>
    </div>
  );
}
