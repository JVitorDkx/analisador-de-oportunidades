import { Activity, CircleGauge, Crosshair, Layers3, Radar, Settings2 } from "lucide-react";

const navigation = [
  { label: "Visão geral", href: "#overview", icon: CircleGauge, active: true },
  { label: "Oportunidades", href: "#opportunities", icon: Crosshair, active: false },
  { label: "Mercado", href: "#market", icon: Radar, active: false },
  { label: "Experimentos", href: "#experiments", icon: Activity, active: false },
] as const;

export function AppSidebar() {
  return (
    <aside className="hidden min-h-svh w-60 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex">
      <div className="flex h-20 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="grid size-9 place-items-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
          <Layers3 className="size-4" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight">Opportunity Desk</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-sidebar-muted">Inteligência v0.1</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3" aria-label="Navegação principal">
        <p className="px-3 pb-2 pt-3 font-mono text-[10px] uppercase tracking-[0.18em] text-sidebar-muted">
          Workspace
        </p>
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.label}
              href={item.href}
              className={
                item.active
                  ? "flex items-center gap-3 rounded-md bg-sidebar-accent px-3 py-2.5 text-sm font-semibold text-sidebar-foreground"
                  : "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
              }
            >
              <Icon className="size-4" aria-hidden="true" />
              {item.label}
            </a>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <a
          href="#settings"
          className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
        >
          <Settings2 className="size-4" aria-hidden="true" />
          Configurações
        </a>
        <div className="mt-3 rounded-md border border-sidebar-border p-3">
          <p className="text-xs font-semibold">Ambiente de prévia</p>
          <p className="mt-1 text-xs leading-relaxed text-sidebar-muted">Sem conexão com dados de clientes.</p>
        </div>
      </div>
    </aside>
  );
}
