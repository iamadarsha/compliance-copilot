import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pins the workspace root to this directory. Without it, Next.js searches
  // upward for lockfiles and can pick up an unrelated one outside the repo
  // (e.g. in a parent directory on the machine doing the build), which only
  // produces a warning locally but is worth pinning down for a clean deploy.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
