"use client";

import { useEffect, useState } from "react";

type Summary = {
  id: string;
  status?: string;
  updatedAt?: string;
  landingPath?: string;
  brief?: { businessName?: string; geo?: string };
};

type Receipt = { step?: string; status?: string; engine?: string };

export default function CampaignsPage() {
  const [rows, setRows] = useState<Summary[]>([]);
  const [detail, setDetail] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/campaigns")
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body.error || res.statusText);
        setRows(body.campaigns || []);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function openOne(id: string) {
    const res = await fetch(`/api/campaigns/${id}`);
    const body = await res.json();
    const rec = ((body.receipts || []) as Receipt[])
      .map((r) => `${r.step}:${r.status}`)
      .join(" → ");
    setDetail(
      `${rec}\n\n${JSON.stringify({ status: body.status, landingPath: body.landingPath, engineConfig: body.engineConfig }, null, 2)}`,
    );
  }

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "36px 20px" }}>
      <p style={{ letterSpacing: "0.18em", fontSize: 12, color: "#c4a574" }}>
        RECEIPTS LEDGER
      </p>
      <h1 style={{ fontSize: 32, fontWeight: 600 }}>Every hop on the record</h1>
      <p style={{ color: "#c9c2b6", maxWidth: 640, lineHeight: 1.5 }}>
        Campaigns from Firestore. The Cloud Run <code>/console</code> page is
        the same ledger if you do not run this Next app.
      </p>
      {error && <p style={{ color: "#e08a8a" }}>{error}</p>}
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 24 }}>
        <thead>
          <tr>
            {["Campaign", "Status", "Updated", ""].map((h) => (
              <th
                key={h}
                style={{
                  textAlign: "left",
                  borderBottom: "1px solid #2a333d",
                  padding: "10px 6px",
                  color: "#8b8378",
                  fontWeight: 500,
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id}>
              <td style={{ padding: "12px 6px" }}>
                <button
                  onClick={() => openOne(c.id)}
                  style={{
                    background: "none",
                    border: 0,
                    color: "#c4a574",
                    cursor: "pointer",
                    padding: 0,
                    font: "inherit",
                  }}
                >
                  {c.brief?.businessName || c.id}
                </button>
                <div style={{ color: "#8b8378", fontSize: 12 }}>{c.id}</div>
              </td>
              <td style={{ padding: "12px 6px", letterSpacing: "0.08em", fontSize: 12 }}>
                {(c.status || "").toUpperCase()}
              </td>
              <td style={{ padding: "12px 6px", color: "#8b8378", fontSize: 13 }}>
                {(c.updatedAt || "").slice(0, 19)}
              </td>
              <td style={{ padding: "12px 6px" }}>
                {c.landingPath ? (
                  <a href={(process.env.NEXT_PUBLIC_FLOCK_API_URL || "") + c.landingPath} style={{ color: "#c4a574" }}>
                    landing
                  </a>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {detail && (
        <pre
          style={{
            marginTop: 28,
            whiteSpace: "pre-wrap",
            background: "#151b22",
            border: "1px solid #2a333d",
            borderRadius: 12,
            padding: 16,
            lineHeight: 1.5,
          }}
        >
          {detail}
        </pre>
      )}
    </main>
  );
}
