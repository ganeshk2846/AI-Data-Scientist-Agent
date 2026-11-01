/** @type {import('next').NextConfig} */
const backendPort = process.env.BACKEND_PORT || '8001';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `http://localhost:${backendPort}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;

