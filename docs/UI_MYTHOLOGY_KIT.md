# UI Mythology Kit

Design tokens, naming conventions, and visual guidelines for the web UI that reinforce the Greek mythology theming.

## Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Olympus Gold | `#C9A227` | Band S signals, Zeus, primary accents |
| Athena Blue | `#2563EB` | Primary actions, approved states |
| Hades Purple | `#7C3AED` | Risk indicators, warnings |
| Ares Red | `#DC2626` | Rejection, stop-loss triggers, Band D |
| Elysium Green | `#16A34A` | Profitable, resolved YES, Band A |
| Parthenon White | `#F8FAFC` | Archive state, completed |
| Underworld Dark | `#1E1B4B` | Failed states, terminated, background |
| Agora Amber | `#D97706` | Band B, monitoring, pending states |

## Signal Band Colors

| Band | Color | Hex |
|------|-------|-----|
| S | Olympus Gold | `#C9A227` |
| A | Elysium Green | `#16A34A` |
| B | Agora Amber | `#D97706` |
| C | Muted Orange | `#EA580C` |
| D | Stone Grey | `#6B7280` |

## Agent Avatars / Icons

Each council agent has an associated icon or symbol:

| Agent | Symbol | Icon Description |
|-------|--------|----------------|
| Zeus | ⚡ | Lightning bolt |
| Hades | 💀 | Skull / underworld key |
| Athena | 🦉 | Owl |
| Apollo | ☀️ | Sun |
| Cassandra | 🔮 | Crystal ball |
| Ares | ⚔️ | Crossed swords |
| Hephaestus | 🔨 | Hammer |
| Solon | ⚖️ | Scales |
| Themis | 🏛️ | Columns |
| Daedalus | 🔧 | Wrench |
| Strategos | 🎯 | Target |
| Humans | 👤 | Person |
| Messengers | 📨 | Envelope |

## Vote State Colors

| Vote | Color |
|------|-------|
| APPROVE | Elysium Green |
| REJECT | Ares Red |
| ABSTAIN | Stone Grey |
| VETO | Hades Purple |
| FLAG | Agora Amber |

## Status Badges

| Status | Color | Label |
|--------|-------|-------|
| Deliberating | Athena Blue | "In Council" |
| Approved | Elysium Green | "Approved" |
| Rejected | Ares Red | "Rejected" |
| Executed | Olympus Gold | "Executed" |
| Expired | Stone Grey | "Expired" |
| ProofOfRestraint | Parthenon White | "Restrained" |
| System Active | Elysium Green | "Active" |
| System Paused | Ares Red | "Paused" |
| System Degraded | Agora Amber | "Degraded" |

## Typography

- **Headings**: Cinzel (or similar serif with classical feel)
- **Body**: Inter (clean, readable)
- **Code/addresses**: JetBrains Mono

## Component Naming (shadcn/ui)

Components follow both functional and mythological naming where appropriate:
- `SignalBand` — the band classification indicator component
- `SwarmGraph` — the agent deliberation graph visualization
- `ArcProofBadge` — the on-chain proof badge
- `RiskGauge` — Areopagus risk level visualization
- `ThesisViewer` — the full thesis detail component
- `TraceViewer` — the debate trace timeline
- `AgentLeaderboard` — the Ostrakon leaderboard table
- `PnLChart` — position PnL chart
- `MarketScanner` — live signal feed

## Language

Use mythology-consistent terminology in UI copy:

| Technical Term | UI Label |
|---------------|---------|
| Signal | Oracle Signal |
| Thesis | Council Thesis |
| Approved | Council Approved |
| ProofOfRestraint | Restrained |
| Deliberation | Council Deliberation |
| Areopagus | The Court |
| Boule | The Council |
| Agent exile | Exile |
| Agent promotion | Ascension |
