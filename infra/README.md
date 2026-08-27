# Leadsy Flock runtime (Google Cloud)

Provisioner of record: `scripts/provision_infra.sh` (idempotent gcloud).
This Terraform mirrors topics, buckets, and IAM so the layout is reviewable.
Model Armor templates and the Pub/Sub push subscription are still created by
the script because they depend on region filter support and the worker URL.

```bash
export GCP_PROJECT_ID=leadsy-flock
export GCP_REGION=asia-south1
bash scripts/provision_infra.sh

# After flock-worker is deployed:
export FLOCK_WORKER_URL="https://flock-worker-xxxxx.asia-south1.run.app"
bash scripts/provision_infra.sh
```

`runtime.json` is written by the provisioner (gitignored values may still be committed as names-only).
