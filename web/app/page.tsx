"use client";

import { FormEvent, useState } from "react";

type Turn = { role: "you" | "flo"; text: string };

export default function Page() {
  const [input, setInput] = useState(
    "I run FitNorth, a gym in Sector 56 Gurgaon. I want 50 evening memberships from working professionals within 7 km by 30 September. Budget ₹50,000.",
  );
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    setTurns((prev) => [...prev, { role: "you", text }]);
    setInput("");
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.error || `HTTP ${response.status}`);
      }
      setTurns((prev) => [...prev, { role: "flo", text: body.text }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "48px 20px" }}>
      <p style={{ letterSpacing: "0.18em", fontSize: 12, color: "#c4a574" }}>
        LEADSY FLOCK · MISSION CONTROL
      </p>
      <h1 style={{ fontSize: 36, fontWeight: 600, margin: "8px 0 12px" }}>
        Talk to Flo
      </h1>
      <p style={{ color: "#c9c2b6", lineHeight: 1.5, marginBottom: 28 }}>
        Talk to Flo, then watch receipts on the Campaigns tab (or
        <code> /console</code> on flock-api). The flock runs in the background
        after you approve a plan.
      </p>
      <div
        style={{
          border: "1px solid #2a333d",
          borderRadius: 16,
          padding: 16,
          minHeight: 280,
          background: "#151b22",
        }}
      >
        {turns.length === 0 && (
          <p style={{ color: "#8b8378" }}>
            Send a brief. Flo will ask only for what is missing.
          </p>
        )}
        {turns.map((turn, i) => (
          <article key={i} style={{ marginBottom: 16 }}>
            <div
              style={{
                fontSize: 11,
                letterSpacing: "0.12em",
                color: turn.role === "flo" ? "#c4a574" : "#8b8378",
              }}
            >
              {turn.role === "flo" ? "FLO" : "YOU"}
            </div>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
                margin: "6px 0 0",
                lineHeight: 1.55,
              }}
            >
              {turn.text}
            </pre>
          </article>
        ))}
        {busy && <p style={{ color: "#c4a574" }}>Flo is reading the brief…</p>}
        {error && <p style={{ color: "#e08a8a" }}>{error}</p>}
      </div>
      <form onSubmit={onSubmit} style={{ marginTop: 16, display: "grid", gap: 10 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={4}
          style={{
            width: "100%",
            resize: "vertical",
            background: "#151b22",
            color: "#f4efe6",
            border: "1px solid #2a333d",
            borderRadius: 12,
            padding: 12,
            font: "inherit",
          }}
        />
        <button
          type="submit"
          disabled={busy}
          style={{
            justifySelf: "start",
            background: "#c4a574",
            color: "#0f1419",
            border: 0,
            borderRadius: 999,
            padding: "10px 18px",
            fontWeight: 600,
            cursor: busy ? "wait" : "pointer",
          }}
        >
          Send to Flo
        </button>
      </form>
    </main>
  );
}
