import { NextRequest, NextResponse } from "next/server";

const FLOCK_API_URL = process.env.FLOCK_API_URL || "http://127.0.0.1:8000";
const APP_NAME = "app";

type AdkEvent = {
  content?: { parts?: Array<{ text?: string }> };
};

export async function POST(req: NextRequest) {
  const { message } = (await req.json()) as { message?: string };
  if (!message?.trim()) {
    return NextResponse.json({ error: "message required" }, { status: 400 });
  }

  const userId = "mission-control";
  const sessionRes = await fetch(
    `${FLOCK_API_URL}/apps/${APP_NAME}/users/${userId}/sessions`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ state: {} }),
    },
  );
  if (!sessionRes.ok) {
    const detail = await sessionRes.text();
    return NextResponse.json(
      { error: `session failed: ${sessionRes.status} ${detail}` },
      { status: 502 },
    );
  }
  const session = (await sessionRes.json()) as { id: string };

  const runRes = await fetch(`${FLOCK_API_URL}/run_sse`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      app_name: APP_NAME,
      user_id: userId,
      session_id: session.id,
      new_message: { role: "user", parts: [{ text: message }] },
      streaming: false,
    }),
  });
  if (!runRes.ok) {
    const detail = await runRes.text();
    return NextResponse.json(
      { error: `run failed: ${runRes.status} ${detail}` },
      { status: 502 },
    );
  }

  const raw = await runRes.text();
  const texts: string[] = [];
  for (const line of raw.split("\n")) {
    if (!line.startsWith("data: ")) continue;
    try {
      const event = JSON.parse(line.slice(6)) as AdkEvent;
      for (const part of event.content?.parts || []) {
        if (part.text) texts.push(part.text);
      }
    } catch {
      // ignore keep-alives
    }
  }

  return NextResponse.json({ text: texts.join("\n").trim() || raw });
}
