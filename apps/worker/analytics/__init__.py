"""Deterministic analytics engines (docs/ALGORITHMS.md).

All scores are produced by auditable formulas; the LLM (when configured) only
narrates the evidence. Every engine reads from the relational/vector store and
persists its results into the derived tables (trend_score, opportunity,
white_space, bottleneck, weekly_report).
"""
