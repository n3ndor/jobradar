import { ImageResponse } from "next/og";

export const alt = "JobRadar — automated tech job market intelligence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#070b0f",
          padding: "72px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <svg width="56" height="56" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="13" stroke="#3ddc97" strokeOpacity="0.3" strokeWidth="1.6" />
            <circle cx="16" cy="16" r="7.5" stroke="#3ddc97" strokeOpacity="0.55" strokeWidth="1.6" />
            <circle cx="16" cy="16" r="2.2" fill="#3ddc97" />
            <path d="M16 16 L26 8" stroke="#3ddc97" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <div style={{ display: "flex", fontSize: 34, color: "#dce5ec", fontWeight: 600 }}>
            <span>job</span>
            <span style={{ color: "#3ddc97" }}>radar</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ fontSize: 68, color: "#dce5ec", fontWeight: 700, lineHeight: 1.05, maxWidth: 900 }}>
            Automated tech job market intelligence
          </div>
          <div style={{ fontSize: 30, color: "#7d8f9e", maxWidth: 860, lineHeight: 1.3 }}>
            Postings from public APIs, deduplicated and enriched into filterable,
            structured market data. Refreshed every 6 hours.
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          {["Python pipeline", "Next.js dashboard", "LLM enrichment", "GitHub Actions cron"].map(
            (chip) => (
              <div
                key={chip}
                style={{
                  fontSize: 22,
                  color: "#3ddc97",
                  border: "1px solid #2a3945",
                  borderRadius: 8,
                  padding: "8px 16px",
                }}
              >
                {chip}
              </div>
            ),
          )}
        </div>
      </div>
    ),
    { ...size },
  );
}
