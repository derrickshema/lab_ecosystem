# ============================================================
# FRONTEND DOCKERFILE (SvelteKit)
# ============================================================
# SvelteKit needs to be built into static files + a Node.js server.
# We use a multi-stage build:
# 1. deps: Install dependencies
# 2. builder: Build the app
# 3. runner: Run the production server
# ============================================================

# ------------------------------------------------------------
# STAGE 1: Dependencies
# ------------------------------------------------------------
FROM node:22-slim AS deps

RUN npm install -g pnpm

WORKDIR /app

# Copy package files first (for caching)
COPY package.json pnpm-lock.yaml ./

# Install dependencies
# --frozen-lockfile: Fail if lockfile is out of sync (reproducible builds)
RUN pnpm install --frozen-lockfile

# ------------------------------------------------------------
# STAGE 2: Builder
# ------------------------------------------------------------
FROM deps AS builder

WORKDIR /app

# Copy dependencies from the deps stage
# COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the SvelteKit app
# This creates a 'build' folder with the production server
# The PUBLIC_* and VITE_* env vars are baked in at build time
# We set a placeholder that will be replaced at runtime
ENV PUBLIC_API_URL=__PUBLIC_API_URL_PLACEHOLDER__

RUN pnpm build

# ------------------------------------------------------------
# STAGE 3: Runner (Production)
# ------------------------------------------------------------
FROM node:22-slim AS runner

# Create a non-root user for security
# Running as root in containers is a security risk
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 --gid 1001 sveltekit

WORKDIR /app

# Copy the built application from the builder stage
# adapter-node outputs to 'build' folder by default
COPY --from=builder --chown=sveltekit:nodejs /app/build ./build
COPY --from=builder --chown=sveltekit:nodejs /app/package.json ./

# Switch to non-root user
USER sveltekit

# SvelteKit adapter-node uses port 3000 by default
EXPOSE 3000

# Environment variables for the Node.js server
# HOST: Listen on all interfaces (required in Docker)
# PORT: Port to listen on
# ORIGIN: Required by SvelteKit for CSRF protection
ENV HOST=0.0.0.0
ENV PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))" || exit 1

# Start the production server
# The 'build' folder contains an 'index.js' that runs the server
CMD ["node", "build"]

