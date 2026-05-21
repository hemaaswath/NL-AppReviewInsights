# Implementation Plan — App Review Insights Analyzer

## Current focus: Phase 2 @ Groq `llama-3.3-70b-versatile`

### Groq model limits (planning assumptions)

| Limit | Value | Implication |
|-------|-------|-------------|
| Requests / minute | **30** | ≥ **2.1 s** between LLM calls |
| Requests / day | **1,000** | ~**8–12 calls per run** → up to ~80–120 runs/day (weekly job uses ≪10) |
| Tokens / minute | **12,000** | No single prompt should spike near 12K; split corpus |
| Tokens / day | **100,000** | **Cannot** run per-review LLM sentiment on 1,000 reviews naïvely |

### Why 2,400 → 1,000 reviews

- Store as many normalized reviews as Phase 1 allows (e.g. 2,400).
- Phase 2 **analyses at most 1,000** per weekly run via **stratified sampling** (keeps 1★–5★ mix).
- Reporting still says `total_reviews_analysed: 1000` (or fewer if DB smaller).

### Naïve approach (do **not** use at 1,000 reviews)

| Step | Calls | Est. tokens (1K reviews) |
|------|-------|---------------------------|
| Sentiment, batch size 10 | **100** | **~160K+** (exceeds **100K TPD**) |
| Themes, full digest 1K × 100 chars | 1 | **~30K+ input** (risks **12K TPM** spike) |
| Quotes + actions | 2 | ~5K |
| **Total** | **103** | **Fails daily token cap** |

---

## Approved Phase 2 call strategy

Design goal: **one weekly run ≈ 7–11 Groq requests, ≈ 20–40K tokens**, safely under all limits.

```
┌─────────────────────────────────────────────────────────────────┐
│ DB: up to 2,400+ normalized reviews (Phase 1)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ stratified_sample(max=1000)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Analysis corpus: 1,000 reviews (counts + rating distribution)   │
└───┬─────────────────┬──────────────────┬────────────────────────┘
    │                 │                  │
    ▼                 ▼                  ▼
 Sentiment          Themes             Quotes + Actions
 (rating-based      (LLM ×1,           (LLM ×1 each)
  OR LLM sample)      200-review digest)
```

### Step-by-step

| # | Step | LLM calls | Input sizing | Notes |
|---|------|-----------|--------------|-------|
| 0 | Load & cap corpus | 0 | — | `PHASE2_MAX_REVIEWS=1000`, stratified by star rating |
| 1 | **Sentiment** | **0** (default) or **4–8** (optional) | — | **Default:** derive from stars for all 1,000 (≥4 positive, ≤2 negative, else neutral). **Optional:** LLM batches only if `N ≤ 150` or on a 80-review validation sample |
| 2 | **Themes** | **1** | 200 reviews × 80 chars digest | Never send all 1,000 reviews in one prompt |
| 3 | **Quotes** | **1** | 30 reviews × 120 chars | Unchanged pattern |
| 4 | **Actions** | **1** | Themes + 3 quotes + summary only | Small structured prompt |
| 5 | Throttle | — | `wait_for_groq_slot()` ~2.1s between calls | Respects 30 RPM |

### Token budget (target run)

| Step | Calls | Est. input | Est. output |
|------|-------|------------|-------------|
| Sentiment (rating-only) | 0 | 0 | 0 |
| Themes | 1 | ~6–8K | ~1K |
| Quotes | 1 | ~2.5K | ~0.5K |
| Actions | 1 | ~1.5K | ~0.5K |
| **Weekly total** | **3** | **~10–12K** | **~2K** |

With optional LLM sentiment sample (80 reviews, 4× batch 20):

| Step | Calls | Est. total tokens |
|------|-------|-------------------|
| Sentiment sample | 4 | ~12K |
| Themes + quotes + actions | 3 | ~14K |
| **Weekly total** | **7** | **~26K** |

Leaves headroom for **~3 full runs/day** under 100K TPD and hundreds of runs under 1K RPD.

---

## Configuration (`.env`)

```env
GROQ_MODEL=llama-3.3-70b-versatile
PHASE2_MAX_REVIEWS=1000
PHASE2_THEME_SAMPLE_SIZE=200
PHASE2_QUOTE_SAMPLE_SIZE=30
PHASE2_LLM_SENTIMENT_MAX=150
PHASE2_SENTIMENT_BATCH_SIZE=20
```

---

## Implementation checklist

### Phase 1 (data volume)

- [x] Normalization: English-only, ≥6 words, no emoji, PII scrub
- [ ] Collection target: up to **2,400** stored; Phase 2 reads capped **1,000**

### Phase 2 (code)

- [x] `shared/phase2_config.py` — limits and env defaults
- [x] `shared/phase2_sampling.py` — stratified cap at 1,000
- [x] `shared/groq_throttle.py` — 2.1s spacing between calls
- [x] `AnalysisOrchestrator` — sample corpus; rating sentiment at scale; pass subsets to cluster/quote
- [x] All Phase 2 LLM modules — default model `llama-3.3-70b-versatile`; throttle before `llm.invoke`
- [x] `ThemeClusterer` — digest capped at `PHASE2_THEME_SAMPLE_SIZE`
- [x] `run_phase2.py` — uses `PHASE2_MAX_REVIEWS` from env (default 1000)

### Phase 3–4

- No Groq usage; unchanged MCP path (saksham-mcp-server)

---

## Operational rules

1. **One weekly Phase 2 job** — avoid repeated full runs the same day unless debugging.
2. **Monitor Groq dashboard** — if 429/rate errors, increase throttle interval or disable LLM sentiment sample.
3. **Do not increase** `PHASE2_THEME_SAMPLE_SIZE` above ~250 without recalculating token math.
4. **Re-collect** after normalization changes; re-run Phase 2 with fresh `processed` flags if needed.

---

## Success criteria

| Metric | Target |
|--------|--------|
| Reviews in one analysis run | ≤ 1,000 |
| Groq requests per weekly run | ≤ 15 |
| Tokens per weekly run | ≤ 50,000 |
| No 429 / TPD exhaustion on normal weekly schedule | Yes |
| Insights quality | Themes/quotes/actions from representative sample; sentiment distribution from full 1K via ratings |

---

## Timeline (suggested)

| Week | Work |
|------|------|
| 1 | Apply Phase 2 code changes + verify on 73-review DB |
| 2 | Scale test with 1,000-review sample; tune `THEME_SAMPLE_SIZE` if needed |
| 3 | Full pipeline demo (Phases 1–4) + doc/screenshots |
