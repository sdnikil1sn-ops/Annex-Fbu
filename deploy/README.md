# `deploy/` — Deployment Manifests

Production deployment assets for ANNEX (Phase 11). Backend services are
deployed to **Google Cloud Run**; the manifests in `cloudrun/` declare
the API and Celery-worker services as infrastructure-as-code.

## Layout

| Path | What it is |
|---|---|
| `cloudrun/api.yaml` | Cloud Run service: FastAPI (request-driven, scales to zero) |
| `cloudrun/worker.yaml` | Cloud Run service: Celery worker (one warm instance) |

## Apply

Both manifests contain `<placeholders>` that must be substituted for
your environment. The release pipeline
(`.github/workflows/release.yml`) publishes the image and can deploy
both services automatically once the Google Cloud secrets are configured.

Manual apply (substitute `REGION`, `PROJECT`, and every `<placeholder>`):

```bash
gcloud run services replace deploy/cloudrun/api.yaml --region REGION
gcloud run services replace deploy/cloudrun/worker.yaml --region REGION
```

See [`docs/guides/deployment.md`](../docs/guides/deployment.md) for the
full walkthrough: secret creation, Workload Identity Federation,
environment configuration, rollback, and troubleshooting.
