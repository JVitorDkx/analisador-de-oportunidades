import { z } from "zod";

export function parseLocalizedNumber(value: unknown): unknown {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value !== "string") {
    return value;
  }
  const compact = value.trim().replace(/\s/g, "");
  if (compact === "") {
    return undefined;
  }
  const comma = compact.lastIndexOf(",");
  const point = compact.lastIndexOf(".");
  let normalized = compact;
  if (comma >= 0 && point >= 0) {
    const decimalSeparator = comma > point ? "," : ".";
    const thousandsSeparator = decimalSeparator === "," ? "." : ",";
    normalized = compact.split(thousandsSeparator).join("").replace(decimalSeparator, ".");
  } else if (comma >= 0) {
    normalized = compact.replace(",", ".");
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : value;
}

const localizedNumber = z.preprocess(parseLocalizedNumber, z.number());

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
    sellingPrice: localizedNumber.pipe(z.number().positive("O preço precisa ser maior que zero.").max(10_000_000)),
    productCost: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    variableFees: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    taxes: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    shippingSubsidy: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    otherVariableCosts: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    minimumTestCost: localizedNumber.pipe(z.number().min(0).max(10_000_000)),
    testBudget: localizedNumber.pipe(z.number().positive("Informe um orçamento maior que zero.").max(10_000_000)),
    maximumTestDays: localizedNumber.pipe(z.number().int().min(1).max(365)),
    demandScore: localizedNumber.pipe(z.number().min(0).max(100)),
    economicsScore: localizedNumber.pipe(z.number().min(0).max(100)),
    competitiveScore: localizedNumber.pipe(z.number().min(0).max(100)),
    operationalFit: z.enum(["strong_fit", "acceptable_fit", "conditional_fit", "poor_fit", "unknown"]),
  })
  .strict();

export type AnalysisFormInput = z.input<typeof analysisFormSchema>;
export type AnalysisFormValues = z.output<typeof analysisFormSchema>;

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
