"""Semantic exit codes for agent-friendly scripting.

Exit codes match the convention established by modelslab-cli and common
Unix tool practices so agents can branch on specific failure types.
"""

OK            = 0   # Success
ERROR         = 1   # Generic / unclassified error
AUTH_ERROR    = 3   # Missing or invalid API key
RATE_LIMITED  = 4   # 429 Too Many Requests
NOT_FOUND     = 5   # 404 — resource or model not found
BILLING_ERROR = 6   # Insufficient credits / payment required
TIMEOUT       = 7   # Generation timed out
VALIDATION    = 8   # Bad input / schema validation failure
