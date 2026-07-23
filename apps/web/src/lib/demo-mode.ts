type RuntimeEnvironment = Record<string, string | undefined>;

export function isDemoMode(environment: RuntimeEnvironment = process.env): boolean {
  const runtime =
    environment.APP_ENV ?? environment.VERCEL_ENV ?? environment.NODE_ENV ?? "development";
  if (runtime.toLowerCase() === "production" || runtime.toLowerCase() === "prod") {
    return false;
  }
  return environment.ENABLE_DEMO_MODE?.trim().toLowerCase() === "true";
}
