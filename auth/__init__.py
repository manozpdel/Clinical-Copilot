"""Authentication layer for Clinical Copilot.

This package provides password hashing, JWT issuance/verification,
Google OAuth ID token validation, the current-user FastAPI dependency,
request/response schemas, and the AuthService orchestrating
registration, login, refresh, and Google login. No persistence
mechanics or routing logic lives here.
"""
