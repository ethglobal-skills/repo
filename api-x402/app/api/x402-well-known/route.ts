import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    version: 1,
    resources: [
      'POST /api/events',
      'POST /api/sponsors',
      'POST /api/prizes',
      'POST /api/projects',
    ],
  })
}
