# Agora Agents Hackathon — Submission Packet

**Event:** Agora Agents Hackathon (Canteen × Circle × Arc) · May 11–25 2026
**Project:** Pantheon Trades
**RFB:** 02 — Prediction Market Trader Intelligence (primary) · partial fit on 03, 04
**Submission form:** https://forms.gle/hFPM2t4Jt1zGfqzM7

This document is the operator's pre-flight checklist. Everything needed
for the submission lives here in one place: video script, Circle-tools
checklist, traction template, repo links, and the form fill-in.

---

## 1. Submission form — fill-in template

Copy-paste these answers into the Google Form. Update bracketed `[]`
fields with current numbers on submission day.

### Project name
`Pantheon Trades`

### One-line description
> A 10-agent AI council debates every Polymarket trade, refuses
> the bad ones, and anchors every restraint on-chain.

### Public GitHub repo
`https://github.com/NAME0x0/Pantheon-Trades`

### Live product link
`https://pantheon-trades-web.vercel.app`

### Video demo link
*[populate with Loom / YouTube URL once recorded — script in §2]*

### Which RFB(s) does this address?
> **Primary: RFB 02 — Prediction Market Trader Intelligence.** Pantheon
> finds +EV bets across noisy signals (GDELT, Wikipedia, FRED,
> Manifold, Polymarket order books) and sizes positions with
> conformal half-Kelly under a constitutional risk regime. Partial fit
> on RFB 03 (architecture supports verticals — see the politics + NFL
> demo bundles) and RFB 04 (Areopagus *is* the portfolio gatekeeper).

### What does your agent decide vs automate?
> Every step of a Pantheon trade is decided autonomously:
>
> - Apollo *decides* which signals clear the 7-dimension band scorer
>   (S/A/B/C/D) — no operator threshold tuning per market.
> - Boule's 10 agents *decide* their own probability estimates per
>   round through structured deliberation; Athena drafts a synthesis
>   from the prior 3 rounds. Zeus and Solon can each veto a trade
>   unilaterally on constitutional grounds.
> - Areopagus *decides* the final position size via half-Kelly with
>   drawdown haircut + correlation cap + category cap.
> - Strategos *decides* maker vs taker per order, post-only vs
>   crossing, and which Circle tool to route gas through.
> - Underworld writes post-mortems that *decide* prompt edits for
>   the agents that consistently underperform.
>
> The operator sets the constitution and the LLM provider. The agents
> do the rest.

### Real users / traction during the event window
> *[update with live numbers from the wallet-connect counter on
> the /demo page — examples below]*
>
> - GitHub stars: `[N]`
> - Wallets that completed SIWE on the demo: `[N]` (verified in
>   browser console + Vercel Analytics)
> - Discord community members in the Pantheon channel: `[N]`
> - On-chain Proof-of-Restraint witnesses on Arc Testnet: `[N]`
>   (block 42,337,549 is the first — verifiable at
>   <https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb>)
> - Paper-trade artifacts: `[N]` runs producing JSON + Sankey
>   (committed under `artifacts/`)

### What user problems are you solving?
> 1. **Discipline is invisible.** Trading bots that *do not* fire are
>    indistinguishable from broken bots. Pantheon makes restraint
>    auditable by writing every refusal to Arc.
> 2. **Single-LLM ceiling.** Diverse council > single model. 11
>    interchangeable providers (Anthropic / Gemini / OpenAI /
>    OpenRouter / Groq / Together / DeepSeek / xAI / Fireworks /
>    Ollama / LM Studio) per the `BOULE_LLM_PROVIDER` env var.
> 3. **Fees eat naive strategies.** The CoinGecko paper-trade
>    artifact (–39.5% PnL on $10k with $1,346 in fees) is the
>    honest evidence; the maker-rebate path (–111 bps net via
>    `post_only`) is the fix.
> 4. **Agents are unmonetized.** Polymarket V2 builder codes are
>    the answer — already plumbed in `services/strategos/src/strategos/polymarket_builder.py`.

### Circle developer-tool usage (most weighted question after agency / traction)
*[checklist in §3 — paste the ✓ rows directly]*

---

## 2. Video demo script (≤ 3 min)

Loom or YouTube. Screen + voiceover. Aim for 2:45–3:00. Polish over
length — judges said they read the repo "like operators."

### 0:00 – 0:25  ·  The problem (25 s)
> 90% of trading bots optimise PnL and report the trades they took.
> Pantheon optimises for the trades it refused — and writes every
> refusal to Arc Testnet so the discipline is auditable.

Visual: open Arcscan, scroll to block 42,337,549. Hover the
`Restrained` event. ~5 seconds. Cut to the demo home page.

### 0:25 – 1:10  ·  Watch the council deliberate (45 s)
> Here's a real BTC market priced at 42% YES. Our Apollo signal
> scorer flags it as B-band with +17 pp edge. The council convenes.

Visual: click "Watch the council" → /demo → press Play. Speed to 4×.
Narrate while events scroll: "Ares argues the long case... Athena
synthesises... Zeus checks the constitution... vote tally APPROVE."

End scene by showing the verdict card + paper trade.

### 1:10 – 1:35  ·  Restraint scenario (25 s)
> When the constitution says no, the chain remembers.

Visual: tab over to "Crypto · Restraint". Show Zeus veto event card.
Click "Verify on Arcscan" → real block / tx / proof_id printed.

### 1:35 – 2:05  ·  Circle stack in action (30 s)
> Pantheon is built on Arc with USDC settlement. Fees are paid in
> USDC via Paymaster. Idle bankroll parks in USYC between trades.
> Polymarket V2 builder codes attribute every fill to our payout
> address. CCTP + Gateway move USDC seamlessly across chains.

Visual: open `docs/HACKATHON_SUBMISSION.md` (this file) in a new tab,
highlight §3 checklist. Then `services/strategos/src/strategos/`
listing — show `paymaster_client.py`, `gateway_client.py`,
`usyc_treasury.py`, `polymarket_builder.py`, `maker_rebate.py`.

### 2:05 – 2:35  ·  Honest performance (30 s)
> We don't pretend to have an edge we haven't proven. Here's a
> real CoinGecko paper trade — 79 trades on naive BTC momentum,
> –39.5% PnL after fees. That's the honest baseline. The maker-
> rebate path on 8 patient politics trades earned +$21 in rebates
> versus paying $0 in fees — same trades, opposite sign on cost.

Visual: scroll the /demo page to the CoinGecko panel. Then open
the synthetic Polymarket paper-trade artifact.

### 2:35 – 3:00  ·  Call to action (25 s)
> 430 Python tests. Halmos symbolic proofs on the immutable
> contracts. Full LLM-agnostic provider matrix. Built for the
> trades we refuse, hardened for the ones we take. Try it at
> pantheon-trades-web.vercel.app — connect your wallet to Arc
> Testnet, watch the council, and let us know what you'd refuse.

Visual: zoom out to the home-page hero. Hold on the final frame.

### Production notes
- **No music.** Demo speaks for itself.
- **One take or two.** Don't over-edit — judges value raw walkthroughs.
- **Captions.** Loom auto-captions; double-check the Greek god names.
- **Upload BOTH** to YouTube (public) AND Loom (link-only) so the
  judges have a fallback if one platform is slow.

---

## 3. Circle developer-tool usage — checklist

This is the 20% rubric column. Mark every line that's in the repo so
the judges can verify by `grep`.

| Tool | Status | Where in the repo |
|------|--------|-------------------|
| **Arc** (settlement L1) | ✓ shipped | `contracts/` deploys on Arc Testnet · `services/areopagus/src/areopagus/chain.py` writes `ProofOfRestraint` records · contract live at [`0x4b35…4895`](https://testnet.arcscan.app/address/0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895). First witness at block 42,337,549. |
| **USDC** | ✓ shipped | Native settlement token throughout · `strategos.paper.PaperBook` denominates in USDC · `strategos.maker_rebate.FeeLedger` accounts in USDC. |
| **Contracts** | ✓ shipped | 8 Solidity contracts in `contracts/src/` including `ProofOfRestraint`, `PantheonConstitution`, `NoTradeAlpha`, `ThesisRegistry`, `AgentReputation`. 51 Foundry tests + 2 Halmos symbolic specs. |
| **Wallets** | ✓ shipped | `apps/web/app/demo/wallet-connect.tsx` — EIP-1193 SIWE flow, Arc-Testnet network switch with `wallet_addEthereumChain` 4902 fallback, personal_sign verification. |
| **App Kit** (Bridge / Send / Unified Balance) | ✓ wired (intent layer) | `services/strategos/src/strategos/gateway_client.py` produces `GatewayTransferIntent` for cross-chain USDC moves. The Bridge / Send UI hooks consume the intent. |
| **Paymaster** | ✓ shipped | `services/strategos/src/strategos/paymaster_client.py` — async client + decide routing between native gas and USDC-denominated gas based on balances + operator preference. |
| **Gateway** | ✓ shipped | `services/strategos/src/strategos/gateway_client.py` — unified balance reads, per-chain segmentation, transfer-intent producer. |
| **USYC** | ✓ shipped | `services/strategos/src/strategos/usyc_treasury.py` — idle-bankroll parking, mint/redeem intent generator, daily-accrual + annual-projection helpers. |
| **CCTP** | ✓ wired (intent layer) | Cross-chain USDC moves flow through `GatewayTransferIntent` which the submitter routes via CCTP for chains not covered by Gateway. |
| **EURC** | partial | `pantheon_core.schema` accepts arbitrary currency; FX-aware strategies are roadmap. |
| **Nanopayments** | partial | High-frequency Polymarket fills are a designed use case for the Paymaster + Gateway path — sub-cent gas is exactly the regime our maker rebates depend on. |

### Two paid-equivalent assets we use

- **Polymarket V2 builder codes** — `services/strategos/src/strategos/polymarket_builder.py`. Per-fill USDC attribution to a payout address. Tied to research note #2 from the hackathon page.
- **Trade reasoning anchors on Arc** — `services/parthenon/src/parthenon/trace_anchor.py`. Hashes each Boule deliberation's `TraceEvent` stream, pins canonical bytes to IPFS, anchors the bundle hash on Arc. Tied to research note #1 ("reasoning traces as the product").

---

## 4. Traction template

How to count, what to report, where to point judges.

### Sources of truth

| Channel | What to count | How to read it |
|---------|---------------|----------------|
| Vercel Analytics | unique visitors, /demo views, time-on-page | dashboard.vercel.com |
| Wallet connects | unique addresses that completed SIWE on /demo | added a counter to the demo page (consult before merging) |
| GitHub | stars, forks, watchers | `gh api repos/NAME0x0/Pantheon-Trades` |
| Arc Testnet | on-chain restraint witnesses | `gh api …` on contract events / Arcscan |
| Discord | engaged users (>3 messages) | manual count |
| Twitter | impressions on launch thread | analytics tab |

### Day-0 → Day-7 plan

**Day 0 (submission day):** post to the Canteen Discord with the demo link + a 60-word pitch. DM 20 prediction-market builders on Twitter. Get 5–10 wallet connects same day.

**Day 1–3:** Twitter thread describing the on-chain restraint witness — link to Arcscan. Engage trading-agent threads on /r/MachineLearning. Post the maker-rebate artifact as evidence.

**Day 4–6:** AMA in the Canteen Discord channel. Show the council deliberating live. Offer 10 paper-trade test slots with operator wallets.

**Day 7:** final tally screenshot. Submit honest numbers in the form.

### What counts as a "real user" per the rubric
> "How many real people have tried the product, and what validation
> you got from end users."

We claim a user when:

1. They connect a wallet on `/demo` and complete the SIWE signature, OR
2. They `git clone` the repo and report back in Discord with a captured artifact, OR
3. They open an issue / PR on GitHub.

Pure page views do not count. We will not inflate.

---

## 5. Repo "for the judges" header

Add the following block to the top of `README.md` near the existing
badges — points the judges directly at what they need to see.

```markdown
> **Hackathon judges:** see [`docs/HACKATHON_SUBMISSION.md`](./docs/HACKATHON_SUBMISSION.md)
> for the submission packet (video, Circle-tools checklist, traction).
> Built for the Agora Agents Hackathon · Canteen × Circle × Arc · May 2026.
```

---

## 6. Submission checklist (do this in order)

- [ ] Push the 6+ commits to `origin/main` (live `pantheon-trades-web.vercel.app` redeploys automatically)
- [ ] Verify `/demo` loads + the on-chain restraint card renders
- [ ] Record the 3-min video per §2 — Loom + YouTube
- [ ] Run `python scripts/backtest_council_vs_manifold.py --mode=full --n=100` and commit the artifact (~$0.02 on Gemini)
- [ ] Update §1 "Real users / traction" numbers from Vercel + GitHub
- [ ] Add the README banner from §5
- [ ] Fill the Google form: https://forms.gle/hFPM2t4Jt1zGfqzM7
- [ ] Post the submission link in `#agora-agents` on Canteen Discord
- [ ] Submit a second time on day 7 with refreshed traction numbers

---

## 7. Honest self-assessment vs the rubric

| Column | Weight | Self-grade | Why |
|--------|--------|------------|-----|
| Agentic Sophistication | 30% | **27 / 30** | 11-agent council · 2 vetoes · adversarial dissenter · ablation · prompt evolution · RAG · drawdown-adjusted half-Kelly · conformal interval sizing. |
| Traction | 30% | **6–18 / 30** | Floor: 0 real wallets + 1 on-chain witness. Target: 20+ wallet connects, 50+ GitHub stars, AMA evidence by day 7. |
| Circle tool usage | 20% | **15–18 / 20** | After this wave: Arc + USDC + Contracts + Wallets + Paymaster + Gateway + USYC + builder codes + trace anchors. Only EURC + Nanopayments partial. |
| Innovation | 20% | **17 / 20** | Proof of Restraint as on-chain glass-box discipline; builder-code attribution + trace anchors per the hackathon's own research notes. |

**Realistic landing:** Standout team if traction stays low. 3rd place ($5k) if we hit 20 wallet connects + 1 on-chain trace anchor demo. 2nd place ($7.5k) needs >50 wallet connects + active AMA proof.

Grand prize ($10k) requires real users. The 4-day traction push is the only path there.
