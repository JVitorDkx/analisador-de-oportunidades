"use client";

import { useActionState } from "react";
import { ArrowRight, LoaderCircle } from "lucide-react";

import type { AuthActionState } from "@/app/(auth)/actions";
import { Button } from "@/components/ui/button";

type AuthFormProps = {
  action: (state: AuthActionState, formData: FormData) => Promise<AuthActionState>;
  mode: "login" | "register";
};

export function AuthForm({ action, mode }: AuthFormProps) {
  const [state, formAction, pending] = useActionState(action, {});
  const isRegister = mode === "register";

  return (
    <form action={formAction} className="mt-8 space-y-5">
      {isRegister ? (
        <div>
          <label className="form-label" htmlFor="displayName">
            Nome
          </label>
          <input
            className="form-input"
            id="displayName"
            name="displayName"
            type="text"
            autoComplete="name"
            minLength={2}
            maxLength={128}
            required
          />
        </div>
      ) : null}
      <div>
        <label className="form-label" htmlFor="email">
          E-mail
        </label>
        <input
          className="form-input"
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
        />
      </div>
      <div>
        <label className="form-label" htmlFor="password">
          Senha
        </label>
        <input
          className="form-input"
          id="password"
          name="password"
          type="password"
          autoComplete={isRegister ? "new-password" : "current-password"}
          minLength={8}
          maxLength={128}
          required
        />
        {isRegister ? (
          <p className="mt-2 text-xs text-muted-foreground">Use pelo menos 8 caracteres.</p>
        ) : null}
      </div>

      {state.error ? (
        <p className="rounded-md border border-red-900/20 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {state.error}
        </p>
      ) : null}
      {state.message ? (
        <p className="rounded-md border border-signal-positive/20 bg-signal-positive/10 px-3 py-2 text-sm text-signal-positive" role="status">
          {state.message}
        </p>
      ) : null}

      <Button className="w-full" type="submit" disabled={pending}>
        {pending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
        {isRegister ? "Criar conta" : "Entrar"}
        {!pending ? <ArrowRight aria-hidden="true" /> : null}
      </Button>
    </form>
  );
}
