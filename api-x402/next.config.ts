import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/.well-known/x402',
        destination: '/api/x402-well-known',
      },
    ]
  },
}

export default nextConfig
