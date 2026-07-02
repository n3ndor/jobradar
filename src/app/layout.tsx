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
  metadataBase: new URL("https://jobradar.nagysolution.com"),
  title: {
    default: "JobRadar — tech job market intelligence",
    template: "%s | JobRadar",
  },
  description:
    "Automated tech-job market intelligence. Engineering, data, design, and product roles from public APIs, enriched into structured, filterable market data.",
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
  { href: "/trends", label: "Trends", live: true },
  { href: "/pipeline", label: "Pipeline", live: true },
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
          <div className="mx-auto max-w-5xl px-4 pt-5">
            <p className="flex flex-wrap items-center gap-1.5 text-xs text-faint">
              <span className="font-mono uppercase tracking-wider">On the radar:</span>
              {[
                "Email digest",
                "Salary benchmarks by stack & region",
                "Company hiring velocity",
                "Ghost-job detector",
                "Public API",
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-border px-2 py-0.5 text-muted"
                >
                  {item}
                </span>
              ))}
            </p>
          </div>
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-5 text-xs text-faint">
            <p className="max-w-xl">
              Tech roles only: engineering, data, design, and product. Aggregated
              every 6 hours from{" "}
              <a href="https://remotive.com" className="hover:text-muted">Remotive</a>,{" "}
              <a href="https://www.arbeitnow.com" className="hover:text-muted">Arbeitnow</a>,{" "}
              <a href="https://boards.greenhouse.io" className="hover:text-muted">Greenhouse</a>,{" "}
              <a href="https://remoteok.com" className="hover:text-muted">RemoteOK</a>,{" "}
              <a href="https://weworkremotely.com" className="hover:text-muted">We Work Remotely</a>, and{" "}
              <a href="https://news.ycombinator.com" className="hover:text-muted">Hacker News</a>.
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
