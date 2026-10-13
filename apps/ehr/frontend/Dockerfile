# ── Stage 1: Deps ─────────────────────────────────────────────
# Install node_modules here and cache them separately from app code.
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

# Bring in installed dependencies from Stage 1
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the app (outputs to /app/build)
RUN pnpm build

# ── Stage 3: Runner ───────────────────────────────────────────
# Final image — only the compiled output, no source or dev tools.
FROM node:22-slim AS runner

# Run as non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 --gid 1001 appuser

WORKDIR /app

# Copy only the compiled build and package.json from Stage 2
COPY --from=builder --chown=appuser:nodejs /app/build ./build
COPY --from=builder --chown=appuser:nodejs /app/package.json ./

USER appuser

EXPOSE 3000

ENV HOST=0.0.0.0
ENV PORT=3000

CMD ["node", "build"]