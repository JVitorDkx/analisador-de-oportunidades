import Link from "next/link";
import { ArrowLeft, Layers3 } from "lucide-react";

import { AnalysisForm } from "@/components/analysis/analysis-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function NewAnalysisPage() {
  return (
    <main className="min-h-svh bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid size-9 place-items-center rounded-md bg-primary text-primary-foreground">
              <Layers3 className="size-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold">Opportunity Desk</p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Nova análise</p>
            </div>
          </Link>
          <Button asChild variant="outline" size="sm">
            <Link href="/">
              <ArrowLeft aria-hidden="true" />
              Voltar ao painel
            </Link>
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="mb-8 max-w-3xl">
          <Badge variant="outline">SCORE-0.1.0 · contrato v1.1.0</Badge>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-[-0.035em] sm:text-5xl">
            Coloque uma nova oportunidade na mesa
          </h1>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            O formulário coleta fatos e avaliações normalizadas. O score oficial, os kill switches e o diagnóstico são produzidos exclusivamente pela API FastAPI.
          </p>
        </div>
        <AnalysisForm />
      </div>
    </main>
  );
}
