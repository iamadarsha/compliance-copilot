import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Compliance Copilot",
  description: "RAG assistant for SEBI/NSE/MCX compliance documents",
};

// Matches the page canvas (--color-canvas in globals.css) so mobile browser
// chrome blends into the app rather than butting against it.
export const viewport: Viewport = {
  themeColor: "#f5f5f7",
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
