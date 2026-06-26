# A2A Agent Orchestrator — 5-Year Financial Projection

> Realistic scenario for a vertical SaaS platform targeting dev teams.
> Mixed remote team (30% US-based, 70% remote EU / LatAm).
> Assumes solid execution but not extraordinary luck.

---

## 1. Executive Summary

| Metric | Year 5 outcome |
|---|---|
| **Annual recurring revenue (ARR)** | $9M |
| **Annual net profit** | $3.3M |
| **5-year cumulative profit** | $5.3M |
| **Company valuation (paper)** | $50–90M |
| **Team size** | 25 people |
| **Founder/CEO compensation** | $280K/year |
| **Months to first profitable year** | ~24 |

---

## 2. 5-Year Profit & Loss Statement

| Line item | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---:|---:|---:|---:|---:|
| **Customers** | 5 | 150 | 400 | 800 | 1,400 |
| **Revenue** | $50K | $720K | $2.4M | $5.0M | $9.0M |
| Salaries (loaded, excl. CEO) | $30K | $550K | $1.2M | $2.3M | $3.8M |
| CEO compensation | $0 | $100K | $180K | $230K | $280K |
| Cloud infrastructure (AWS, DB) | $5K | $30K | $120K | $280K | $500K |
| LLM API costs (net of passthrough) | $5K | $50K | $60K | $120K | $200K |
| Marketing & sales | $5K | $50K | $180K | $400K | $700K |
| SaaS tools & subscriptions | $3K | $15K | $40K | $80K | $140K |
| Legal, accounting, operations | $5K | $15K | $40K | $120K | $200K |
| **Total costs** | $90K | $880K | $1.78M | $3.4M | $5.7M |
| **Net income** | **-$40K** | **-$160K** | **$620K** | **$1.6M** | **$3.3M** |
| **Cumulative net income** | -$40K | -$200K | $420K | $2.02M | $5.32M |

---

## 3. Revenue Model

### Pricing tiers

| Plan | Monthly price | Target customer | Features |
|---|---:|---|---|
| Starter | $99 | Indie dev / small team | 5 agents, 1K tasks/month |
| Pro | $499 | Growing startup | 25 agents, 10K tasks |
| Business | $1,999 | Mid-market | Unlimited agents, 100K tasks |
| Enterprise | $5K–25K+ | Large company | Custom + SLAs + SSO |

### Average revenue per customer (ARPC)

- Year 1: $250/month (mostly Starter early adopters)
- Year 2: $400/month (mix of Starter + Pro)
- Year 3: $500/month (more Pro + first Business)
- Year 4: $520/month (Business + first Enterprise)
- Year 5: $535/month (mature mix, Enterprise contracts growing)

### Customer acquisition assumptions

| Year | Net new customers | End of year total | Channels |
|---|---:|---:|---|
| Year 1 | 5 | 5 | Personal network, design partners |
| Year 2 | 145 | 150 | Content marketing, ProductHunt, dev communities |
| Year 3 | 250 | 400 | Paid ads, partnerships, referrals |
| Year 4 | 400 | 800 | Inbound sales, integrations |
| Year 5 | 600 | 1,400 | Enterprise sales motion, channel partners |

### Churn assumptions

- Year 1: 5% monthly (high — early product, finding fit)
- Year 2: 3% monthly (stabilizing)
- Year 3: 2% monthly (good fit)
- Year 4: 1.5% monthly (mature product)
- Year 5: 1.2% monthly (best in class for SMB SaaS)

---

## 4. Cost Structure Details

### 4.1 Salaries (the biggest cost)

All figures shown are **loaded cost** — base salary × 1.3 to account for taxes, benefits, equipment, and overhead.

### 4.2 Cloud infrastructure breakdown (Year 3 detail)

| Service | Monthly | Annual |
|---|---:|---:|
| AWS EC2 / Fargate (agent runtime) | $4,000 | $48K |
| AWS RDS PostgreSQL | $1,500 | $18K |
| AWS ElastiCache Redis | $500 | $6K |
| AWS S3 + CloudFront | $400 | $5K |
| Datadog / monitoring | $1,500 | $18K |
| Sentry (error tracking) | $300 | $4K |
| SendGrid (email) | $200 | $2K |
| Auth0 / Clerk | $800 | $10K |
| Other / overhead | $800 | $9K |
| **Total** | **$10,000** | **$120K** |

### 4.3 LLM API economics

This is often misunderstood. Here's how the model works:

- Customers pay you for AI usage with markup (typical: cost × 1.5–2.0)
- You pay Claude / OpenAI for the actual API calls
- The difference is your gross profit on usage

**Year 3 example:**
- Customers consume $300K worth of LLM tokens
- You charge them $480K for that usage (60% markup)
- Your net LLM expense after markup: $60K
- Your gross profit from passthrough: $180K (counted in revenue)

### 4.4 Marketing & sales scaling

| Year | Spend | Focus |
|---|---:|---|
| Year 1 | $5K | Free content, dev communities, conferences |
| Year 2 | $50K | Content marketing, light paid ads |
| Year 3 | $180K | First sales hire, paid ads, partnerships |
| Year 4 | $400K | Sales team of 3, attended events |
| Year 5 | $700K | Field sales for enterprise, sponsored events |

---

## 5. Team Composition by Year

### Year 1 — Solo founder
- **CEO / Engineer (you)** — $0 (founder, no salary)
- Optional: 1 contractor for specialized work

### Year 2 — Small team (3 people)
- CEO (you) — $100K
- Senior backend engineer — $140K
- AI / agent engineer — $150K
- Loaded total: ~$507K + $50K contractors = ~$557K

### Year 3 — Established team (8 people)
- CEO (you) — $180K
- 2× Senior backend engineers — $140K each
- AI / agent engineer — $150K
- Frontend engineer — $110K
- DevOps / SRE — $120K
- Growth / sales — $100K
- Customer success — $70K
- Loaded total: ~$1.38M

### Year 4 — Scaling (15 people)
- CEO (you) — $230K
- VP Engineering — $200K
- 4× Engineers (backend/AI/frontend) — avg $130K
- 1× Senior DevOps — $140K
- 1× Designer — $110K
- 3× Sales — $100K base + commission
- 2× Customer success — $80K each
- 2× Operations / finance — $100K each
- Loaded total: ~$2.53M

### Year 5 — Real company (25 people)
- CEO (you) — $280K
- VP Engineering — $230K
- VP Sales — $220K
- VP Customer Success — $180K
- 8× Engineers — avg $135K
- 3× DevOps / SRE — avg $130K
- 2× Designers — avg $115K
- 5× Sales — $110K base + commission
- 3× Customer success — avg $85K
- 1× Marketing — $130K
- 1× Finance / operations — $120K
- Loaded total: ~$4.08M

---

## 6. CEO Compensation Plan

| Year | CEO base salary | Rationale |
|---|---:|---|
| Year 1 | $0 | Bootstrap mode, founder lives off savings |
| Year 2 | $100K | First sustainable salary, still below market |
| Year 3 | $180K | At-market for early-stage CEO of profitable company |
| Year 4 | $230K | Market rate for CEO of $5M ARR company |
| Year 5 | $280K | Standard for CEO of $9M ARR profitable SaaS |

**Note:** This excludes equity, which is the real founder upside (see Section 7). It also excludes potential bonuses or distributions from profits in Years 3–5.

---

## 7. Company Valuation Analysis

### Valuation multiples for SaaS companies

Most SaaS businesses are valued as a multiple of ARR (annual recurring revenue). The multiple depends on:

- Growth rate (faster growth = higher multiple)
- Gross margin (>75% is good)
- Churn (lower is better)
- Market size
- Profitability

| Growth profile | ARR multiple |
|---|---:|
| Slow growth (<30% YoY) | 3–5× |
| Moderate growth (30–60% YoY) | 5–8× |
| Fast growth (60–100% YoY) | 8–12× |
| Hypergrowth (>100% YoY) | 12–20× |

This business projects **80%+ YoY growth** through Year 5, so 6–10× ARR is realistic.

### Valuation by year

| Year | ARR | Multiple range | Company value |
|---|---:|---|---:|
| Year 2 | $720K | 4–6× | $3M–$4M |
| Year 3 | $2.4M | 5–8× | $12M–$19M |
| Year 4 | $5M | 6–9× | $30M–$45M |
| Year 5 | $9M | 6–10× | $54M–$90M |

### Your stake at Year 5

| Funding path | Founder ownership | Stake value |
|---|---:|---:|
| Pure bootstrap (no funding) | ~95% | $51M–$85M |
| One seed round ($1.5M) | ~75% | $40M–$67M |
| Seed + Series A ($8M total) | ~55% | $30M–$50M |

---

## 8. Paper Value vs. Real Cash

**Critical distinction:** The valuations above are *company values*, not money you can spend.

### Ways to convert paper value to real cash

1. **Acquisition (most common)**
   - A larger company buys you (e.g., Atlassian, Microsoft, Salesforce)
   - Cash arrives in 3–6 months
   - You typically have a 2–3 year earnout staying as employee
   - Realistic timing: Year 6–8

2. **Secondary sale**
   - Investors buy some of your existing shares (you cash out partial)
   - Typically 10–20% of your stake
   - Possible: $5M–$15M cash in Year 4–5
   - You keep running the company

3. **Dividends**
   - Once profitable, the company can pay you part of profits
   - At $3M+ net income, you could take $1M–$2M/year as distributions
   - Tax-efficient depending on structure

4. **IPO**
   - Requires $100M+ ARR (you're not there yet at Year 5)
   - Realistic timeline: Year 8–12
   - Best long-term outcome but slowest

### Realistic founder take-home timeline

| Period | Annual income |
|---|---:|
| Year 1 | $0 (savings runway) |
| Year 2 | $100K (salary) |
| Year 3 | $180K (salary) |
| Year 4 | $230K (salary) + possible $1M secondary |
| Year 5 | $280K (salary) + $1–2M distribution from profits |
| Year 6–8 | $80M–$150M exit OR continued $3M+/year as owner |

---

## 9. Three Scenarios

### Conservative (most likely outcome — 40% probability)
- Slower growth, smaller team, longer to profitability
- Year 5 ARR: $3–5M
- Year 5 valuation: $15–35M
- Founder exit: $10–20M

### Realistic (this projection — 30% probability)
- Numbers shown in this document
- Year 5 ARR: $9M
- Year 5 valuation: $50–90M
- Founder exit: $30–70M

### Aggressive (best case — 8% probability)
- Excellent execution + favorable market timing
- Year 5 ARR: $20M+
- Year 5 valuation: $150–250M
- Founder exit: $80M–$150M

### Failure case (the most common single outcome — 22% probability)
- Run out of money / no product-market fit / co-founder conflict
- Company shuts down or pivots
- Founder loses 2–4 years of salary and savings

---

## 10. Key Risk Factors

| Risk | Severity | Mitigation |
|---|---|---|
| Big tech (Google, Microsoft) launches competing product | High | Go vertical-deep, build network effects via federation |
| AI model costs increase | Medium | Multi-provider strategy, optimize prompts, charge customers more |
| Customer acquisition costs (CAC) blow up | High | Strong content marketing, focus on retention |
| Cannot hire fast enough | Medium | Remote-first, equity-heavy comp |
| Regulatory uncertainty around AI agents | Medium | Stay informed, build compliance early |
| Recession reduces SaaS spending | Medium | Conservative cash management, focus on ROI messaging |
| Co-founder / team conflict | High | Get clear equity + decision rights in writing day 1 |

---

## 11. Critical Milestones to Hit

These are the make-or-break moments. Miss any of them and the projection breaks.

- **Month 6** — MVP launched, first 5 design partners using it
- **Month 12** — $15K MRR, first paying customer outside personal network
- **Month 18** — $40K MRR, hired first engineer
- **Month 24** — $100K MRR, profitability in sight
- **Month 30** — $200K MRR, sales team in place
- **Month 36** — $500K MRR ($6M ARR run rate, ahead of projection)
- **Month 48** — $750K MRR + first Enterprise contract
- **Month 60** — $1M MRR ($12M ARR) — exit conversations begin

---

## 12. Key Assumptions (the things that must be true)

For these numbers to materialize, the following must hold:

1. **Product-market fit is achievable** — There is a real, painful problem dev teams will pay to solve with multi-agent orchestration.
2. **A2A protocol becomes mainstream** — Companies adopt it as the standard for cross-agent communication.
3. **You stay focused on the vertical** — No drift into general-purpose tooling.
4. **You're willing to sell** — You'll do customer development, demos, and close deals.
5. **You can attract talent** — Equity + mission story is compelling enough to hire below market.
6. **Capital efficiency** — You don't burn cash on premature scaling.
7. **No catastrophic external event** — No deep recession, no AI regulation that breaks the model.

If 3+ of these don't hold, the projection collapses into the failure case.

---

## 13. What This Means For You

This is a **5-year commitment** for a chance at $30M–$70M of personal wealth. That works out to ~$6M–$14M per year of your time, in expected value. Better than most jobs, worse than getting lucky with a top tech company's stock.

The trade is real but the math only works if you actually build the thing. **Stop calculating, start building.**

---

*Last updated: June 2026. All figures are projections, not guarantees. Past performance of similar companies does not guarantee future results.*
