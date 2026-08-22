import {
  deploymentEnv,
  routes,
  type VercelConfig,
} from "@vercel/config/v1";

const backendUrl = deploymentEnv("RAILWAY_BACKEND_URL");

const config: VercelConfig = {
  rewrites: [
    routes.rewrite("/health", `${backendUrl}/health`),
    routes.rewrite("/api/:path*", `${backendUrl}/api/:path*`),
  ],
};

export default config;
