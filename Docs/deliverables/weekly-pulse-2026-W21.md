# Weekly Pulse — Groww App Reviews — 2026-W21

| | |
|---|---|
| **App** | Groww Stocks, Mutual Fund, Gold (`com.nextbillion.groww`) |
| **Source** | Google Play (public reviews) |
| **Week** | 2026-W21 |
| **Reviews analysed** | 124 |
| **Generated** | 22 May 2026 |

---

## Sentiment overview

| Positive | Negative | Neutral |
|----------|----------|---------|
| 34 (27%) | 86 (69%) | 4 (3%) |

**Star ratings:** 80 × 1★ · 6 × 2★ · 4 × 3★ · 13 × 4★ · 21 × 5★

---

## Top product areas (Groww map)

| # | Product area | Reviews | Dominant signal |
|---|----------------|--------:|-----------------|
| 1 | **Stocks & F&O** | 55 | Negative — chart lag, order visibility, commodity/F&O on expiry |
| 2 | **Mutual Funds & SIP** | 24 | Mixed — expense ratio, fund UX |
| 3 | **Charts & UX** | 17 | Mixed — crashes, navigation, performance |
| 4 | **KYC & Onboarding** | 11 | Negative — signup / verification friction |
| 5 | **Payments & UPI** | 8 | Negative — add money, transfers |

*Areas assigned via Groww fintech taxonomy (keyword + LLM). See [THEME_LEGEND.md](./THEME_LEGEND.md).*

---

## User voices

> "Very poor experience with Groww commodity trading. Chart candles lag and don't match actual market price, leading to wrong entries."  
> — **1★** · Stocks & F&O / Charts & UX

> "this app is scam . i withdraw money from this app and it didn't receive from 5 days ."  
> — **1★** · Withdrawals & Settlement / Trust & Fraud

> "One of the worst broker. I placed an order today but my app got a glitch where i was not able to see my open order… today was expiry and i got panicked."  
> — **1★** · Stocks & F&O / Charts & UX

---

## Action ideas

| Priority | Action |
|----------|--------|
| **HIGH** | Fix chart sync and open-order visibility on F&O/commodity screens (especially expiry days). |
| **HIGH** | Audit withdrawal/settlement SLAs; show in-app payout status when delays exceed expectations. |
| **MEDIUM** | Improve support response time; add trust/transparency flows where users report fraud or unauthorized debits. |

---

## Executive headline

**Trading reliability and money movement drive most negative sentiment** — prioritize chart accuracy, order state, and withdrawal transparency before broad UX polish.

---

## Delivery (MCP)

| Step | Tool |
|------|------|
| Publish report | **MCP** `POST /append_to_doc` → Google Doc ([saksham-mcp-server](https://github.com/saksham20189575/saksham-mcp-server)) |
| Email draft | **MCP** `POST /create_email_draft` → Gmail |
| Local fallback | Direct Google APIs or markdown file if MCP is offline |

*No PII in this artifact · Sample reviews: [reviews-2026-W21-sample-redacted.csv](./reviews-2026-W21-sample-redacted.csv)*
