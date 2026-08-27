import { NextResponse } from "next/server";

const FLOCK_API_URL = process.env.FLOCK_API_URL || "http://127.0.0.1:8000";

export async function GET() {
  const res = await fetch(`${FLOCK_API_URL}/v1/campaigns`, { cache: "no-store" });
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "content-type": "application/json" },
  });
}
