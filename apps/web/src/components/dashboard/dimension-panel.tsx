import { demoOpportunity } from "@/lib/demo-data";

export function DimensionPanel() {
  return (
    <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Composição determinística</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">Dimensões do score</h2>
        </div>
        <span className="hidden font-mono text-[10px] uppercase tracking-wider text-muted-foreground sm:block">
          SCORE-0.1.0
        </span>
      </div>
      <div className="mt-7 space-y-6">
        {demoOpportunity.dimensions.map((dimension) => (
          <div key={dimension.label}>
            <div className="mb-2 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold">{dimension.label}</p>
                <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">peso {dimension.weight}</p>
              </div>
              <span className="font-mono text-lg font-medium tabular-nums">{dimension.value}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-foreground" style={{ width: `${dimension.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
