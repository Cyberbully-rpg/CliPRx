# CliPRx — Ideal Customer Profile

## Primary persona

**A hands-on infrastructure owner at a company with real but not-enterprise-scale cloud spend.**

Think: DevOps/Platform Engineer, SRE, or a technical Engineering Manager/CTO at a startup or mid-market company who personally owns the AWS/Azure/GCP bill and is expected to bring it down — but doesn't have (or can't yet justify) a dedicated FinOps platform like CloudHealth or Vantage.

## Firmographic profile

| Attribute | Fit |
|---|---|
| Company stage | Series A–C startup, or mid-market company |
| Monthly cloud spend | ~$5K–$150K/month (large enough that a 10–20% savings number matters; small enough that an enterprise FinOps suite isn't worth buying) |
| FinOps maturity | No dedicated FinOps hire — cost optimization is a side responsibility of an existing engineer/manager |
| Cloud footprint | Primarily single-cloud (AWS, Azure, or GCP), possibly with light secondary-cloud usage |
| Team structure | Has an engineering team that can execute a sprint ticket — not a solo founder with no one to hand work to |

## Why this profile, mapped to what the product actually does

| Product fact | ICP implication |
|---|---|
| CSV upload, not a live billing API integration | Buyer is comfortable manually exporting a billing CSV periodically — this is an **on-demand audit tool**, not continuous monitoring. Fits monthly/quarterly review cadence, not real-time alerting. |
| Essential-services tier declaration requires knowing which services are "untouchable prod" vs "safe to modify" | Requires **actual infra ownership/domain knowledge** — not usable by a finance/procurement person in isolation. |
| Recommendations are Jira-ticket-styled, with effort-hour estimates | Buyer has (or is) **an engineering team that executes tickets**, not a solo consultant with no team. |
| Reports auto-expire after 30 days, no cross-report trend view | Fits **occasional/periodic use**, not a team already running rigorous weekly FinOps reviews. |
| No team/org/multi-seat concept — single-user ownership throughout | Built today for **one accountable individual**, not a shared multi-owner workflow. Caps effective company size. |
| Multi-cloud parsers (AWS/Azure/GCP), one provider per upload | Fits companies on **one primary cloud** more than heavy multi-cloud shops needing a unified cross-cloud view. |

## Secondary / adjacent persona

**Fractional CTO or infra consultant** running the tool against multiple clients' bills as a quick-audit deliverable. The PDF export ("generated once, downloadable anytime within the 30-day window") fits a one-time engagement well — upload the client's CSV, get a branded report to hand over, move on.

## Who this is *not* for (today)

- **Non-technical finance/procurement teams** — the tier-declaration step assumes infra knowledge.
- **Enterprises with dedicated FinOps teams** already running continuous cost governance — this tool is a lighter-weight, episodic complement, not a replacement.
- **Heavy multi-cloud orgs** wanting one unified report across providers — each upload is single-provider.
- **Teams needing shared/collaborative review** — no multi-seat, no comments, no assignment of tickets to teammates.
- **Anyone wanting real-time cost anomaly alerting** — there's no live integration, scheduling, or push notifications.
