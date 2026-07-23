import { z } from "zod";

export const loginSchema = z
  .object({
    email: z.email("Informe um e-mail válido."),
    password: z.string().min(8, "A senha deve ter pelo menos 8 caracteres.").max(128),
  })
  .strict();

export const registerSchema = loginSchema
  .extend({
    displayName: z.string().trim().min(2, "Informe seu nome.").max(128),
  })
  .strict();

export const workspaceSchema = z
  .object({
    name: z.string().trim().min(2, "Informe um nome para o workspace.").max(128),
  })
  .strict();

export const tenantSelectionSchema = z
  .object({
    tenantId: z.uuid("Workspace inválido."),
  })
  .strict();
