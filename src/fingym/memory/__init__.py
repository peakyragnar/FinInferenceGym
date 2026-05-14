"""Memory and promotion (Layer 4).

Versioned, model-readable artifacts: skills, hypotheses, observations,
lessons. Stored as YAML files in memory_registry/ (in git for audit
history). Any model can read and propose modifications.

Promotion gate: any memory addition must survive
  1. held-out replay calibration on ≥2 of 4 split types (time, regime,
     sector, cross-model)
  2. live calibration over a 2-week probationary period
  3. process discipline (Bayesian update, not price-chasing)
  4. cross-model regression (validated under ≥2 model engines)
  5. survivorship check (against delisted shadow universe, for
     transcript-derived skills)
  6. domain-of-validity declaration (horizon, expression-type, sector
     tags)

Memory outlives any one model — this is how knowledge compounds across
model generations.

Architectural import boundary:
  - This package is read by agents/, cli/.
  - This package MUST NOT import from agents/.
"""
