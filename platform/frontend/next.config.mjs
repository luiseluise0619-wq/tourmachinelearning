/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // 개발 시 /api → 백엔드(8000) 프록시
    const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${base}/api/:path*` }];
  },
};
export default nextConfig;
