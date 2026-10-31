import { useArea, useTerrain } from "../../api/queries";
import { CellFeatureMap, type CellMapFeature } from "../map/CellFeatureMap";
import { SectionHeading } from "../ui/SectionHeading";

const COLORS = { high: "#1d4f91", medium: "#5f97cf", low: "#cfe2f3" } as const;
const LEGEND = [
  { label: "Water gathers most easily", color: COLORS.high },
  { label: "In between", color: COLORS.medium },
  { label: "Drains more easily", color: COLORS.low },
];

function colorFor(value: number): string {
  return value >= 2 ? COLORS.high : value >= 1 ? COLORS.medium : COLORS.low;
}

/** Shows only where real terrain is stored, so other areas don't get an empty box. */
export function LowGroundMap() {
  const terrain = useTerrain();
  const area = useArea();
  const cells = terrain.data?.features ?? [];
  if (!cells.length) return null;

  const features: CellMapFeature[] = cells.map((cell) => ({
    id: cell.properties.cell_code,
    geometry: cell.geometry,
    value: { high: 2, medium: 1, low: 0 }[cell.properties.terrain_class] ?? 0,
    label: `${cell.properties.elevation_m} m above sea level`,
    unit: "",
    detail: `${cell.properties.relative_elevation_m} m against nearby land`,
  }));

  return (
    <section>
      <SectionHeading
        eyebrow="The shape of the land"
        title="Where water can gather"
        description="Lower ground and hollows collect rain first. This comes from satellite elevation and can't see drains or pumps, so a pale area can still flood. Check live reports for what is happening now."
      />
      <div className="panel mt-4 p-4 sm:p-5">
        <CellFeatureMap
          features={features}
          colorFor={colorFor}
          legend={LEGEND}
          boundary={area.data?.boundary}
          height="400px"
          caption={terrain.data?.source ? `Elevation: ${terrain.data.source}` : undefined}
        />
      </div>
    </section>
  );
}
