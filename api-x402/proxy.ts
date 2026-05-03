import { paymentProxy, x402ResourceServer } from '@x402/next'
import { ExactEvmScheme } from '@x402/evm/exact/server'
import { HTTPFacilitatorClient } from '@x402/core/server'
import { createFacilitatorConfig } from '@coinbase/x402'
import { NextRequest, NextResponse } from 'next/server'

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
          price: '$0.01',
          network: 'eip155:8453',
          payTo: process.env.PAYMENT_ADDRESS!,
        },
      ],
      description: 'ETHGlobal Search API — $0.01 USDC per request on Base mainnet',
      mimeType: 'application/json',
    },
  },
  server,
)

export async function proxy(req: NextRequest): Promise<NextResponse> {
  return await paywalled(req) as NextResponse
}

export const config = {
  matcher: ['/api/:path*'],
}
