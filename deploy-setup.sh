#!/usr/bin/env bash
#
# One-time GCP setup for deploying Housing Boba Index to Cloud Run
# via GitHub Actions.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud init)
#   - An existing GCP project
#
# Usage:
#   chmod +x deploy-setup.sh
#   ./deploy-setup.sh YOUR_PROJECT_ID
#

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy-setup.sh YOUR_PROJECT_ID}"
REGION="us-west1"
SERVICE_ACCOUNT="github-deploy"
REPO_NAME="housing-boba-index"

echo "==> Setting project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

echo "==> Enabling required APIs"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

echo "==> Creating Artifact Registry repository"
gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Housing Boba Index container images" \
  2>/dev/null || echo "    (repository already exists)"

echo "==> Creating service account for GitHub Actions"
gcloud iam service-accounts create "${SERVICE_ACCOUNT}" \
  --display-name="GitHub Actions deployer" \
  2>/dev/null || echo "    (service account already exists)"

SA_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Granting IAM roles to ${SA_EMAIL}"
for ROLE in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --quiet
done

echo "==> Creating service account key"
KEY_FILE="gha-deploy-key.json"
gcloud iam service-accounts keys create "${KEY_FILE}" \
  --iam-account="${SA_EMAIL}"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Now add these secrets to your GitHub repo"
echo "(Settings > Secrets and variables > Actions):"
echo ""
echo "  GCP_PROJECT_ID = ${PROJECT_ID}"
echo "  GCP_REGION     = ${REGION}"
echo "  GCP_SA_KEY     = (paste contents of ${KEY_FILE})"
echo ""
echo "Then push to main to trigger the deploy."
echo ""
echo "IMPORTANT: Delete ${KEY_FILE} after adding it to GitHub secrets."
echo "           Do NOT commit it to the repository."
