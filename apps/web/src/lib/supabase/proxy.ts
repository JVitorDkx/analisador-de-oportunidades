import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { getSupabaseConfig } from "./config";

const AUTH_PATHS = new Set(["/login", "/register"]);
const PROTECTED_PREFIXES = ["/workspace", "/analysis"];

export async function updateSession(request: NextRequest) {
  const config = getSupabaseConfig();
  if (!config) {
    return NextResponse.next({ request });
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(config.url, config.publishableKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  const { data: claimsData } = await supabase.auth.getClaims();
  const claims = claimsData?.claims;
  const pathname = request.nextUrl.pathname;
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (!claims && isProtected) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (claims && AUTH_PATHS.has(pathname)) {
    const workspaceUrl = request.nextUrl.clone();
    workspaceUrl.pathname = "/workspace";
    workspaceUrl.search = "";
    return NextResponse.redirect(workspaceUrl);
  }

  return response;
}
