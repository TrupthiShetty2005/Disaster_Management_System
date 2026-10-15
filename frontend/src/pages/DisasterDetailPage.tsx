import { Link, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import { Breadcrumbs } from "../components/Breadcrumbs";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { KpiCard } from "../components/KpiCard";
import { SafetyBanner } from "../components/SafetyBanner";
import { StatusBadge } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { fetchIncidentPicture } from "../services/incident";
import { DEMO_INCIDENT_ID } from "../constants/demo";

const sections = [
  ["Overview", "overview"],
  ["Weather", "weather"],
  ["Risk", "risk"],
  ["Satellite", "satellite"],
  ["Flood", "flood"],
  ["Computer Vision", "vision"],
  ["Damage", "damage"],
  ["Infrastructure", "infra"],
  ["Resources", "resources"],
  ["Alerts", "alerts"],
  ["Rescue Plan", "rescue"],
  ["Timeline", "timeline"],
] as const;

export function DisasterDetailPage() {
  const { id } = useParams();
  const incidentId = id || DEMO_INCIDENT_ID;
  const { data, loading, error } = useAsync(() => fetchIncidentPicture(incidentId), [incidentId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message="Incident not found." />;

  return (
    <div className="space-y-4">
      <Breadcrumbs
        items={[
          { to: "/dashboard", label: "Command dashboard" },
          { label: "Incident command" },
        ]}
      />
      <SafetyBanner compact />
      <header>
        <h2 className="font-display text-2xl text-amber-300">{data.incident.title}</h2>
        <p className="text-sm text-slate-400">
          {data.region} · {data.incident.disaster_type} · <StatusBadge value={data.incident.severity} />
        </p>
      </header>
      <nav className="flex flex-wrap gap-2 text-xs">
        {sections.map(([label, hash]) => (
          <a key={hash} href={`#${hash}`} className="rounded border border-line px-2 py-1 text-slate-400 hover:text-slate-200">
            {label}
          </a>
        ))}
      </nav>
      <Section id="overview" title="Overview">
        <p className="text-sm text-slate-300">{data.incident.summary}</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <KpiCard label="People at risk" value={String(data.incident.people_at_risk)} />
          <KpiCard label="Flood extent" value={`${data.flood.extent_km2} km²`} />
          <KpiCard label="Phase" value={data.incident.phase} />
        </div>
      </Section>
      <Section id="weather" title="Weather">
        <p>
          {data.weather.conditions} · {data.weather.rainfall_mm} mm · {data.weather.temperature_c}°C
        </p>
        <Link className="text-xs text-sky-300" to="/weather">
          Open weather intelligence
        </Link>
      </Section>
      <Section id="risk" title="High-risk zone prediction">
        {data.risk_zones.length ? (
          <ul className="list-disc pl-5 text-sm">
            {data.risk_zones.map((z) => (
              <li key={z.id}>
                {z.name} — {z.risk_level} ({z.risk_score})
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="No risk zones for this location." />
        )}
        <Link className="text-xs text-sky-300" to={data.links.risk}>
          Risk intelligence
        </Link>
      </Section>
      <Section id="satellite" title="Satellite image comparison">
        <Link className="text-sm text-sky-300" to={data.links.satellite_compare}>
          Before/after comparison
        </Link>
      </Section>
      <Section id="flood" title="Flood detection map">
        <p className="text-sm">
          Depth {data.flood.water_depth_m} m · extent {data.flood.extent_km2} km²
        </p>
        <Link className="text-xs text-sky-300" to={data.links.flood_map}>
          Flood detection
        </Link>
      </Section>
      <Section id="vision" title="Computer vision">
        <Link className="text-sm text-sky-300" to={data.links.vision}>
          Object detection / incident analysis
        </Link>
      </Section>
      <Section id="damage" title="Building damage classification">
        {data.buildings.length ? (
          <ul className="list-disc pl-5 text-sm">
            {data.buildings.map((b) => (
              <li key={b.name}>
                {b.name}: {b.damage_class}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="No building rows yet." />
        )}
        <Link className="text-xs text-sky-300" to={data.links.damage_report}>
          Damage assessment report
        </Link>
      </Section>
      <Section id="infra" title="Infrastructure / road accessibility">
        <ul className="list-disc pl-5 text-sm">
          {data.roads.map((r) => (
            <li key={r.name}>
              {r.name}: {r.accessibility}
            </li>
          ))}
          {data.infrastructure.map((i) => (
            <li key={i.name}>
              {i.name} ({i.category}): {i.status}
            </li>
          ))}
        </ul>
      </Section>
      <Section id="resources" title="Rescue resource recommendation">
        {data.resources.length ? (
          <ul className="list-disc pl-5 text-sm">
            {data.resources.map((r) => (
              <li key={r.id}>
                {r.name} · {r.type} · {r.status}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message="No resources in this region." />
        )}
      </Section>
      <Section id="alerts" title="Early warning alerts">
        {data.alerts.map((a) => (
          <p key={a.id} className="text-sm">
            <StatusBadge value={a.severity} /> {a.title}
          </p>
        ))}
        <Link className="text-xs text-sky-300" to={data.links.alerts}>
          Alert history
        </Link>
      </Section>
      <Section id="rescue" title="AI-generated rescue plan">
        {data.rescue_plan ? (
          <p className="text-sm">
            Plan {data.rescue_plan.id.slice(0, 8)}… · {data.rescue_plan.decision}
          </p>
        ) : (
          <EmptyState message="Generate a plan from Rescue Planning (human approval required)." />
        )}
        <ul className="mt-2 list-disc pl-5 text-sm">
          {data.priorities.map((p) => (
            <li key={p.title}>
              {p.title} · {p.level ?? "n/a"} · {p.people_affected} people
            </li>
          ))}
        </ul>
        <Link className="text-xs text-sky-300" to={data.links.rescue}>
          Rescue planning
        </Link>
      </Section>
      <Section id="timeline" title="Scenario timeline">
        <ol className="space-y-1 text-sm text-slate-400">
          {data.timeline.map((t) => (
            <li key={t.t}>
              <span className="font-mono text-[11px] text-slate-500">{t.t}</span> — {t.event}
            </li>
          ))}
        </ol>
      </Section>
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-4 rounded border border-line bg-panel p-3">
      <h3 className="mb-2 text-xs uppercase tracking-widest text-slate-500">{title}</h3>
      {children}
    </section>
  );
}
