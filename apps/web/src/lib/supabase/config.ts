export type SupabasePublicConfig = {
  publishableKey: string;
  url: string;
};

type SupabaseConfigInput = {
  publishableKey?: string;
  url?: string;
};

const PLACEHOLDER_MARKERS = ["your-", "example", "project-ref"];

export function parseSupabaseConfig(input: SupabaseConfigInput): SupabasePublicConfig | null {
  const url = input.url?.trim();
  const publishableKey = input.publishableKey?.trim();

  if (!url || !publishableKey) {
    return null;
  }

  if (PLACEHOLDER_MARKERS.some((marker) => url.includes(marker) || publishableKey.includes(marker))) {
    return null;
  }

  try {
    const parsedUrl = new URL(url);
    const isLocal = parsedUrl.hostname === "127.0.0.1" || parsedUrl.hostname === "localhost";
    if (parsedUrl.protocol !== "https:" && !(isLocal && parsedUrl.protocol === "http:")) {
      return null;
    }
  } catch {
    return null;
  }

  return { publishableKey, url };
}

export function getSupabaseConfig(): SupabasePublicConfig | null {
  return parseSupabaseConfig({
    url: process.env.NEXT_PUBLIC_SUPABASE_URL,
    publishableKey: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  });
}
