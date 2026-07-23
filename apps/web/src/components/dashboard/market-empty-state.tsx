import { RadioTower } from "lucide-react";

import { Button } from "@/components/ui/button";

export function MarketEmptyState() {
  return (
    <section id="market" className="market-grid flex min-h-80 flex-col rounded-lg border border-border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Inteligência de anúncios</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">Pulso de mercado</h2>
        </div>
        <div className="grid size-10 place-items-center rounded-md border border-border bg-background">
          <RadioTower className="size-4" aria-hidden="true" />
        </div>
      </div>
      <div className="my-auto max-w-sm py-10">
        <p className="text-lg font-semibold">Aguardando uma coleta válida</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Anúncios ativos, churn criativo e formatos de oferta aparecerão aqui quando houver observações reais ou um fixture de inteligência selecionado.
        </p>
        <Button variant="outline" size="sm" className="mt-5" disabled>
          Conectar fonte de mercado
        </Button>
      </div>
      <p className="border-t border-border pt-4 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        Nenhum valor estimado pelo navegador
      </p>
    </section>
  );
}
