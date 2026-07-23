"use client";

import { useActionState } from "react";
import { LoaderCircle, Plus } from "lucide-react";

import {
  createWorkspaceAction,
  type WorkspaceActionState,
} from "@/app/workspace/actions";
import { Button } from "@/components/ui/button";

const initialState: WorkspaceActionState = {};

export function CreateWorkspaceForm() {
  const [state, formAction, pending] = useActionState(createWorkspaceAction, initialState);

  return (
    <form action={formAction} className="mt-5 flex flex-col gap-3 sm:flex-row">
      <div className="flex-1">
        <label className="sr-only" htmlFor="workspaceName">
          Nome do novo workspace
        </label>
        <input
          className="form-input"
          id="workspaceName"
          name="name"
          placeholder="Ex.: Operação Brasil"
          minLength={2}
          maxLength={128}
          required
        />
        {state.error ? (
          <p className="mt-2 text-xs text-red-800" role="alert">
            {state.error}
          </p>
        ) : null}
      </div>
      <Button type="submit" disabled={pending}>
        {pending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Plus aria-hidden="true" />}
        Criar workspace
      </Button>
    </form>
  );
}
