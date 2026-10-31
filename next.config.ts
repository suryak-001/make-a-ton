import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components is off on purpose: almost every page here is per-user (cookies/session),
  // and opting in would force Suspense boundaries around every session read.
  experimental: {
    authInterrupts: true, // enables forbidden() used by requireRole()
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
