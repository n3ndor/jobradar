import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "JobRadar",
    template: "%s | JobRadar",
  },
  description:
    "Automated job-market intelligence. Remote postings from public APIs, enriched with AI into structured, filterable market data.",
};

function RadarMark() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="size-5 text-accent"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      <circle cx="12" cy="12" r="9.5" opacity="0.35" />
      <circle cx="12" cy="12" r="5.5" opacity="0.55" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <path d="M12 12 L19.5 6.5" strokeLinecap="round" />
    </svg>
  );
}

const NAV = [
  { href: "/", label: "Feed", live: true },
  { href: "/trends", label: "Trends", live: false },
  { href: "/pipeline", label: "Pipeline", live: false },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-accent focus:px-3 focus:py-2 focus:text-background focus:text-sm focus:font-medium"
        >
          Skip to content
        </a>

        <header className="border-b border-border">
          <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-4">
            <Link
              href="/"
              className="flex items-center gap-2 font-mono text-sm font-semibold tracking-wide"
            >
              <RadarMark />
              <span>
                job<span className="text-accent">radar</span>
              </span>
            </Link>
            <nav aria-label="Main" className="flex items-center gap-1 text-sm">
              {NAV.map((item) =>
                item.live ? (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded px-3 py-1.5 text-muted transition-colors hover:bg-surface-raised hover:text-foreground"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span
                    key={item.href}
                    className="flex items-center gap-1.5 rounded px-3 py-1.5 text-faint"
                    title="Coming soon"
                  >
                    {item.label}
                    <span className="rounded-sm border border-border px-1 font-mono text-[10px] uppercase tracking-wider">
                      soon
                    </span>
                  </span>
                ),
              )}
            </nav>
          </div>
        </header>

        <div className="flex-1">{children}</div>

        <footer className="border-t border-border">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-5 text-xs text-faint">
            <p>
              Data from public APIs: Remotive, Arbeitnow. Refreshed every 6 hours
              by an automated pipeline.
            </p>
            <p>
              <a
                href="https://github.com/n3ndor/jobradar"
                className="underline decoration-border-strong underline-offset-2 transition-colors hover:text-muted"
              >
                Source on GitHub
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
