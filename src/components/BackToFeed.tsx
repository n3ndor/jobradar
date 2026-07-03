"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

/**
 * Goes back in history when the visitor came from within the site, so feed
 * filters and scroll position survive. Falls back to a plain link to the feed
 * for direct visits (shared/bookmarked job links).
 */
export function BackToFeed() {
  const router = useRouter();

  return (
    <Link
      href="/"
      className="text-muted hover:text-foreground"
      onClick={(event) => {
        if (
          window.history.length > 1 &&
          document.referrer.startsWith(window.location.origin)
        ) {
          event.preventDefault();
          router.back();
        }
      }}
    >
      ← Back to feed
    </Link>
  );
}
