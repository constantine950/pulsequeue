import { NavLink } from "react-router-dom";
import clsx from "clsx";

const links = [
  { to: "/metrics", label: "Overview" },
  { to: "/jobs", label: "Jobs" },
  { to: "/workers", label: "Workers" },
  { to: "/failed", label: "Failed" },
];

export function Sidebar() {
  return (
    <nav className="w-44 shrink-0 border-r border-border flex flex-col py-6 gap-1 px-3">
      <div className="px-3 mb-6">
        <span className="text-xs font-mono font-semibold text-primary tracking-widest uppercase">
          ▶ Pulse
        </span>
      </div>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            clsx(
              "px-3 py-2 rounded text-sm transition-colors",
              isActive
                ? "bg-border text-gray-100"
                : "text-muted hover:text-gray-300 hover:bg-border/50",
            )
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
