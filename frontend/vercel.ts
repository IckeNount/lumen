import { routes, type VercelConfig } from "@vercel/config/v1";

const rawBackendUrl = process.env.RAILWAY_BACKEND_URL;

if (!rawBackendUrl) {
  throw new Error("RAILWAY_BACKEND_URL is required for Vercel rewrites.");
}

const backendUrl = rawBackendUrl.replace(/\/+$/, "");

export const config: VercelConfig = {
  rewrites: [
    routes.rewrite("/health", `${backendUrl}/health`),
    routes.rewrite("/api/:path*", `${backendUrl}/api/:path*`),
  ],
};
