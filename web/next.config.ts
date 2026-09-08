import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The Desktop above this project is itself a git repo; pin the workspace root
  // so Turbopack does not walk up and adopt an unrelated lockfile.
  turbopack: { root: __dirname },
};

export default nextConfig;
