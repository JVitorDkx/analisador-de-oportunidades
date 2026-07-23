import {
  ArrowUpRight,
  CheckCircle2,
  CircleGauge,
  Crosshair,
  FileCheck2,
  Layers3,
  Radar,
} from "lucide-react";

import { DimensionPanel } from "@/components/dashboard/dimension-panel";
import { MarketEmptyState } from "@/components/dashboard/market-empty-state";
import { ScorePanel } from "@/components/dashboard/score-panel";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { demoOpportunity } from "@/lib/demo-data";

const mobileNavigation = [
  { label: "Visão geral", href: "#overview", icon: CircleGauge },
  { label: "Oportunidades", href: "#opportunities", icon: Crosshair },
  { label: "Mercado", href: "#market", icon: Radar },
] as const;

export default function Home() {
  return (
    <div className="flex min-h-svh bg-background">
      <AppSidebar />

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur lg:hidden">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-2.5">
              <div className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground">
                <Layers3 className="size-4" aria-hidden="true" />
              </div>
              <span className="text-sm font-semibold">Opportunity Desk</span>
            </div>
            <Badge variant="outline">Prévia</Badge>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-3" aria-label="Navegação principal">
            {mobileNavigation.map(({ label, href, icon: Icon }) => (
              <a
                key={label}
                href={href}
                className="flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {label}
              </a>
            ))}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-[1480px] px-4 py-7 sm:px-6 sm:py-10 xl:px-10">
          <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="warning">Dados demonstrativos</Badge>
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {demoOpportunity.analysisId}
                </span>
              </div>
              <h1 className="mt-4 max-w-3xl text-3xl font-semibold leading-[1.05] tracking-[-0.035em] sm:text-4xl xl:text-5xl">
                Mesa de inteligência de oportunidades
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                Decisões comerciais auditáveis, apoiadas pelo motor determinístico e separadas de qualquer estimativa do navegador.
              </p>
            </div>
            <Button asChild>
              <a href="/analysis/new">
                Nova análise
                <ArrowUpRight aria-hidden="true" />
              </a>
            </Button>
          </div>

          <ScorePanel />

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <DimensionPanel />
            <MarketEmptyState />
          </div>

          <section id="opportunities" className="mt-6 rounded-lg border border-border bg-card">
            <div className="flex flex-col justify-between gap-4 border-b border-border p-5 sm:flex-row sm:items-end sm:p-6">
              <div>
                <p className="eyebrow">Oportunidades</p>
                <h2 className="mt-2 text-xl font-semibold tracking-tight">Fila de decisão</h2>
              </div>
              <p className="max-w-md text-xs leading-5 text-muted-foreground sm:text-right">
                Esta linha usa exclusivamente o fixture oficial do repositório para demonstrar o layout inicial.
              </p>
            </div>

            <div className="hidden grid-cols-[minmax(250px,1.5fr)_0.65fr_0.65fr_0.75fr_40px] gap-4 border-b border-border px-6 py-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground md:grid">
              <span>Oportunidade</span>
              <span>Score</span>
              <span>Cobertura</span>
              <span>Decisão</span>
              <span className="sr-only">Abrir</span>
            </div>

            <article className="grid gap-5 p-5 md:grid-cols-[minmax(250px,1.5fr)_0.65fr_0.65fr_0.75fr_40px] md:items-center md:px-6 md:py-5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-signal-positive" aria-hidden="true" />
                  <h3 className="truncate text-sm font-semibold">{demoOpportunity.name}</h3>
                </div>
                <p className="mt-1 pl-4 text-xs text-muted-foreground">{demoOpportunity.category}</p>
              </div>
              <div>
                <p className="mb-1 font-mono text-[10px] uppercase text-muted-foreground md:hidden">Score</p>
                <span className="font-mono text-lg font-medium tabular-nums">{demoOpportunity.officialScore}</span>
              </div>
              <div>
                <p className="mb-1 font-mono text-[10px] uppercase text-muted-foreground md:hidden">Cobertura</p>
                <span className="font-mono text-sm">{demoOpportunity.coverage}%</span>
              </div>
              <Badge variant="success" className="justify-self-start">
                <CheckCircle2 aria-hidden="true" />
                Avançar
              </Badge>
              <Button asChild variant="ghost" size="icon" aria-label="Abrir diagnóstico demonstrativo">
                <a href="#quality">
                  <ArrowUpRight aria-hidden="true" />
                </a>
              </Button>
            </article>
          </section>

          <section id="quality" className="mt-6 grid gap-6 md:grid-cols-3">
            <div className="rounded-lg border border-border bg-primary p-6 text-primary-foreground md:col-span-2">
              <div className="flex items-center gap-2 text-primary-foreground/65">
                <FileCheck2 className="size-4" aria-hidden="true" />
                <p className="font-mono text-[10px] uppercase tracking-[0.16em]">Rastreabilidade</p>
              </div>
              <h2 className="mt-5 max-w-xl text-2xl font-semibold tracking-tight">Cada decisão continua ligada às evidências e cálculos que a sustentam.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-primary-foreground/65">
                O front-end exibe o contrato recebido. Pontuação, filtros e recomendações permanecem sob responsabilidade do core Python.
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6">
              <p className="eyebrow">Qualidade da entrada</p>
              <p className="mt-5 font-mono text-5xl font-medium tracking-[-0.06em]">{demoOpportunity.coverage}%</p>
              <p className="mt-3 text-sm text-muted-foreground">{demoOpportunity.evidenceCount} evidências observáveis presentes</p>
              <div className="mt-6 h-px bg-border" />
              <p className="mt-4 break-all font-mono text-[10px] leading-5 text-muted-foreground">Fonte: {demoOpportunity.source}</p>
            </div>
          </section>

          <footer id="settings" className="mt-10 border-t border-border py-6 text-xs text-muted-foreground">
            Prévia visual local · nenhuma informação de cliente foi carregada.
          </footer>
        </main>
      </div>
    </div>
  );
}
