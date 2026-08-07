import {
  BarChart3,
  Bot,
  Gauge,
  LineChart,
  NotebookPen,
  Send,
  Settings as SettingsIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: Gauge, end: true },
  { to: "/market", label: "Market", icon: LineChart },
  { to: "/analysis", label: "Analysis", icon: BarChart3 },
  { to: "/journal", label: "Journal", icon: NotebookPen },
  { to: "/performance", label: "Performance", icon: BarChart3 },
  { to: "/telegram", label: "Telegram", icon: Send },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface-card md:flex">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15">
          <Bot className="text-accent" size={18} />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-ink-primary">Fathir AI</p>
          <p className="text-[11px] text-ink-muted">Trading Assistant</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-ink-secondary hover:bg-surface-raised hover:text-ink-primary",
              )
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border px-4 py-4 text-[11px] text-ink-muted">
        Never blind signals — every setup ships with its reasons.
      </div>
    </aside>
  );
}
