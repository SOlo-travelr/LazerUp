# Algorithms & AI Features

Deterministic, auditable scoring algorithms + LLM-assisted synthesis. LLMs extract and narrate; **numbers come from formulas** so results are explainable and reproducible.

---

## 1. Trend detection & scoring

Goal: detect **acceleration**, not just volume. A topic with steady high output isn't "trending"; one accelerating is.

For technology `t` over rolling windows, compute per signal `s ∈ {papers, patents, funding, grants}` a normalized **acceleration**:

$$
a_{t,s} = \frac{C_{t,s}^{\text{recent}} - C_{t,s}^{\text{prior}}}{C_{t,s}^{\text{prior}} + \epsilon}
$$

where `C^recent` is the count (or summed USD for funding) in the last window (e.g. 90d) and `C^prior` is the preceding equal window. Apply log-damping to tame explosive small bases:

$$
\tilde{a}_{t,s} = \operatorname{sign}(a_{t,s}) \cdot \ln(1 + |a_{t,s}|)
$$

Z-score each signal across all technologies, then composite:

$$
\text{TrendScore}_t = \sigma\!\Big( \sum_s w_s \cdot z(\tilde{a}_{t,s}) \Big),
\quad w = \{papers:0.30,\ patents:0.25,\ funding:0.30,\ grants:0.15\}
$$

`σ` (logistic) maps to 0..1. Weights are config, tuned against historical "known winners." Also flag **emerging** technologies: those with `C^prior ≈ 0` but rising `C^recent` (new-entrant detector), reported separately from established accelerators. Output → `trend_score` table, ranked.

**Mann-Kendall / linear-slope** on the monthly time series provides a significance check so we don't surface noise.

---

## 2. Opportunity detection engine

An opportunity = **demand signals high, supply (companies solving it) low, and it's buildable.** Combine four normalized factors per candidate technology/problem cluster:

| Factor | Meaning | Source |
|--------|---------|--------|
| `M` Momentum | trend score | `trend_score` |
| `F` Funding presence | normalized capital flowing in | `funding_event`, `grant_award` |
| `G` Gap | inverse startup density (few providers) | org counts on graph |
| `B` Buildability | inverse technical risk | LLM-assessed from bottleneck/literature maturity |

$$
\text{OppScore} = w_M M + w_F F + w_G G + w_B B,\quad w=\{0.30,0.25,0.30,0.15\}
$$

**Confidence** is separate from score — it reflects *evidence strength* (corpus volume, source diversity, recency):

$$
\text{Confidence} = \sigma\big(\alpha \ln(1+N_{docs}) + \beta\, \text{source\_diversity} + \gamma\, \text{recency}\big)
$$

**Pipeline:**
1. Candidate generation: cluster accelerating technologies + unsolved bottlenecks (vector clustering on `document_embedding`).
2. Quantitative scoring: compute `M,F,G,B`, `OppScore`, `Confidence` from tables (deterministic).
3. LLM brief generation: GPT-4o turns the evidence bundle into the structured brief (title, thesis, market, risk rationale) — **grounded** in the numbers, not inventing them.
4. Persist to `opportunity`.

Produces the target shape:
```
Opportunity: AI-based solid-state battery design platform
Evidence: +45% papers, 23 patents, $200M invested, few software providers
Market: Battery startups | Technical risk: Medium | Commercial: High | Confidence: 85%
```

---

## 3. White-space detection

White space = **research rising + funding present + startup density low**. For technology `t`:

$$
\text{WhiteSpace}_t = R_t \cdot \mathbb{1}[F_t > \tau_F] \cdot (1 - D_t)
$$

- `R` = normalized research activity/growth (papers+patents acceleration).
- `F` = normalized funding presence; gate `τ_F` ensures money is actually moving.
- `D` = startup density = normalized count of startups linked to `t` via `graph_edge`.

High `R`, funding above threshold, low `D` → high score. Rank, attach LLM rationale, persist to `white_space`. Contrast with **overcrowded** detection (high `D`, decelerating `R`) to answer "which areas are overcrowded."

---

## 4. Technical bottleneck finder

Identify recurring **unsolved challenges** across literature.

1. **Extraction:** during ingestion, an LLM function-call pulls a `problems_unsolved: [{statement, technology}]` array from each paper's abstract/conclusion ("remains challenging", "open problem", "limited by", "not yet achieved").
2. **Normalization:** embed each problem statement; cluster (HDBSCAN/agglomerative on cosine) so paraphrases collapse to one canonical bottleneck.
3. **Scoring:** `frequency` = #docs in cluster; `severity` = freq × recency × breadth (distinct authors/orgs). Rising frequency = an unsolved-and-worsening pain point.
4. Persist to `bottleneck` with `supporting_docs`. Feeds the opportunity engine (a high-severity bottleneck with funding + low startup density is a prime opportunity).

---

## 5. Founder Fit Score

Rank opportunities for a founder by matching expertise to what the opportunity demands.

**Inputs:** founder education, skills, experience, research areas → composed into a profile embedding (`founder_profile.embedding`) plus a structured skills set.

**Hybrid score** (semantic + symbolic, so it's both flexible and explainable):

$$
\text{Fit} = w_1 \cos(\vec{p}, \vec{o}) + w_2\,\text{SkillJaccard} + w_3\,\text{DomainMatch} + w_4\,\text{RiskAlignment}
$$

- `cos(p,o)` — profile embedding vs. opportunity embedding (captures latent overlap).
- `SkillJaccard` — overlap of founder skills with opportunity's required-capability tags.
- `DomainMatch` — research-area ↔ technology-category alignment.
- `RiskAlignment` — does founder's technical depth match the opportunity's technical risk (deep-tech PhD ↔ high-risk hardware).
- `w = {0.40, 0.25, 0.20, 0.15}`.

LLM generates the `rationale` and explicit `matched` / `gaps` lists from the computed overlap.

**Worked example** (founder: Mechanical Eng. PhD — solid-state batteries, COMSOL, multiphysics, fracture mechanics, HPC, AI/ML):

| Ranked opportunity | Fit | Why |
|---|---|---|
| AI-based solid-state battery design platform | 0.92 | SSB domain + COMSOL/multiphysics + AI/ML map directly to a simulation-driven design tool |
| Mechanics-informed dendrite/fracture prediction for Li-metal | 0.88 | Fracture mechanics + multiphysics + HPC are the core moat |
| Surrogate ML models for electrolyte screening (HPC→ML) | 0.81 | HPC + AI/ML + materials domain |
| Battery recycling process optimization | 0.46 | Weaker domain overlap, more process-chem than mechanics |

---

## 6. AI feature: Weekly Intelligence Report

Scheduled job (Celery Beat, Monday 06:00 UTC):
1. Pull top-N from `trend_score`, `grant_award`, `funding_event`, `patent`, `opportunity` for the week.
2. GPT-4o composes an executive narrative per section grounded in those rows.
3. Render JSON + PDF (HTML→PDF), store in `weekly_report` + S3, expose via API and email digest.

Sections: **Top technologies · Top grants · Top startups · Top patents · Top opportunities.**

---

## 7. AI feature: Opportunity Generator (autonomous idea creation)

Beyond surfacing detected opportunities, generate **novel startup ideas**: take a high-severity bottleneck + white-space pair, prompt GPT-4o to propose a concrete product/company concept (problem, solution, wedge, ICP, why-now), then **validate** it back against the corpus (does evidence support the "why now"?) and assign `OppScore`/`Confidence` before persisting. Generated ideas are flagged `source: generated` and held to the same scoring bar as detected ones.

---

## 8. RAG (semantic search & Ask)

- **Retrieval:** hybrid — pgvector ANN (cosine) on `document_embedding` ∪ Postgres FTS, reciprocal-rank fused, pre-filtered by SQL metadata (date/type/technology).
- **Re-rank:** top-50 → cross-encoder/LLM re-rank to top-8.
- **Generate:** GPT-4o answers strictly from retrieved context with inline citations; abstains/low-confidence when context is thin.
- **Caching:** semantic cache on normalized questions to cut cost.

---

## 9. Cost & quality controls

- Bulk extraction on `gpt-4o-mini`; synthesis/briefs/reports on `gpt-4o`.
- Embeddings batched (up to 2048 inputs/request), cached by `content_hash`.
- All scores stored with their component breakdown for auditability and A/B weight tuning.
- Backtesting harness: replay last 2 years, check the engine would have flagged known winners (e.g. LFP resurgence, sodium-ion) early → tune weights.
