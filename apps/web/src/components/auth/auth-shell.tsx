import Link from "next/link";
import { Layers3, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

export function AuthShell({
  children,
  description,
  eyebrow,
  title,
}: {
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <main className="grid min-h-svh bg-background lg:grid-cols-[0.9fr_1.1fr]">
      <section className="hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col">
        <Link className="flex items-center gap-3" href="/">
          <span className="grid size-10 place-items-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <Layers3 className="size-5" aria-hidden="true" />
          </span>
          <span className="font-semibold">Opportunity Desk</span>
        </Link>
        <div className="my-auto max-w-lg">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary-foreground/55">
            Acesso à mesa
          </p>
          <p className="mt-6 text-4xl font-semibold leading-tight tracking-[-0.035em]">
            Decisões auditáveis começam com uma fronteira confiável.
          </p>
          <div className="mt-10 flex items-center gap-3 border-t border-primary-foreground/15 pt-5 text-sm text-primary-foreground/65">
            <ShieldCheck className="size-4" aria-hidden="true" />
            Sessão SSR, JWT verificado e isolamento por tenant
          </div>
        </div>
      </section>
      <section className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between lg:hidden">
            <Link className="flex items-center gap-2 font-semibold" href="/">
              <Layers3 className="size-5" aria-hidden="true" />
              Opportunity Desk
            </Link>
            <Badge variant="outline">Acesso seguro</Badge>
          </div>
          <p className="eyebrow mt-14 lg:mt-0">{eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em]">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
          {children}
        </div>
      </section>
    </main>
  );
}
