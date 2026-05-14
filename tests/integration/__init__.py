"""Integration tests.

End-to-end tests across multiple layers:
  - Replay-vs-live parity tests (data spine)
  - Full agent loop on toy worlds
  - Promotion gate against held-out replay
  - Cross-model swap regression

Slower than unit and property tests; run on CI but not on every commit.
"""
