# Monitoring

Clinical Copilot exposes Prometheus-compatible metrics at `/metrics`
(see Part 11 — `observability/metrics.py`) and structured JSON logs via
`structlog`.

This directory is reserved for future Grafana dashboard JSON exports
and Prometheus scrape-config files. `observability/dashboards.py`
(Part 11) already provides a `recommended_dashboard_panels()` helper
describing the panels a dashboard here should include.

To scrape metrics locally, point Prometheus at:

```yaml
scrape_configs:
  - job_name: clinical-copilot
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
```

Celery task monitoring: `flower` is included as a dependency; run it
against the same Redis broker to get a live task dashboard:

```bash
uv run celery -A worker.celery_app flower --port=5555
```
```

=================================================
FILE: monitoring/.gitkeep
=================================================

```