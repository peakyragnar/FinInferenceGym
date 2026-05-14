"""Vendor-specific ingest pipelines.

Each submodule wraps a specific data source:
  - norgate: PIT fundamentals + prices, including delisted names
  - ibkr: live prices + options + execution
  - transcripts: Michael's 10-year / 1700-name speaker-tagged corpus
  - fred: free macro data (rates, yields, inflation)

All ingest writes through the canonical six-data-type schema with
versioned timestamps. Corpus-level biases (e.g., survivorship) are
flagged on the records they affect, not buried.
"""
