/** Labels data provenance for demo / rule-based / model outputs. */
export function EstimateCallout({
  title,
  kind,
  value,
  factors,
}: {
  title: string;
  kind: "SIMULATED DATA" | "RULE-BASED ESTIMATE" | "MODEL PREDICTION" | "REAL DATA";
  value?: string;
  factors?: { name: string; level: string }[];
}) {
  return (
    <aside className="rounded border border-line bg-panel p-3 text-sm" aria-label={title}>
      <p className="text-[10px] uppercase tracking-widest text-slate-500">{kind}</p>
      <p className="mt-1 text-slate-200">
        {title}
        {value ? `: ${value}` : ""}
      </p>
      {factors?.length ? (
        <ul className="mt-2 space-y-1 text-xs text-slate-400">
          {factors.map((f) => (
            <li key={f.name} className="flex justify-between gap-2">
              <span>{f.name}</span>
              <span className="text-slate-300">{f.level}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </aside>
  );
}
