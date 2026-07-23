import { z } from "zod";

const optionalSourceUrl = z
  .string()
  .trim()
  .max(2048)
  .refine((value) => value === "" || z.url().safeParse(value).success, "Informe uma URL válida.");

export const analysisFormSchema = z
  .object({
    name: z.string().trim().min(3, "Informe o nome da oportunidade.").max(128),
    category: z.string().trim().min(2, "Informe a categoria.").max(128),
    description: z.string().trim().max(1000),
    sourceUrl: optionalSourceUrl,
    businessModel: z.enum(["ecommerce", "dropshipping", "marketplace", "infoproduct", "affiliate"]),
    primaryChannel: z.enum(["meta", "tiktok", "google", "organic", "marketplace", "mixed"]),
    sellingPrice: z.number().positive("O preço precisa ser maior que zero.").max(10_000_000),
    productCost: z.number().min(0).max(10_000_000),
    variableFees: z.number().min(0).max(10_000_000),
    taxes: z.number().min(0).max(10_000_000),
    shippingSubsidy: z.number().min(0).max(10_000_000),
    otherVariableCosts: z.number().min(0).max(10_000_000),
    minimumTestCost: z.number().min(0).max(10_000_000),
    testBudget: z.number().positive("Informe um orçamento maior que zero.").max(10_000_000),
    maximumTestDays: z.number().int().min(1).max(365),
    demandScore: z.number().min(0).max(100),
    economicsScore: z.number().min(0).max(100),
    competitiveScore: z.number().min(0).max(100),
    operationalFit: z.enum(["strong_fit", "acceptable_fit", "conditional_fit", "poor_fit", "unknown"]),
  })
  .strict();

export type AnalysisFormValues = z.infer<typeof analysisFormSchema>;

export const syntheticAnalysisExample: AnalysisFormValues = {
  name: "Organizador modular demonstrativo",
  category: "Casa e organização",
  description: "Exemplo sintético para validar o fluxo completo da interface.",
  sourceUrl: "",
  businessModel: "ecommerce",
  primaryChannel: "meta",
  sellingPrice: 149.9,
  productCost: 35,
  variableFees: 15,
  taxes: 12,
  shippingSubsidy: 10,
  otherVariableCosts: 5,
  minimumTestCost: 400,
  testBudget: 1000,
  maximumTestDays: 7,
  demandScore: 92,
  economicsScore: 88,
  competitiveScore: 82,
  operationalFit: "strong_fit",
};
