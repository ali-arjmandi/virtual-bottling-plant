# Edge bridge (L1/L2 conduit). Build context: repo root (needs the workspace and packages/contracts).
FROM node:22-alpine AS build
RUN npm install -g pnpm@9.15.4 --no-update-notifier --no-fund
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/contracts/package.json packages/contracts/
COPY services/edge-bridge/package.json services/edge-bridge/
RUN pnpm install --frozen-lockfile --filter @vbp/edge-bridge...
COPY packages/contracts packages/contracts
COPY services/edge-bridge services/edge-bridge
RUN pnpm --filter @vbp/contracts build && pnpm --filter @vbp/edge-bridge build \
 && pnpm --filter @vbp/edge-bridge deploy --prod /out

FROM node:22-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=node:node /out .
USER node
EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --retries=6 \
  CMD node -e "fetch('http://127.0.0.1:8081/health').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"
CMD ["node", "dist/main.js"]
