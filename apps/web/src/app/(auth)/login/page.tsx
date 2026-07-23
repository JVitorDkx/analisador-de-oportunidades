import Link from "next/link";

import { loginAction } from "@/app/(auth)/actions";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export default function LoginPage() {
  return (
    <AuthShell
      eyebrow="Bem-vindo de volta"
      title="Entre na sua mesa"
      description="Acesse os workspaces em que sua identidade possui participação confirmada."
    >
      <AuthForm action={loginAction} mode="login" />
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Ainda não possui conta?{" "}
        <Link className="font-semibold text-foreground underline-offset-4 hover:underline" href="/register">
          Criar acesso
        </Link>
      </p>
    </AuthShell>
  );
}
