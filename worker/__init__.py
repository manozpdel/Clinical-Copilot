"""Celery background task layer for Clinical Copilot.

Reuses existing business logic (evaluation, embeddings, feedback
analytics) as async task wrappers, backed by Redis as broker and
result store. No pipeline logic is duplicated here.
"""
