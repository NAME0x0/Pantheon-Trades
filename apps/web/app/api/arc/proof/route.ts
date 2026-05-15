import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    { error: "Not implemented in static demo. Run the FastAPI gateway." },
    { status: 501 }
  );
}
