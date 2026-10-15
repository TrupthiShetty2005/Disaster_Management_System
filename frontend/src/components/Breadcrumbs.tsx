import { Link } from "react-router-dom";

export function Breadcrumbs({ items }: { items: { to?: string; label: string }[] }) {
  return (
    <nav className="mb-3 text-xs text-slate-500" aria-label="Breadcrumb">
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`}>
          {i > 0 ? <span className="mx-1 text-slate-600">/</span> : null}
          {item.to ? (
            <Link to={item.to} className="text-sky-300 hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="text-slate-300">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
