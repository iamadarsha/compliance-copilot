import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance Copilot",
  description: "RAG assistant for SEBI/NSE/MCX compliance documents",
};

// Matches the dark theme's page background (--color-surface-0 in globals.css),
// tinting mobile browser chrome (Safari/Chrome address bar) to match rather
// than showing a default white bar around a dark page.
export const viewport: Viewport = {
  themeColor: "#09090b",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* Background/text color come from globals.css's body rule, which is
          unlayered CSS and so always wins over Tailwind's layered utility
          classes regardless of specificity — intentionally not duplicated
          here via background/text-color utility classes, which would just
          be dead, and in this case actively misleading (light-theme
          classes), code. */}
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
