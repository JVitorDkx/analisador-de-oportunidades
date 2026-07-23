import type { AnalysisResponse } from "@opportunity-analyzer/typescript-sdk";
import { AlertTriangle, CheckCircle2, ClipboardCheck, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const recommendationLabels: Record<AnalysisResponse["recommendation"], string> = {
  prioritize_test: "Priorizar teste",
  test_with_conditions: "Testar com condições",
  collect_more_data: "Coletar mais dados",
  continue_collecting: "Continuar coleta",
  consider_limited_scale: "Considerar escala limitada",
  iterate_creative: "Iterar criativo",
  iterate_offer: "Iterar oferta",
  inspect_landing_page: "Revisar landing page",
  inspect_checkout: "Revisar checkout",
  pause_for_review: "Pausar para revisão",
  run_controlled_test: "Executar teste controlado",
  deprioritize: "Despriorizar",
  reject_for_now: "Rejeitar por enquanto",
  insufficient_data: "Dados insuficientes",
};

export function AnalysisResult({ result }: { result: AnalysisResponse }) {
  const ranking = result.ranking[0];
  const score = ranking?.official_score ?? null;
  const isPositive = score !== null && score >= 70;

  return (
    <section className="scroll-mt-8 overflow-hidden rounded-lg border border-border bg-card" id="analysis-result">
      <div className="grid lg:grid-cols-[0.75fr_1.25fr]">
        <div className="border-b border-border p-6 lg:border-b-0 lg:border-r lg:p-8">
          <div className="flex items-center justify-between gap-3">
            <p className="eyebrow">Resultado oficial</p>
            <Badge variant={isPositive ? "success" : "warning"}>
              {isPositive ? <CheckCircle2 aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}
              {result.input_status}
            </Badge>
          </div>
          <p className="mt-8 font-mono text-7xl font-medium tracking-[-0.08em]">
            {score ?? "—"}
            <span className="ml-3 text-sm tracking-normal text-muted-foreground">/ 100</span>
          </p>
          <div className="mt-7 h-2 overflow-hidden rounded-full bg-muted">
            <div
              className={isPositive ? "h-full bg-signal-positive" : "h-full bg-signal-warning"}
              style={{ width: `${score ?? 0}%` }}
            />
          </div>
          <p className="mt-5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {result.analysis_id} · confiança {result.confidence}
          </p>
        </div>

        <div className="bg-primary p-6 text-primary-foreground lg:p-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-foreground/55">
            Diagnóstico do core
          </p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">
            {recommendationLabels[result.recommendation]}
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-primary-foreground/70">
            {result.executive_summary}
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-md border border-primary-foreground/15 p-4">
              <div className="flex items-center gap-2 text-primary-foreground/55">
                <ClipboardCheck className="size-4" aria-hidden="true" />
                <p className="font-mono text-[10px] uppercase tracking-wider">Próxima ação</p>
              </div>
              <p className="mt-3 text-sm font-semibold">{result.next_experiment.minimum_action}</p>
            </div>
            <div className="rounded-md border border-primary-foreground/15 p-4">
              <div className="flex items-center gap-2 text-primary-foreground/55">
                <ShieldCheck className="size-4" aria-hidden="true" />
                <p className="font-mono text-[10px] uppercase tracking-wider">Revisão humana</p>
              </div>
              <p className="mt-3 text-sm font-semibold">
                {result.human_review.required ? "Obrigatória" : "Não obrigatória"}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-px border-t border-border bg-border md:grid-cols-3">
        <div className="bg-card p-5">
          <p className="eyebrow">Pontos fortes</p>
          <ul className="mt-4 space-y-3 text-sm leading-5">
            {(ranking?.strengths ?? []).slice(0, 3).map((strength) => (
              <li key={strength.statement}>{strength.statement}</li>
            ))}
            {!ranking?.strengths.length ? <li className="text-muted-foreground">Nenhum destaque registrado.</li> : null}
          </ul>
        </div>
        <div className="bg-card p-5">
          <p className="eyebrow">Riscos</p>
          <ul className="mt-4 space-y-3 text-sm leading-5">
            {(ranking?.risks ?? []).slice(0, 3).map((risk) => (
              <li key={risk.risk}>{risk.risk}</li>
            ))}
            {!ranking?.risks.length ? <li className="text-muted-foreground">Nenhum risco crítico registrado.</li> : null}
          </ul>
        </div>
        <div className="bg-card p-5">
          <p className="eyebrow">Dados pendentes</p>
          <ul className="mt-4 space-y-3 text-sm leading-5">
            {result.missing_data.slice(0, 3).map((item) => (
              <li key={item.field}>{item.field}</li>
            ))}
            {!result.missing_data.length ? <li className="text-muted-foreground">Entrada suficiente para conclusão.</li> : null}
          </ul>
        </div>
      </div>
    </section>
  );
}
