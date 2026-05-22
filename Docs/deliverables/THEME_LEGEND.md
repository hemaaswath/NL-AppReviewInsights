# Groww product-map — theme legend

Reviews are grouped into **fixed fintech product areas** (not free-form labels like “General Feedback”). This keeps insights comparable week over week and routable to squads.

## Canonical areas

| Product area | What users usually mean | Example keywords |
|--------------|-------------------------|------------------|
| **KYC & Onboarding** | Signup, PAN/Aadhaar, verification, first-time setup | kyc, onboard, pan, verify, register |
| **Payments & UPI** | Adding money, UPI, bank transfer, deposits | upi, payment, add money, neft, imps |
| **Mutual Funds & SIP** | MF discovery, SIP, NAV, expense ratio | mutual, sip, nav, expense ratio, elss |
| **Stocks & F&O** | Equity, F&O, commodity, orders, demat, brokerage | stock, fno, commodity, demat, order, intraday |
| **Withdrawals & Settlement** | Cash out, pending payouts, money not received | withdraw, payout, settlement, stuck, pending |
| **Charts & UX** | UI, charts, lag, crashes, navigation | chart, lag, crash, ui, navigation |
| **Fees & Pricing** | Charges, brokerage, AMC, hidden deductions | fee, brokerage, charge, amc |
| **Customer Support** | Helpdesk, calls, tickets, resolution time | support, customer care, ticket, response |
| **Trust & Fraud** | Scam accusations, unauthorized debits, regulatory fear | fraud, scam, unauthorized, sebi |

## How assignment works

1. **Primary (LLM):** Phase 2 `ThemeClusterer` prompts Groq to use **only** the names above.  
2. **Fallback:** If Groq is unavailable or rate-limited, `cluster_by_keywords()` scores review text against the keyword lists in `shared/groww_product_map.py`.  
3. **Sentiment per area:** Derived from average star rating of reviews mapped to that area (≥3.5★ positive, ≤2.5★ negative, else neutral).

## Sentiment icons (reports & dashboard)

| Label | Meaning |
|-------|---------|
| positive | Mostly 4–5★ reviews in that area |
| negative | Mostly 1–2★ reviews in that area |
| neutral | Mixed or 3★-heavy |

## Priority icons (action items)

| Priority | Use when |
|----------|----------|
| **high** | Revenue/trust/stability risk; many 1★ reviews |
| **medium** | Clear pain but narrower blast radius |
| **low** | Nice-to-have / smaller volume |

## Week-over-week

Themes use the **same area names** each week so the dashboard can show rising/falling areas (e.g. “Trust & Fraud +12 mentions vs 2026-W20”). Two weekly snapshots in SQLite are required for WoW.
