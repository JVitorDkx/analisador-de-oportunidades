"use client";

import type { AnalysisResponse } from "@opportunity-analyzer/typescript-sdk";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, FlaskConical, LoaderCircle, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import { useForm, type FieldError } from "react-hook-form";

import { AnalysisResult } from "@/components/analysis/analysis-result";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  analysisFormSchema,
  parseLocalizedNumber,
  syntheticAnalysisExample,
  type AnalysisFormInput,
  type AnalysisFormValues,
} from "@/lib/analysis/schema";

async function submitAnalysis(values: AnalysisFormValues): Promise<AnalysisResponse> {
  const response = await fetch("/api/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(values),
  });
  const body = (await response.json()) as AnalysisResponse | { detail?: string };
  if (!response.ok) {
    throw new Error("detail" in body && body.detail ? body.detail : "Não foi possível concluir a análise.");
  }
  return body as AnalysisResponse;
}

function FieldMessage({ error }: { error?: FieldError }) {
  return error ? (
    <p className="mt-1.5 text-xs text-red-800" role="alert">
      {error.message}
    </p>
  ) : null;
}

export function AnalysisForm() {
  const resultRef = useRef<HTMLDivElement>(null);
  const form = useForm<AnalysisFormInput, unknown, AnalysisFormValues>({
    resolver: zodResolver(analysisFormSchema),
    defaultValues: syntheticAnalysisExample,
  });
  const mutation = useMutation({
    mutationFn: submitAnalysis,
  });

  useEffect(() => {
    if (mutation.data) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [mutation.data]);

  const numberRegistration = (name: keyof AnalysisFormInput) =>
    form.register(name, { setValueAs: parseLocalizedNumber });

  return (
    <div className="space-y-7">
      <form
        className="space-y-6"
        onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        noValidate
      >
        <div className="flex flex-col justify-between gap-4 rounded-lg border border-signal-warning/30 bg-signal-warning/10 p-4 sm:flex-row sm:items-center">
          <div>
            <Badge variant="warning">Exemplo sintético carregado</Badge>
            <p className="mt-2 text-sm text-signal-warning-foreground">
              Edite os valores ou use o caso demonstrativo para testar o fluxo ponta a ponta.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              form.reset(syntheticAnalysisExample);
              mutation.reset();
            }}
          >
            <RotateCcw aria-hidden="true" />
            Restaurar exemplo
          </Button>
        </div>

        <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
          <div className="border-b border-border pb-5">
            <p className="eyebrow">Etapa 01</p>
            <h2 className="mt-2 text-xl font-semibold">Identificação da oportunidade</h2>
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <div>
              <label className="form-label" htmlFor="name">Nome da oportunidade</label>
              <input className="form-input" id="name" {...form.register("name")} aria-invalid={Boolean(form.formState.errors.name)} />
              <FieldMessage error={form.formState.errors.name} />
            </div>
            <div>
              <label className="form-label" htmlFor="category">Categoria</label>
              <input className="form-input" id="category" {...form.register("category")} aria-invalid={Boolean(form.formState.errors.category)} />
              <FieldMessage error={form.formState.errors.category} />
            </div>
            <div className="sm:col-span-2">
              <label className="form-label" htmlFor="description">Descrição</label>
              <textarea className="form-input min-h-24 resize-y" id="description" {...form.register("description")} />
              <FieldMessage error={form.formState.errors.description} />
            </div>
            <div className="sm:col-span-2">
              <label className="form-label" htmlFor="sourceUrl">Fonte principal (opcional)</label>
              <input className="form-input" id="sourceUrl" type="url" placeholder="https://..." {...form.register("sourceUrl")} aria-invalid={Boolean(form.formState.errors.sourceUrl)} />
              <FieldMessage error={form.formState.errors.sourceUrl} />
            </div>
            <div>
              <label className="form-label" htmlFor="businessModel">Modelo de negócio</label>
              <select className="form-input" id="businessModel" {...form.register("businessModel")}>
                <option value="ecommerce">E-commerce</option>
                <option value="dropshipping">Dropshipping</option>
                <option value="marketplace">Marketplace</option>
                <option value="infoproduct">Infoproduto</option>
                <option value="affiliate">Afiliado</option>
              </select>
            </div>
            <div>
              <label className="form-label" htmlFor="primaryChannel">Canal principal</label>
              <select className="form-input" id="primaryChannel" {...form.register("primaryChannel")}>
                <option value="meta">Meta Ads</option>
                <option value="tiktok">TikTok</option>
                <option value="google">Google</option>
                <option value="organic">Orgânico</option>
                <option value="marketplace">Marketplace</option>
                <option value="mixed">Misto</option>
              </select>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
          <div className="border-b border-border pb-5">
            <p className="eyebrow">Etapa 02</p>
            <h2 className="mt-2 text-xl font-semibold">Economia e capacidade de teste</h2>
            <p className="mt-2 text-sm text-muted-foreground">Valores declarados em BRL. O core calcula margem e filtros eliminatórios.</p>
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["sellingPrice", "Preço de venda"],
              ["productCost", "Custo do produto"],
              ["variableFees", "Taxas variáveis"],
              ["taxes", "Tributos"],
              ["shippingSubsidy", "Subsídio de frete"],
              ["otherVariableCosts", "Outros custos"],
              ["minimumTestCost", "Custo mínimo do teste"],
              ["testBudget", "Orçamento disponível"],
            ].map(([name, label]) => (
              <div key={name}>
                <label className="form-label" htmlFor={name}>{label}</label>
                <input className="form-input font-mono" id={name} type="text" inputMode="decimal" {...numberRegistration(name as keyof AnalysisFormInput)} />
                <FieldMessage error={form.formState.errors[name as keyof AnalysisFormInput] as FieldError | undefined} />
              </div>
            ))}
            <div>
              <label className="form-label" htmlFor="maximumTestDays">Janela máxima (dias)</label>
              <input className="form-input font-mono" id="maximumTestDays" type="number" min="1" max="365" {...numberRegistration("maximumTestDays")} />
              <FieldMessage error={form.formState.errors.maximumTestDays as FieldError | undefined} />
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 sm:p-6">
          <div className="border-b border-border pb-5">
            <p className="eyebrow">Etapa 03</p>
            <h2 className="mt-2 text-xl font-semibold">Sinais normalizados</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Informe avaliações de 0 a 100 provenientes da sua coleta. O navegador não estima esses valores.
            </p>
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["demandScore", "Demanda"],
              ["economicsScore", "Economia"],
              ["competitiveScore", "Atratividade competitiva"],
            ].map(([name, label]) => (
              <div key={name}>
                <label className="form-label" htmlFor={name}>{label}</label>
                <input className="form-input font-mono" id={name} type="number" min="0" max="100" {...numberRegistration(name as keyof AnalysisFormInput)} />
                <FieldMessage error={form.formState.errors[name as keyof AnalysisFormInput] as FieldError | undefined} />
              </div>
            ))}
            <div>
              <label className="form-label" htmlFor="operationalFit">Fit operacional</label>
              <select className="form-input" id="operationalFit" {...form.register("operationalFit")}>
                <option value="strong_fit">Forte</option>
                <option value="acceptable_fit">Aceitável</option>
                <option value="conditional_fit">Condicional</option>
                <option value="poor_fit">Fraco</option>
                <option value="unknown">Desconhecido</option>
              </select>
            </div>
          </div>
        </section>

        {mutation.error ? (
          <div className="rounded-lg border border-red-900/20 bg-red-50 p-4 text-sm text-red-800" role="alert">
            <p className="font-semibold">A análise não foi concluída</p>
            <p className="mt-1">{mutation.error.message}</p>
          </div>
        ) : null}

        <div className="flex flex-col justify-between gap-4 rounded-lg bg-primary p-5 text-primary-foreground sm:flex-row sm:items-center">
          <div>
            <p className="font-semibold">Pronto para consultar o motor determinístico?</p>
            <p className="mt-1 text-sm text-primary-foreground/65">Nenhuma pontuação oficial é calculada nesta página.</p>
          </div>
          <Button type="submit" variant="inverse" size="lg" disabled={mutation.isPending}>
            {mutation.isPending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <FlaskConical aria-hidden="true" />}
            {mutation.isPending ? "Analisando..." : "Executar análise"}
            {!mutation.isPending ? <ArrowRight aria-hidden="true" /> : null}
          </Button>
        </div>
      </form>

      <div ref={resultRef}>{mutation.data ? <AnalysisResult result={mutation.data} /> : null}</div>
    </div>
  );
}
