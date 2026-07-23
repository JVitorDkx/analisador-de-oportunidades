import Link from "next/link";
import { ArrowRight, Building2, Layers3, LogOut, ShieldCheck } from "lucide-react";
import { redirect } from "next/navigation";

import { selectWorkspaceAction } from "@/app/workspace/actions";
import { Button } from "@/components/ui/button";
import { CreateWorkspaceForm } from "@/components/workspace/create-workspace-form";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

type Workspace = {
  created_at: string;
  id: string;
  name: string;
};

export default async function WorkspacePage() {
  const isConfigured = Boolean(getSupabaseConfig());
  let workspaces: Workspace[] = [];
  let email = "ambiente local";

  if (isConfigured) {
    const supabase = await createClient();
    const { data: claimsData } = await supabase.auth.getClaims();
    const claims = claimsData?.claims;
    if (!claims) {
      redirect("/login");
    }

    email = typeof claims.email === "string" ? claims.email : "usuário autenticado";
    const { data } = await supabase
      .from("tenants")
      .select("id,name,created_at")
      .order("created_at", { ascending: true });
    workspaces = (data ?? []) as Workspace[];
  }

  return (
    <main className="min-h-svh bg-background px-4 py-8 sm:px-8 lg:py-12">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-center">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid size-10 place-items-center rounded-md bg-primary text-primary-foreground">
              <Layers3 className="size-5" aria-hidden="true" />
            </span>
            <div>
              <p className="font-semibold">Opportunity Desk</p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Seleção de contexto</p>
            </div>
          </Link>
          {isConfigured ? (
            <form action="/auth/signout" method="post">
              <Button type="submit" variant="outline" size="sm">
                <LogOut aria-hidden="true" />
                Sair
              </Button>
            </form>
          ) : (
            <Button asChild variant="outline" size="sm">
              <Link href="/login">Configurar acesso</Link>
            </Button>
          )}
        </header>

        <div className="mt-10 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <section>
            <p className="eyebrow">Workspace / Tenant</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em]">Escolha sua mesa de trabalho</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              Cada workspace define uma fronteira isolada de projetos, análises e assinatura. Sua identidade precisa possuir participação válida no banco.
            </p>

            <div className="mt-8 space-y-3">
              {workspaces.map((workspace) => (
                <form action={selectWorkspaceAction} key={workspace.id}>
                  <input type="hidden" name="tenantId" value={workspace.id} />
                  <button
                    className="group flex w-full items-center gap-4 rounded-lg border border-border bg-card p-5 text-left transition-colors hover:border-foreground/30 hover:bg-muted"
                    type="submit"
                  >
                    <span className="grid size-11 place-items-center rounded-md bg-primary text-primary-foreground">
                      <Building2 className="size-5" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold">{workspace.name}</span>
                      <span className="mt-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                        Tenant verificado por RLS
                      </span>
                    </span>
                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" aria-hidden="true" />
                  </button>
                </form>
              ))}

              {workspaces.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-card p-6">
                  <p className="font-semibold">
                    {isConfigured ? "Nenhum workspace disponível" : "Supabase ainda não configurado"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {isConfigured
                      ? "Crie o primeiro workspace abaixo. A associação de proprietário será registrada automaticamente."
                      : "A interface está pronta para receber as variáveis públicas do projeto. Nenhum tenant fictício foi criado para esta prévia."}
                  </p>
                </div>
              ) : null}
            </div>

            <div className="mt-8 rounded-lg border border-border bg-card p-5">
              <p className="font-semibold">Novo workspace</p>
              <p className="mt-1 text-sm text-muted-foreground">
                O usuário autenticado será o proprietário e o RLS criará a associação inicial.
              </p>
              <CreateWorkspaceForm />
            </div>
          </section>

          <aside className="h-fit rounded-lg bg-primary p-6 text-primary-foreground">
            <ShieldCheck className="size-5 text-sidebar-primary" aria-hidden="true" />
            <p className="mt-6 font-mono text-[10px] uppercase tracking-[0.18em] text-primary-foreground/55">
              Identidade atual
            </p>
            <p className="mt-2 break-all font-semibold">{email}</p>
            <div className="my-6 h-px bg-primary-foreground/15" />
            <ul className="space-y-3 text-sm leading-5 text-primary-foreground/70">
              <li>JWT verificado com getClaims()</li>
              <li>Tenant revalidado antes da seleção</li>
              <li>Cookie HTTP-only não concede autorização</li>
              <li>Consultas protegidas no PostgreSQL por RLS</li>
            </ul>
          </aside>
        </div>
      </div>
    </main>
  );
}
