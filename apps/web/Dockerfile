# syntax=docker/dockerfile:1.7-labs
FROM node:20-alpine AS deps
WORKDIR /repo
COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/types/package.json packages/types/package.json
COPY packages/hermes/package.json packages/hermes/package.json
COPY packages/config packages/config
RUN corepack enable && pnpm install --filter ./apps/web... --frozen-lockfile=false

FROM node:20-alpine AS builder
WORKDIR /repo
COPY --from=deps /repo /repo
COPY apps/web apps/web
COPY packages packages
WORKDIR /repo/apps/web
RUN corepack enable && pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /repo/apps/web/.next ./.next
COPY --from=builder /repo/apps/web/public ./public
COPY --from=builder /repo/apps/web/package.json ./
COPY --from=builder /repo/node_modules ./node_modules
EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
