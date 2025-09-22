# AI-Enabled Multi-Tenant MCP Server (AWS-only)

## 1. Problem & Goals

### Problem
Teams need a safe, auditable way to ask in natural language for AWS infrastructure changes and get **reviewable Terraform** (plan → approval → apply), per user/account.

### Primary Goals

- **Multi-tenant**: Each user/team maintains multiple AWS accounts/configs; select at login
- **AI → Terraform**: Normalize NL intent → generate Terraform, run **policy & cost** gates, produce **plan**, apply after approval
- **Auditability**: Frontend shows command history, artifacts (Terraform, plans, applies), approvers, and costs
- **Reusability**: Store generated Blueprints (Terraform + metadata) for reuse on future requests

### Non-Goals

- No direct "unreviewed" CLI mutation path
- No cross-cloud (AWS only)

## 2. High-Level Architecture (AWS)

### Core Components

- **Frontend**: Next.js (App Router), Auth UI, Tenant selection, "Command" console, "Audit & Artifacts" tab
- **MCP Server**: FastAPI + LangGraph agents (intent → Terraform), MCP tools exposed (generate, validate, plan, apply)
- **Orchestration**: GitHub Actions runners (or ECS Fargate self-hosted) perform `fmt/validate/tflint/Checkov/OPA/Infracost/plan/apply`

### State & Storage

- **DynamoDB**: `tenants`, `accounts`, `configs`, `users`, `sessions`, `artifacts`, `runs`
- **S3**: Terraform code, plans, reports, logs
- **Terraform state**: S3 backend + DynamoDB lock table (per env/workspace)

### Auth & Tenancy

- Cognito (users), JWT with `tenant_id`, **RBAC** via groups (`admin`, `approver`, `operator`, `viewer`)
- Each user can bind multiple **AWS account configs** (assume-role ARN, region, VPC prefs, tags)

### Security

- Secrets in **AWS Secrets Manager** (OIDC client secrets, Github tokens)
- **SCPs** at org level; **permission boundaries** for runners
- **OPA/Regula** policies + Checkov + Infracost gates

### Observability

- Structured logs (JSON) → CloudWatch Logs
- CloudTrail + CloudTrail Lake; Security Hub, GuardDuty
- Metrics: API latency, plan/apply durations, gated fails, cost deltas

## 3. Core Flows

### (A) First-time User

1. Register (Cognito) → create **tenant** (if new) or join existing → set **MFA**
2. Add **Account Config**: name, account alias, **role ARN**, default region, mandatory tags, budget guardrail, allowed services
3. Select **active config** at login (changeable in header)

### (B) NL Command → Terraform (Plan & Apply)

1. User types: "Create 3 t3.medium behind ALB in ap-south-1; max ₹1500/day"
2. **Intent Resolver** normalizes request; checks policy & budget constraints
3. **Blueprint Resolver**: find **approved module** or generate module/composition
4. Commit to `feature/<requestId>` branch; run **CI plan**:
   - fmt/validate/tflint → Checkov → **OPA/Regula** → **Infracost** → `terraform plan`
5. PR created with plan details + cost; approver reviews
6. On approval, **apply** in the selected config/workspace
7. **Artifacts** saved (Terraform, plan JSON, apply log), audit updated

### (C) Reuse

- User types same/variant intent → system suggests prior approved Blueprint, adjusts parameters, re-runs gates

## 4. Functional Requirements

- Multi-tenant, multi-account config store with **assume-role** per account
- Intent to Terraform with **pluggable modules** (VPC, ALB, ASG/EC2, RDS, S3, EKS)
- CI gates: fmt/validate, **tflint**, **Checkov**, **OPA/Regula**, **Infracost**, **terraform plan**
- UI: Login, Config selector, **Command console**, **Audit & Artifacts** (search, filter, download)
- RBAC: Only **approvers** can promote apply; **operators** can draft & plan
- Cost control: **Infracost** hard fail if budget threshold exceeded

## 5. Non-Functional Requirements

### Security
- MFA; encryption at rest; least privilege IAM; OIDC for CI; no public S3 by default

### Reliability
- State locking; retry on transient errors; drift detection job

### Performance
- P95 plan pipeline < 8 min; apply times vary by stack

### Scalability
- Per-tenant isolation in storage; ECS runners auto-scale

## 6. Data Model (DynamoDB)

| Table | Primary Key | Description |
|-------|-------------|-------------|
| `tenants` | `tenant_id` | name, created_by, plan |
| `users` | `user_id` | tenant_id, email, roles, mfa |
| `accounts` | `account_id` | tenant_id, name, **role_arn**, default_region, tag_policy, budget_limits |
| `configs` | `config_id` | tenant_id, account_id, env, workspace, defaults (tags, kms, vpc) |
| `artifacts` | `artifact_id` | tenant_id, type=terraform, purpose, inputs(json), code_ref(s3/git), policy_passed(bool), cost_estimate, created_by, approved_by, usage_count |
| `runs` | `run_id` | tenant_id, artifact_id, config_id, status, plan_uri, apply_uri, logs_uri, started_at, ended_at |

## 7. APIs (FastAPI)

### Authentication
- `POST /auth/register`
- `POST /auth/login`

### Configuration Management
- `GET/POST /configs` (CRUD per tenant)
- `POST /configs/select`

### Infrastructure as Code
- `POST /nl/intent` → returns normalized intent + safety evaluation
- `POST /iac/generate` → creates feature branch + artifact record
- `POST /iac/plan` → triggers CI plan; returns run_id
- `POST /iac/apply` → requires approval; returns run_id

### Audit & Artifacts
- `GET /audit` → list runs/artifacts (filters: tenant, user, config, time)
- `GET /artifacts/{id}` → metadata + S3 links

## 8. Frontend (Next.js)

### Pages
- `/login` - User authentication
- `/register` - User registration
- `/console` - Config selector + NL input
- `/audit` - Audit trail and artifacts

### Components
- `ConfigPicker` - AWS account/configuration selection
- `NLConsole` - Natural language command interface
- `RunTimeline` - Execution history visualization
- `ArtifactCard` - Terraform artifact display
- `PlanDiff` - Terraform plan comparison
- `CostBadge` - Cost estimation display

## 9. CI/CD

### GitHub Actions
- **OIDC to AWS**: `plan.yml`, `apply.yml`
- **Environment protection**: `apply.yml` requires approval + `changeTicket` input
- **Runners**: ECS Fargate in VPC with endpoints

## 10. Policy Guardrails

### OPA/Regula Policies
- Mandatory tags
- KMS encryption
- Region allow-list
- Instance type/size caps by env
- Max desired_capacity
- Deny public resources unless override tag & approver

### Service Control Policies (SCP)
- Deny `iam:*` (except pipeline role)
- Deny public S3
- Region allow-list

### Budget Controls
- Infracost threshold (fail if delta > limit)

## 11. Repository Structure

```
repo/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── mcp-server/          # FastAPI + LangGraph + MCP tools
├── iac/
│   ├── global/              # Org-level guards: SCPs, IAM SSO, logging
│   ├── platform/            # S3 state buckets, DDB lock, ECR, runners
│   ├── modules/             # VPC, ALB, ASG_EC2, RDS, EKS, S3, KMS
│   └── stacks/              # Compositions (web_tier, data_tier...)
├── policies/
│   ├── opa/                 # *.rego
│   ├── checkov/
│   └── regula/
├── workflows/
│   ├── plan.yml
│   └── apply.yml
├── packages/
│   └── shared/              # schema, clients, utils
└── docs/
    ├── ADRs/
    └── runbooks/
```

## 12. Implementation Phases

### Phase 1: Foundation
- [ ] Basic MCP server with FastAPI
- [ ] DynamoDB schema implementation
- [ ] Cognito authentication
- [ ] Basic Terraform generation

### Phase 2: Core Features
- [ ] Natural language intent processing
- [ ] CI/CD pipeline with gates
- [ ] Frontend console
- [ ] Audit trail

### Phase 3: Advanced Features
- [ ] Blueprint reuse system
- [ ] Advanced policy enforcement
- [ ] Cost optimization
- [ ] Multi-tenant isolation

### Phase 4: Production Readiness
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Monitoring and alerting
- [ ] Documentation and runbooks

---

*This PRD serves as the foundation for building a comprehensive AI-enabled infrastructure management platform focused on AWS services with strong security, audit, and cost controls.*
