#!/usr/bin/env bash
#
# GCP Infrastructure Setup for AI PR Code Review
#
# This script creates all the GCP resources needed to run AI-powered
# PR reviews in GitHub Actions using Workload Identity Federation.
#
# One-time setup per GCP project. Run once, then add the outputs
# as GitHub Secrets in your repository.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Permissions: roles/iam.workloadIdentityPoolAdmin,
#                  roles/iam.serviceAccountAdmin,
#                  roles/iam.serviceAccountKeyAdmin,
#                  roles/resourcemanager.projectIamAdmin
#   - Billing enabled on the project
#
# Usage:
#   export GCP_PROJECT_ID="my-project-123"
#   export GITHUB_ORG="my-github-username-or-org"
#   export GITHUB_REPO="my-repo-name"
#   bash scripts/gcp-setup.sh
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Configuration ───────────────────────────────────────────────────────────────

PROJECT_ID="${GCP_PROJECT_ID:-}"
GITHUB_ORG="${GITHUB_ORG:-}"
GITHUB_REPO="${GITHUB_REPO:-}"
POOL_NAME="github-actions"
PROVIDER_NAME="github"
SA_NAME="pr-reviewer"
SA_DISPLAY_NAME="PR Code Reviewer"
REGION="${GCP_REGION:-us-central1}"

# ── Validate inputs ────────────────────────────────────────────────────────────

if [ -z "$PROJECT_ID" ] || [ -z "$GITHUB_ORG" ] || [ -z "$GITHUB_REPO" ]; then
    echo "Usage:"
    echo "  export GCP_PROJECT_ID=\"my-project-123\""
    echo "  export GITHUB_ORG=\"my-gh-org\""
    echo "  export GITHUB_REPO=\"my-repo\""
    echo "  bash scripts/gcp-setup.sh"
    echo ""
    log_error "Missing required environment variables."
    exit 1
fi

log_info "Configuring GCP project: $PROJECT_ID"
log_info "GitHub: $GITHUB_ORG/$GITHUB_REPO"
log_info "Region: $REGION"

# ── Set project ────────────────────────────────────────────────────────────────

gcloud config set project "$PROJECT_ID"

# ── Enable APIs ────────────────────────────────────────────────────────────────

log_info "Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com
gcloud services enable iamcredentials.googleapis.com
gcloud services enable iam.googleapis.com

# ── Get project number ─────────────────────────────────────────────────────────

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
log_info "Project number: $PROJECT_NUMBER"

# ── Create Workload Identity Pool ──────────────────────────────────────────────

log_info "Creating Workload Identity Pool: $POOL_NAME..."
if gcloud iam workload-identity-pools describe "$POOL_NAME" \
    --project="$PROJECT_ID" --location="global" &>/dev/null; then
    log_warn "Pool '$POOL_NAME' already exists. Skipping creation."
else
    gcloud iam workload-identity-pools create "$POOL_NAME" \
        --project="$PROJECT_ID" \
        --location="global" \
        --display-name="GitHub Actions Pool"
    log_info "Pool created."
fi

# ── Create OIDC Provider ───────────────────────────────────────────────────────

log_info "Creating OIDC Provider: $PROVIDER_NAME..."
if gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --project="$PROJECT_ID" --location="global" \
    --workload-identity-pool="$POOL_NAME" &>/dev/null; then
    log_warn "Provider '$PROVIDER_NAME' already exists. Skipping creation."
else
    gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
        --project="$PROJECT_ID" \
        --location="global" \
        --workload-identity-pool="$POOL_NAME" \
        --display-name="GitHub OIDC Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
        --attribute-condition="assertion.repository_owner == '$GITHUB_ORG'" \
        --issuer-uri="https://token.actions.githubusercontent.com"
    log_info "Provider created."
fi

# ── Get provider resource name ─────────────────────────────────────────────────

PROVIDER_RESOURCE=$(gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --project="$PROJECT_ID" \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" \
    --format="value(name)")
log_info "Provider resource: $PROVIDER_RESOURCE"

POOL_RESOURCE="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME"
MEMBER="principalSet://iam.googleapis.com/${POOL_RESOURCE}/attribute.repository/$GITHUB_ORG/$GITHUB_REPO"

# ── Create Service Account ─────────────────────────────────────────────────────

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

log_info "Creating Service Account: $SA_EMAIL..."
if gcloud iam service-accounts describe "$SA_EMAIL" \
    --project="$PROJECT_ID" &>/dev/null; then
    log_warn "Service account '$SA_EMAIL' already exists. Skipping creation."
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="$SA_DISPLAY_NAME" \
        --project="$PROJECT_ID"
    log_info "Service account created."
fi

# ── Grant Vertex AI access to service account ──────────────────────────────────

log_info "Granting roles/aiplatform.user to $SA_EMAIL..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --condition=None &>/dev/null || log_warn "Role may already be granted."

# ── Allow GitHub Actions to impersonate the SA ─────────────────────────────────

log_info "Granting Workload Identity User to GitHub Actions pool..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="$MEMBER" \
    --condition=None &>/dev/null || log_warn "Binding may already exist."

# ── Output summary ─────────────────────────────────────────────────────────────

log_info "Waiting for propagation (IAM can take ~2 minutes)..."
sleep 10

echo ""
echo "=============================================="
echo "  GCP Setup Complete"
echo "=============================================="
echo ""
echo "Add these to your GitHub repo secrets"
echo "(Settings > Secrets and variables > Actions):"
echo ""
echo "  GCP_PROJECT_ID:                  $PROJECT_ID"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER:  $PROVIDER_RESOURCE"
echo "  GCP_SERVICE_ACCOUNT:             $SA_EMAIL"
echo "  GCP_REGION:                      $REGION"
echo ""
echo "Optional secrets:"
echo "  GEMINI_MODEL:                    gemini-2.5-pro  (or gemini-2.5-flash)"
echo ""
echo "=============================================="
echo ""
echo "To verify authentication works:"
echo ""
echo "  gcloud iam service-accounts get-iam-policy $SA_EMAIL --project=$PROJECT_ID"
echo ""
echo "To clean up (if needed):"
echo ""
echo "  gcloud iam service-accounts delete $SA_EMAIL --project=$PROJECT_ID"
echo "  gcloud iam workload-identity-pools providers delete $PROVIDER_NAME \\"
echo "    --project=$PROJECT_ID --location=global --workload-identity-pool=$POOL_NAME"
echo "  gcloud iam workload-identity-pools delete $POOL_NAME \\"
echo "    --project=$PROJECT_ID --location=global"
echo ""
