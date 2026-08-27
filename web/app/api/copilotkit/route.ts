import { NextResponse } from "next/server";

/**
 * CopilotKit / AG-UI runtime stub.
 *
 * Day-1 Mission Control talks to Flo through /api/chat → ADK /run_sse.
 * This route is the placeholder for the CopilotKit runtime that will wrap
 * the same Cloud Run service over AG-UI once the chat path is proven.
 */
export async function POST() {
  return NextResponse.json(
    {
      error: "CopilotKit AG-UI runtime not wired yet",
      use: "/api/chat",
    },
    { status: 501 },
  );
}
