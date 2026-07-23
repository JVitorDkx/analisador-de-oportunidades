import { analyzeOpportunity } from "@opportunity-analyzer/typescript-sdk";
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import { buildAnalyzeRequest } from "@/lib/analysis/payload";
import { analysisFormSchema } from "@/lib/analysis/schema";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

function problem(status: number, title: string, detail: string) {
  return NextResponse.json(
    {
      type: `https://opportunity.local/problems/web-${status}`,
      title,
      status,
      detail,
      instance: "/api/analysis",
    },
    { status, headers: { "Content-Type": "application/problem+json" } },
  );
}

export async function POST(request: NextRequest) {
  let input: unknown;
  try {
    input = await request.json();
  } catch {
    return problem(400, "Corpo inválido", "A requisição precisa conter um objeto JSON válido.");
  }

  const parsed = analysisFormSchema.safeParse(input);
  if (!parsed.success) {
    return NextResponse.json(
      {
        type: "https://opportunity.local/problems/web-validation",
        title: "Entrada inválida",
        status: 422,
        detail: "Revise os campos do formulário.",
        instance: "/api/analysis",
        errors: parsed.error.issues.map((issue) => ({
          pointer: `/${issue.path.join("/")}`,
          detail: issue.message,
          code: issue.code,
        })),
      },
      { status: 422, headers: { "Content-Type": "application/problem+json" } },
    );
  }

  const supabaseConfig = getSupabaseConfig();
  const forwardedHeaders: Record<string, string> = {};
  if (supabaseConfig) {
    const supabase = await createClient();
    const { data: claimsData } = await supabase.auth.getClaims();
    const claims = claimsData?.claims;
    const userId = typeof claims?.sub === "string" ? claims.sub : null;
    if (!userId) {
      return problem(401, "Autenticação necessária", "Entre novamente para executar a análise.");
    }

    const cookieStore = await cookies();
    const tenantId = cookieStore.get("od_tenant_id")?.value;
    if (!tenantId) {
      return problem(403, "Workspace necessário", "Selecione um workspace autorizado antes de analisar.");
    }

    const { data: membership } = await supabase
      .from("tenant_memberships")
      .select("tenant_id")
      .eq("tenant_id", tenantId)
      .eq("user_id", userId)
      .maybeSingle();
    if (!membership) {
      return problem(403, "Acesso negado", "O workspace selecionado não está disponível para esta identidade.");
    }

    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) {
      return problem(401, "Sessão indisponível", "Entre novamente para executar a análise.");
    }
    forwardedHeaders.Authorization = `Bearer ${session.access_token}`;
    forwardedHeaders["X-Tenant-ID"] = tenantId;
  } else if (process.env.NODE_ENV === "production") {
    return problem(503, "Autenticação não configurada", "A configuração do Supabase é obrigatória em produção.");
  }

  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  try {
    const result = await analyzeOpportunity({
      baseUrl: apiUrl,
      body: buildAnalyzeRequest(parsed.data),
      headers: forwardedHeaders,
    });
    if (result.error) {
      return NextResponse.json(result.error, {
        status: result.response?.status ?? 502,
        headers: { "Content-Type": result.response?.headers.get("content-type") ?? "application/problem+json" },
      });
    }
    if (!result.data) {
      return problem(502, "Resposta vazia", "A API não devolveu um relatório de análise.");
    }
    return NextResponse.json(result.data, {
      status: result.response?.status ?? 200,
      headers: {
        "X-Request-ID": result.response?.headers.get("x-request-id") ?? "",
      },
    });
  } catch {
    return problem(502, "API indisponível", "Não foi possível alcançar o motor de análise neste momento.");
  }
}
