# Deploying the Pantheon demo site to Vercel

The marketing site lives at `apps/web` inside the monorepo. The repo
root contains a `vercel.json` that wires the pnpm + Turborepo build
pipeline into Vercel's defaults.

## One-time setup

1. Push the repo to GitHub (`origin/main`).
2. Sign in to <https://vercel.com> with the GitHub account that owns
   the repo.
3. Click **Add New → Project**.
4. Select the Pantheon-Trades repository.
5. **Leave Root Directory as the repo root** (`.`). The `vercel.json`
   tells Vercel everything it needs to know.
6. Framework preset auto-detects as **Next.js**.
7. Hit **Deploy**. First build takes ~3 minutes (pnpm install + turbo
   build). Subsequent builds are cached and finish in ~30 seconds.

The site lands at `https://<project-name>.vercel.app`. Every PR auto-
gets a preview URL.

## Environment variables

The marketing landing and `/demo` replay do not require any env vars.

The `/dashboard` route calls the FastAPI gateway. If you want it to
work from Vercel, expose your gateway at a public URL and set:

```
NEXT_PUBLIC_API_URL=https://api.pantheon.example.com
```

For the demo deploy you can leave this unset — `/dashboard` will show
a friendly "backend not reachable" notice.

## Refreshing the captured demo

The demo replay reads two static JSON bundles from
`apps/web/public/demo/`:

- `btc-120k-approve.json` — full council approval scenario
- `btc-120k-restraint.json` — Zeus veto / Proof of Restraint scenario

To regenerate them with a real Gemini deliberation (when quota allows):

```bash
uv run python tests/capture_demo_trace.py
```

To rebuild the curated bundles (verdict + paper trade are still computed
by the real Areopagus and Strategos code paths):

```bash
uv run python tests/build_demo_traces.py
```

Then commit the updated JSON and push — Vercel auto-redeploys.

## Local preview

```bash
pnpm install
pnpm --filter @pantheon/web dev
# open http://localhost:3000
```

## Cost

Vercel Hobby tier:

- Bandwidth: 100 GB / month
- Build minutes: 6000 / month
- Serverless invocations: 100k / month

A demo site with a few hundred visitors per month sits well inside
free.
