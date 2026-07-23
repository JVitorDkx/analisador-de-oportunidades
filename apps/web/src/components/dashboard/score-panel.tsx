import { ArrowUpRight, CheckCircle2, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { demoOpportunity } from "@/lib/demo-data";

export function ScorePanel() {
  return (
    <section id="overview" className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
        <div className="border-b border-border p-6 sm:p-8 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between gap-3">
            <p className="eyebrow">Score oficial</p>
            <Badge variant="success">
              <CheckCircle2 aria-hidden="true" />
              {demoOpportunity.status}
            </Badge>
          </div>
          <div className="mt-8 flex items-end gap-3">
            <span className="font-mono text-7xl font-medium leading-none tracking-[-0.08em] text-foreground sm:text-8xl">
              {demoOpportunity.officialScore}
            </span>
            <span className="mb-2 font-mono text-sm text-muted-foreground">/ 100</span>
          </div>
          <div className="mt-7 h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-signal-positive"
              style={{ width: `${demoOpportunity.officialScore}%` }}
            />
          </div>
          <div className="mt-5 flex items-center gap-2 text-sm text-muted-foreground">
            <ShieldCheck className="size-4 text-signal-positive" aria-hidden="true" />
            {demoOpportunity.killSwitches} filtros eliminatórios acionados
          </div>
        </div>

        <div className="bg-primary p-6 text-primary-foreground sm:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary-foreground/60">
            Leitura executiva
          </p>
          <h2 className="mt-4 max-w-lg text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">
            {demoOpportunity.recommendation}
          </h2>
          <p className="mt-4 max-w-xl text-sm leading-6 text-primary-foreground/70">
            Os indicadores autorizados sustentam avanço para um experimento pequeno, reversível e mensurável — sem promessa de resultado.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-px overflow-hidden rounded-md border border-primary-foreground/15 bg-primary-foreground/15">
            {[
              ["Confiança", demoOpportunity.confidence],
              ["Orçamento", demoOpportunity.budget],
              ["Janela", demoOpportunity.duration],
            ].map(([label, value]) => (
              <div key={label} className="bg-primary px-3 py-4">
                <p className="text-[10px] uppercase tracking-wider text-primary-foreground/50">{label}</p>
                <p className="mt-1 font-mono text-sm font-medium">{value}</p>
              </div>
            ))}
          </div>
          <Button asChild variant="inverse" className="mt-8">
            <a href="#opportunities">
              Abrir diagnóstico
              <ArrowUpRight aria-hidden="true" />
            </a>
          </Button>
        </div>
      </div>
    </section>
  );
}
