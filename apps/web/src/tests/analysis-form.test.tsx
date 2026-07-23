// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisForm } from "@/components/analysis/analysis-form";

const response = {
  analysis_id: "ANL-WEB-TEST",
  input_status: "sufficient",
  confidence: "high",
  recommendation: "prioritize_test",
  executive_summary: "A oportunidade pode avançar para um teste controlado.",
  next_experiment: { minimum_action: "Validar uma campanha pequena." },
  human_review: { required: false },
  missing_data: [],
  ranking: [
    {
      official_score: 90.4,
      strengths: [{ statement: "Economia saudável." }],
      risks: [],
    },
  ],
};

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AnalysisForm />
    </QueryClientProvider>,
  );
}

describe("interactive analysis form", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the synthetic example and renders the API diagnosis after submission", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => response,
    });
    vi.stubGlobal("fetch", fetchMock);
    Element.prototype.scrollIntoView = vi.fn();

    renderForm();

    expect(screen.getByLabelText("Nome da oportunidade")).toHaveValue(
      "Organizador modular demonstrativo",
    );
    fireEvent.change(screen.getByLabelText("Nome da oportunidade"), {
      target: { value: "Caso editado pelo usuário" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Executar análise" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("heading", { name: "Priorizar teste" })).toBeVisible();
    expect(screen.getByText("90.4")).toBeVisible();

    const submitted = JSON.parse(fetchMock.mock.calls[0]![1]!.body as string) as {
      name: string;
      official_score?: number;
    };
    expect(submitted.name).toBe("Caso editado pelo usuário");
    expect(submitted).not.toHaveProperty("official_score");
  });
});
