import { paymentProxy, x402ResourceServer } from '@x402/next'
import { ExactEvmScheme } from '@x402/evm/exact/server'
import { HTTPFacilitatorClient } from '@x402/core/server'
import { createFacilitatorConfig } from '@coinbase/x402'
import { NextRequest, NextResponse } from 'next/server'

const REQUESTS_PER_MINUTE = 10

// In-memory rate limit store — works for local testing only.
// Replace with Upstash Redis for production on Vercel (Edge functions don't share memory).
const ipRequests = new Map<string, { count: number; resetAt: number }>()

function getIp(req: NextRequest): string {
  return req.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    ?? req.headers.get('x-real-ip')
    ?? 'unknown'
}

function isRateLimited(ip: string): boolean {
  const now = Date.now()
  const entry = ipRequests.get(ip)

  if (!entry || now > entry.resetAt) {
    ipRequests.set(ip, { count: 1, resetAt: now + 60_000 })
    return false
  }

  if (entry.count >= REQUESTS_PER_MINUTE) return true

  entry.count++
  return false
}

const facilitatorClient = new HTTPFacilitatorClient(
  createFacilitatorConfig(
    process.env.CDP_API_KEY_ID!,
    process.env.CDP_API_KEY_SECRET!,
  )
)

const server = new x402ResourceServer(facilitatorClient)
  .register('eip155:8453', new ExactEvmScheme())

const paywalled = paymentProxy(
  {
    '/api/:path*': {
      accepts: [
        {
          scheme: 'exact',
          price: '$0.05',
          network: 'eip155:8453',
          payTo: process.env.PAYMENT_ADDRESS!,
        },
      ],
      description: 'ETHGlobal Search API — 10 free requests/min, $0.05 USDC per additional request',
      mimeType: 'application/json',
    },
  },
  server,
)

export async function middleware(req: NextRequest): Promise<NextResponse> {
  const ip = getIp(req)
  if (!isRateLimited(ip)) return NextResponse.next()
  return paywalled(req) as Promise<NextResponse>
}

export const config = {
  matcher: ['/api/:path*'],
}
