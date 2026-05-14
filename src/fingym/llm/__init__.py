"""Model swap layer.

The ONLY place in the codebase that imports specific LLM provider SDKs
(anthropic, openai, google). Enforces DESIGN.md #7: intelligence lives
in architecture, not in weights/prompts; models are swappable engines.

Submodules:
  - contract: typed Protocol defining the model-interface contract.
    Raw evidence in, structured terminal output out.
  - anthropic, openai, google: concrete implementations.
  - openweights: Phase 5+ (Llama / Qwen / DeepSeek / etc., served via
    vllm locally or rented GPU).

Code outside this package never imports a provider SDK directly. The
no_hardcoded_models pre-commit lint enforces this structurally.

Model swap is a config change, not a code change.

Architectural import boundary:
  - This package is read by agents/, cli/.
  - This package MUST NOT import from anything outside src/fingym/llm/
    (no upward dependencies).
"""
