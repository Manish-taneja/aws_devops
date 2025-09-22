# Cursor Build Plan — Copy-Paste Prompt Series

> Use these in Cursor (or any codegen agent). Each step has **Goal**, **Prompt**, and **Accept/Verify**.

## Overview

This build plan provides a comprehensive, step-by-step approach to implementing the AI-Enabled Multi-Tenant MCP Server. Each phase builds upon the previous one, ensuring a solid foundation and incremental development.

---

## Phase 0 — Bootstrap & Environment Setup

### Goal
Monorepo scaffold with Next.js, FastAPI, infrastructure stubs.

### Prompt
```
Create a monorepo named "aws-mcp-iac" with:
- apps/web: Next.js (TypeScript, App Router), shadcn/ui, auth pages, /console and /audit pages.
- apps/mcp-server: FastAPI (Python 3.12), uvicorn, pydantic, boto3, aioboto3, langgraph, MCP server scaffolding.
- packages/shared: python + ts shared types (OpenAPI clients later).
- iac/global + iac/platform + iac/modules + iac/stacks directories.
- policies/opa with placeholder rego files.
- workflows/plan.yml and apply.yml (placeholders).
- Root README with dev scripts, Makefile, taskfile.
Add devcontainer and pre-commit hooks for black, isort, ruff, eslint, prettier, tflint.
```

### Accept/Verify
- `pnpm dev` for web, `uvicorn main:app` for server
- Pre-commit runs

---

## Phase 1 — Authentication, Tenancy & Configurations

### Goal
Cognito auth + tenant model + multi-account configs + secure storage.

### Prompt
```
Implement Cognito User Pools auth for apps/web.
- Add /register and /login pages with MFA on.
- On first login, create a tenant if none exists; else join existing by invite code.
Add mcp-server models & DynamoDB tables: tenants, users, accounts, configs (PKs as ULIDs).
Create REST endpoints:
  POST /auth/register, POST /auth/login
  GET/POST/PUT /configs, POST /configs/select
Store AWS account configs: display_name, role_arn, default_region, required_tags, budget_limits.
Use AWS Secrets Manager for sensitive OAuth/issuer secrets (just the integration stub now).
Return JWT containing tenant_id, user_id, roles. Web should store and include it in API calls.
```

### Accept/Verify
- Can create tenant, add multiple configs, select active config at login header
- Items appear in DynamoDB

---

## Phase 2 — Intent Normalization & Policy Pre-check

### Goal
NL → structured intent; OPA pre-check before codegen.

### Prompt
```
Add an endpoint POST /nl/intent that:
- Accepts { query: string } and active config context.
- Calls a LangGraph pipeline to extract: action, params, constraints, env, cost_limit.
- Validates against JSON schema; returns normalized intent.
Add OPA policy call: deny if request violates pre-checks (env not allowed, region blocked, service blocked).
Return {intent, policy: pass|fail, reasons}.
In web /console, build NL input component that shows parsed intent and policy result.
```

### Accept/Verify
- Type prompt, see normalized JSON + pass/fail reasons

---

## Phase 3 — Terraform Blueprint Generation

### Goal
Generate TF from intent using approved modules; commit branch; create artifact.

### Prompt
```
Implement POST /iac/generate:
- Input: intent + selected config.
- Choose appropriate modules (e.g., vpc, alb, asg_ec2) and synthesize a stack in iac/stacks/<action>-<requestId>/.
- Render main.tf/variables.tf/outputs.tf with pinned providers, S3 backend (per workspace), tags from config.
- Commit to branch feature/<requestId> via GitHub API; push.
- Create artifact in DynamoDB with purpose, inputs, code_ref (git branch + S3 mirror), policy_passed=false, cost_estimate=null.
- Upload sources to S3 under s3://artifacts/<tenant>/<artifact_id>/src/.
Web: show the branch link & artifact_id.
```

### Accept/Verify
- Branch exists with TF code; artifact entry created

---

## Phase 4 — Plan Pipeline (CI Gates)

### Goal
Run plan gates + attach results to PR.

### Prompt
```
Fill workflows/plan.yml:
- Triggers on PR to main from feature/*.
- Jobs: setup terraform, tflint; run terraform fmt/validate, tflint, Checkov, OPA/Regula, Infracost, terraform plan -out=plan.bin, terraform show -json plan.bin.
- Upload artifacts (plan.bin, plan.json, checkov report, opa summary, infracost diff) to S3 paths under artifacts/<tenant>/<artifact_id>/<run_id>/.
- Comment summary on PR with policy and cost results; fail job if hard gates violated.
- Update DynamoDB 'runs' and backpatch 'artifacts' with policy_passed & cost_estimate.
Ensure OIDC role assumption to AWS; use per-tenant workspace naming.
```

### Accept/Verify
- Opening PR from the branch triggers pipeline; PR shows plan + reports

---

## Phase 5 — Apply Pipeline (Protected)

### Goal
Approval-gated apply to selected workspace.

### Prompt
```
Implement workflows/apply.yml:
- Manual dispatch or PR merged to main → environment protection requiring 'approver' role.
- Re-run policy checks, then 'terraform apply plan.bin' in the workspace bound to selected config.
- Save apply logs, outputs.json to S3; update 'runs' with status final and link to CloudWatch log stream.
- Emit Slack/JSM webhook notification with changeTicket and run_id.
```

### Accept/Verify
- Apply only runs with approval; resources created; run is auditable

---

## Phase 6 — Audit & Artifacts UI

### Goal
Frontend tab to browse all commands, artifacts, runs.

### Prompt
```
Build /audit page:
- Filters: time range, user, config, status (planned/applied/failed), policy status.
- Cards list runs with: request text, parsed intent, approver, cost estimate, links to plan/apply logs, download TF, download plan.json.
- Detail drawer shows OPA violations (if any), cost breakdown, resource changes (adds/updates/destroys).
Add server APIs:
  GET /audit?tenant=...&filters=...
  GET /artifacts/{id}
  GET /runs/{id}
```

### Accept/Verify
- Can view history, download artifacts, inspect cost & policy results

---

## Phase 7 — Reuse & Blueprint Resolver

### Goal
Suggest previously approved TF blueprints.

### Prompt
```
Add a Blueprint Resolver:
- /nl/intent checks 'artifacts' for similar purpose/inputs under same tenant/config.
- If a match exists and policy_passed=true, suggest reuse with adjustable params (e.g., instance_count).
- On accept, create new branch using the prior blueprint as base and only change variables; re-run plan gates.
UI: Show "Reuse prior blueprint" callout with diff preview (vars).
```

### Accept/Verify
- Reuse suggestion shows; generates updated branch & PR quickly

---

## Phase 8 — Guardrails & Drift Detection

### Goal
Complete safety net.

### Prompt
```
Add OPA policies:
- Mandatory tags Owner, CostCenter, Purpose, Env.
- Enforce encryption for S3/EBS/RDS, deny public unless Tag AllowPublic=true and approver present.
- Region allow-list per tenant; instance type and count caps per env.
Add a scheduled job (GitHub Action cron) that:
- Runs 'terraform plan -detailed-exitcode' for active workspaces nightly.
- If drift detected or changes pending, open a task in JSM/Slack with context links.
```

### Accept/Verify
- OPA denies invalid TF; drift alerts appear

---

## Key Implementation Snippets

### OPA Allow-list (Example Skeleton)

```rego
package tf.guardrails

deny[msg] {
  input.resource.type == "aws_s3_bucket"
  not input.resource.encryption
  msg := "S3 bucket must enable encryption"
}

deny[msg] {
  input.resource.public == true
  not input.resource.tags["AllowPublic"] == "true"
  msg := "Public resource without explicit override"
}
```

### Artifact Record (DynamoDB JSON)

```json
{
  "artifact_id": "01JABCDE...",
  "tenant_id": "TEN123",
  "type": "terraform",
  "purpose": "web_tier_alb_asg",
  "inputs": {"instance_count": 3, "instance_type": "t3.medium", "region": "ap-south-1"},
  "code_ref": {"git": "feature/01JABCDE", "s3": "s3://artifacts/TEN123/01JABCDE/src/"},
  "env_constraints": ["dev","staging"],
  "policy_passed": true,
  "cost_estimate": 1200,
  "created_by": "user@org",
  "approved_by": "lead@org",
  "usage_count": 1,
  "created_at": "2025-09-22T15:30:00Z"
}
```

### GitHub Actions (OIDC to AWS) — Header Block

```yaml
permissions:
  id-token: write
  contents: read
env:
  AWS_REGION: ap-south-1
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_OIDC_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
```

---

## Rollout & Operations

### Environment Strategy
- **Environments**: sandpit → dev → staging → prod (separate workspaces & OIDC roles)

### Operational Runbooks

#### Security & Compliance
- Rotate CI OIDC role every 90 days
- Quarterly OPA policy review
- Regular security audits and penetration testing

#### Cost Management
- Infracost budgets per tenant
- Monthly cost reviews and optimization
- Automated cost alerts and thresholds

#### Disaster Recovery
- S3 cross-region replication for artifacts
- DynamoDB PITR (Point-in-Time Recovery) enabled
- Regular backup testing and recovery procedures

#### Monitoring & Alerting
- CloudWatch dashboards for system health
- Automated alerts for failed deployments
- Performance monitoring and optimization

---

## Implementation Timeline

| Phase | Duration | Dependencies | Key Deliverables |
|-------|----------|--------------|------------------|
| Phase 0 | 1-2 days | None | Monorepo structure, dev environment |
| Phase 1 | 3-5 days | Phase 0 | Authentication, tenant management |
| Phase 2 | 2-3 days | Phase 1 | Intent processing, policy validation |
| Phase 3 | 4-6 days | Phase 2 | Terraform generation, artifact creation |
| Phase 4 | 3-4 days | Phase 3 | CI/CD pipeline, policy gates |
| Phase 5 | 2-3 days | Phase 4 | Protected apply pipeline |
| Phase 6 | 3-4 days | Phase 5 | Audit UI, artifact management |
| Phase 7 | 2-3 days | Phase 6 | Blueprint reuse system |
| Phase 8 | 3-4 days | Phase 7 | Guardrails, drift detection |

**Total Estimated Duration**: 20-30 days

---

## Success Criteria

### Technical Metrics
- [ ] All phases completed with acceptance criteria met
- [ ] 95% test coverage across all components
- [ ] Sub-8 minute plan pipeline execution time
- [ ] Zero security vulnerabilities in production

### Business Metrics
- [ ] Multi-tenant isolation working correctly
- [ ] Cost controls preventing budget overruns
- [ ] Audit trail capturing all infrastructure changes
- [ ] User adoption and satisfaction metrics

### Operational Metrics
- [ ] 99.9% uptime for critical services
- [ ] Mean time to recovery < 30 minutes
- [ ] Automated drift detection working
- [ ] Policy compliance at 100%

---

*This build plan provides a comprehensive roadmap for implementing the AI-Enabled Multi-Tenant MCP Server with strong security, audit, and cost controls.*
