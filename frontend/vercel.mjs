const rawBackendUrl = process.env.RAILWAY_BACKEND_URL;

if (!rawBackendUrl) {
  throw new Error("RAILWAY_BACKEND_URL is required for Vercel rewrites.");
}

const backendUrl = rawBackendUrl.replace(/\/+$/, "");

export const config = {
  rewrites: [
    { source: "/health", destination: `${backendUrl}/health` },
    { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
  ],
};
