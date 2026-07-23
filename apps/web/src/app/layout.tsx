import type { Metadata } from "next";

import "@fontsource-variable/source-sans-3";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Opportunity Desk",
  description: "Mesa de inteligência para análise determinística de oportunidades.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
