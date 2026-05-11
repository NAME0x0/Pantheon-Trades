# Pantheon Trades

## What Is It?

Pantheon Trades is an AI-powered prediction market trading system. A council of specialized AI agents, each embodying a Greek god archetype, deliberates on every trade before any capital is deployed. The entire decision process — including decisions *not* to trade — is permanently recorded on-chain.

## Core Premise

Prediction markets are fundamentally about information aggregation. If you have better information, or better judgment about existing information, you can trade profitably.

The question is: can a council of diverse, adversarially-structured AI agents consistently identify mispriced prediction market contracts?

## The Hypothesis

A multi-agent council with structured adversarial debate (bull vs. bear, risk-focused vs. execution-focused, cautious vs. aggressive) will produce better-calibrated probability estimates than any single agent, and will identify a exploitable edge on a subset of Polymarket markets.

The structured debate format is designed to:
1. Surface information that any single agent might miss
2. Prevent groupthink via adversarial roles
3. Apply domain-specific expertise (Hades for risk, Hephaestus for execution, etc.)
4. Maintain constitutional constraints (Zeus, Solon) that prevent overconfident overreach

## On-Chain Accountability

Every trade, every no-trade, every agent vote is on-chain. This creates:
- **Immutable track record**: can't cherry-pick results
- **Agent accountability**: every agent's calibration is public
- **Proof of restraint**: showing you *didn't* trade bad opportunities is as important as showing you traded good ones
- **Counterfactual honesty**: we compute and publish what would have happened if we hadn't traded (or if we had)

## System Goals

1. Identify S/A band signals on Polymarket with consistent positive edge
2. Convert signals to profitable trades via sound deliberation
3. Demonstrate that the council's judgment adds value beyond a simple statistical model
4. Build a public, auditable record of AI agent performance in real markets

## What This Is Not

- Not a market maker or liquidity provider
- Not HFT — deliberation takes minutes, not milliseconds
- Not a fully automated "fire and forget" system — human oversight is built in
- Not trying to dominate markets — position sizes are small (max 5% per trade)

## Current Status

System in development. All services have code structure in place. Actively building out implementations starting with Pythia (data) → Apollo (signals) → Boule (deliberation).
