import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    version: 1,
    resources: [
      'GET /api/sponsors',
      'GET /api/events',
      'GET /api/prizes',
      'GET /api/projects',
    ],
  })
}
