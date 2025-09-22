# Cursor Build Plan — Super Multi-Agent AWS MCP Server

> **Purpose**: This document provides step-by-step prompts for building the Super Multi-Agent AWS MCP Server using Cursor AI. Each phase builds upon the previous one, creating a comprehensive AWS automation platform.

---

## Phase 0 — Repository Bootstrap & Local Runner Setup

### 🎯 Goal
Create the minimal repository structure with MCP server skeleton and Docker-based execution runner for isolated, secure command execution.

### 📋 Cursor Prompt

```markdown
Create a comprehensive repository called "aws-super-mcp" with the following structure:

**Repository Structure:**
```
aws-super-mcp/
├── mcp_server/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── infra/                 # Infrastructure agent (Terraform)
│   │   │   └── __init__.py
│   │   ├── config/                # Configuration agent (Ansible)
│   │   │   └── __init__.py
│   │   ├── ops/                   # Operations agent (AWS CLI/SSM)
│   │   │   └── __init__.py
│   │   ├── cost/                  # Cost management agent
│   │   │   └── __init__.py
│   │   ├── security/              # Security agent (GuardDuty, Security Hub)
│   │   │   └── __init__.py
│   │   ├── monitor/               # Monitoring agent (CloudWatch)
│   │   │   └── __init__.py
│   │   └── ml/                    # Machine Learning agent (Bedrock, SageMaker)
│   │       └── __init__.py
│   └── core/
│       ├── __init__.py
│       ├── auth.py                # Authentication and authorization
│       ├── classifier.py          # Intent classification
│       ├── schemas.py             # Pydantic models and schemas
│       ├── artifacts.py           # Artifact management
│       └── executor.py            # Execution orchestration
├── tests/
│   ├── __init__.py
│   ├── test_health.py             # Basic health endpoint tests
│   └── conftest.py                # Pytest configuration
├── scripts/
│   ├── dev.sh                     # Development server startup
│   ├── format.sh                  # Code formatting and linting
│   └── clean.sh                   # Cleanup temporary files
├── infra_examples/                # Example infrastructure templates
├── .work/                         # Temporary working directory (gitignored)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── Dockerfile                     # MCP runner container
├── docker-compose.yml             # Local development setup
└── README.md                      # Quickstart guide
```

**Key Requirements:**

1. **FastAPI Application** (`mcp_server/main.py`):
   - Health endpoint: `GET /_health` → `{"ok": true, "timestamp": "ISO8601", "version": "0.1.0"}`
   - Version endpoint: `GET /_version` → `{"version": "0.1.0", "build": "dev"}`
   - CORS enabled for development
   - Request/response logging middleware
   - Error handling with structured responses

2. **Dependencies** (`requirements.txt`):
   ```
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   pydantic==2.5.0
   boto3==1.34.0
   aioboto3==12.3.0
   langgraph==0.0.20
   typer==0.9.0
   pytest==7.4.3
   pytest-asyncio==0.21.1
   moto[all]==4.2.14
   jinja2==3.1.2
   python-multipart==0.0.6
   python-dotenv==1.0.0
   ```

3. **Docker Setup**:
   - **Dockerfile**: Ubuntu-based image with AWS CLI, Terraform, Ansible, and Python
   - **docker-compose.yml**: Service named `mcp-runner` with volume mounts and environment variables
   - Container should have: AWS CLI v2, Terraform 1.6+, Ansible 6+, Python 3.11+

4. **Development Scripts**:
   - `scripts/dev.sh`: Start development server with auto-reload
   - `scripts/format.sh`: Run black, isort, and flake8
   - `scripts/clean.sh`: Clean up `.work/` directory and temporary files

5. **Testing Setup**:
   - Basic health endpoint test
   - Version endpoint test
   - Pytest configuration with async support

6. **Documentation**:
   - README.md with quickstart instructions
   - Environment variables documentation
   - API endpoint documentation

**Implementation Notes:**
- Use Python 3.11+ features
- Implement proper error handling and logging
- Set up development environment with hot reload
- Ensure all imports work correctly
- Add proper type hints throughout
```

### 🧪 Testing & Validation

**Setup Commands:**
```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v

# Start development server
UVICORN_RELOAD=true ./scripts/dev.sh
```

**Validation Commands:**
```bash
# Test health endpoint
curl http://localhost:8000/_health

# Test version endpoint
curl http://localhost:8000/_version

# Test Docker setup
docker-compose up -d mcp-runner
docker-compose exec mcp-runner aws --version
docker-compose exec mcp-runner terraform --version
```

### ✅ Acceptance Criteria
- [ ] All tests pass (`pytest -v`)
- [ ] Health endpoint returns `{"ok": true, "timestamp": "...", "version": "0.1.0"}`
- [ ] Version endpoint returns version information
- [ ] Docker container starts successfully
- [ ] AWS CLI, Terraform, and Ansible are available in container
- [ ] Development server starts with hot reload
- [ ] Code formatting script works
- [ ] README provides clear setup instructions

---

## Phase 1 — Intent Classification & Schema Definition

### 🎯 Goal
Implement natural language intent classification system with typed schemas to route user requests to appropriate agents.

### 📋 Cursor Prompt

```markdown
Implement the core intent classification system with the following components:

**1. Schema Definitions** (`mcp_server/core/schemas.py`):

```python
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

class AgentType(str, Enum):
    INFRA = "infra"
    CONFIG = "config"
    OPS = "ops"
    COST = "cost"
    SECURITY = "security"
    MONITOR = "monitor"
    ML = "ml"

class IntentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Natural language input")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    user_id: Optional[str] = Field(None, description="User identifier")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")

class IntentResponse(BaseModel):
    agent: AgentType = Field(..., description="Selected agent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    params: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Identified constraints")
    reasoning: str = Field(..., description="Explanation of classification decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**2. Intent Classifier** (`mcp_server/core/classifier.py`):

```python
import re
from typing import Dict, List, Tuple
from .schemas import AgentType, IntentRequest, IntentResponse

class IntentClassifier:
    def __init__(self):
        self.patterns = {
            AgentType.INFRA: [
                r'\b(create|provision|deploy|build|setup)\b',
                r'\b(vpc|rds|alb|elb|eks|ec2|s3|lambda|api gateway)\b',
                r'\b(infrastructure|infra|cloudformation|terraform)\b',
                r'\b(instance|cluster|database|bucket|function)\b'
            ],
            AgentType.CONFIG: [
                r'\b(install|configure|setup|patch|update)\b',
                r'\b(nginx|apache|mysql|postgres|redis|docker)\b',
                r'\b(package|service|daemon|application)\b',
                r'\b(ansible|chef|puppet|configuration)\b'
            ],
            AgentType.OPS: [
                r'\b(start|stop|restart|reboot|describe|list)\b',
                r'\b(ssm|run-command|execute|run)\b',
                r'\b(operational|operations|ops|maintenance)\b',
                r'\b(status|health|check|monitor)\b'
            ],
            AgentType.COST: [
                r'\b(cost|budget|spend|billing|price)\b',
                r'\b(infracost|cost optimization|savings)\b',
                r'\b(estimate|forecast|analysis)\b',
                r'\b(expensive|cheap|optimize)\b'
            ],
            AgentType.SECURITY: [
                r'\b(guardduty|security hub|iam|kms|encryption)\b',
                r'\b(security|vulnerability|threat|compliance)\b',
                r'\b(scan|audit|policy|permission)\b',
                r'\b(public|private|access|firewall)\b'
            ],
            AgentType.MONITOR: [
                r'\b(cloudwatch|logs|metrics|x-ray|trail)\b',
                r'\b(monitor|alert|dashboard|graph)\b',
                r'\b(error|warning|critical|performance)\b',
                r'\b(trace|debug|investigate)\b'
            ],
            AgentType.ML: [
                r'\b(bedrock|sagemaker|comprehend|textract|rekognition)\b',
                r'\b(machine learning|ml|ai|artificial intelligence)\b',
                r'\b(model|training|inference|prediction)\b',
                r'\b(analyze|sentiment|classification|detection)\b'
            ]
        }
    
    def classify(self, request: IntentRequest) -> IntentResponse:
        text_lower = request.text.lower()
        scores = {}
        
        for agent_type, patterns in self.patterns.items():
            score = 0
            matches = []
            
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
                    matches.append(pattern)
            
            scores[agent_type] = {
                'score': score,
                'matches': matches,
                'confidence': min(score / len(patterns), 1.0)
            }
        
        # Select agent with highest confidence
        best_agent = max(scores.keys(), key=lambda k: scores[k]['confidence'])
        best_score = scores[best_agent]
        
        # Extract basic parameters
        params = self._extract_params(request.text)
        constraints = self._extract_constraints(request.text)
        
        return IntentResponse(
            agent=best_agent,
            confidence=best_score['confidence'],
            params=params,
            constraints=constraints,
            reasoning=f"Matched {len(best_score['matches'])} patterns: {', '.join(best_score['matches'][:3])}"
        )
    
    def _extract_params(self, text: str) -> Dict[str, Any]:
        params = {}
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', text)
        if numbers:
            params['count'] = int(numbers[0])
        
        # Extract regions
        regions = re.findall(r'\b(us-east-1|us-west-2|ap-south-1|eu-west-1)\b', text.lower())
        if regions:
            params['region'] = regions[0]
        
        # Extract instance types
        instance_types = re.findall(r'\b(t\d+\.\w+|m\d+\.\w+|c\d+\.\w+)\b', text.lower())
        if instance_types:
            params['instance_type'] = instance_types[0]
        
        return params
    
    def _extract_constraints(self, text: str) -> Dict[str, Any]:
        constraints = {}
        
        # Extract cost constraints
        cost_match = re.search(r'\$(\d+)', text)
        if cost_match:
            constraints['max_cost'] = int(cost_match.group(1))
        
        # Extract time constraints
        if 'urgent' in text.lower() or 'asap' in text.lower():
            constraints['priority'] = 'high'
        
        return constraints
```

**3. API Endpoint** (add to `mcp_server/main.py`):

```python
from fastapi import APIRouter, HTTPException
from mcp_server.core.schemas import IntentRequest, IntentResponse, ErrorResponse
from mcp_server.core.classifier import IntentClassifier

router = APIRouter()
classifier = IntentClassifier()

@router.post("/nl/intent", response_model=IntentResponse)
async def classify_intent(request: IntentRequest):
    try:
        result = classifier.classify(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Intent classification failed: {str(e)}"
        )
```

**4. Unit Tests** (`tests/test_classifier.py`):

```python
import pytest
from mcp_server.core.schemas import IntentRequest
from mcp_server.core.classifier import IntentClassifier

class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()
    
    def test_infrastructure_classification(self):
        request = IntentRequest(text="create 2 ec2 instances with alb in ap-south-1")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "infra"
        assert result.confidence > 0.5
        assert result.params.get('count') == 2
        assert result.params.get('region') == 'ap-south-1'
    
    def test_configuration_classification(self):
        request = IntentRequest(text="install nginx and configure ssl")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "config"
        assert result.confidence > 0.5
    
    def test_operations_classification(self):
        request = IntentRequest(text="start all ec2 instances tagged with env=prod")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "ops"
        assert result.confidence > 0.5
    
    def test_cost_classification(self):
        request = IntentRequest(text="what is my daily ec2 spend in us-east-1")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "cost"
        assert result.confidence > 0.5
    
    def test_security_classification(self):
        request = IntentRequest(text="scan all s3 buckets for public access")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "security"
        assert result.confidence > 0.5
    
    def test_monitoring_classification(self):
        request = IntentRequest(text="show cloudwatch logs for lambda function")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "monitor"
        assert result.confidence > 0.5
    
    def test_ml_classification(self):
        request = IntentRequest(text="analyze sentiment using bedrock")
        result = self.classifier.classify(request)
        
        assert result.agent.value == "ml"
        assert result.confidence > 0.5
```

**Implementation Requirements:**
- Add proper error handling and validation
- Include comprehensive logging
- Add type hints throughout
- Implement parameter extraction for common patterns
- Add confidence scoring based on pattern matches
- Include reasoning for classification decisions
```

### 🧪 Testing & Validation

**Test Commands:**
```bash
# Run unit tests
pytest tests/test_classifier.py -v

# Test API endpoint
curl -X POST localhost:8000/nl/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "create 2 ec2 instances with alb in ap-south-1"}'

# Test different agent types
curl -X POST localhost:8000/nl/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "install nginx and configure ssl"}'

curl -X POST localhost:8000/nl/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "what is my daily ec2 spend"}'
```

### ✅ Acceptance Criteria
- [ ] All classifier tests pass
- [ ] Infrastructure requests are classified as "infra" agent
- [ ] Configuration requests are classified as "config" agent
- [ ] Operations requests are classified as "ops" agent
- [ ] Cost requests are classified as "cost" agent
- [ ] Security requests are classified as "security" agent
- [ ] Monitoring requests are classified as "monitor" agent
- [ ] ML requests are classified as "ml" agent
- [ ] Confidence scores are between 0.0 and 1.0
- [ ] Basic parameters are extracted (count, region, instance_type)
- [ ] API returns structured JSON responses
- [ ] Error handling works for invalid inputs

---

## Phase 2 — Infrastructure Agent (Terraform Integration)

### 🎯 Goal
Implement the Infrastructure Agent with Terraform integration to generate, plan, and apply infrastructure changes with proper safety controls and audit logging.

Paste into Cursor (Prompt 2):

Inside agents/infra:
- Implement generator that creates a minimal Terraform stack (provider aws with region param, one security group, one t3.micro EC2) using Jinja2 templates.
- Create executor to run local Terraform in a temp workspace directory under .work/requests/<request_id>.
- Expose endpoints:
  POST /infra/generate {text, region, instance_type, count}
    -> writes files main.tf, variables.tf, outputs.tf; returns {request_id, dir}
  POST /infra/plan {request_id, aws_profile}
  POST /infra/apply {request_id, aws_profile, approve:boolean}
  POST /infra/destroy {request_id, aws_profile, approve:boolean}

Safety:
- plan/apply/destroy run Terraform via the Docker mcp-runner container (docker-compose service).
- Log stdout/stderr to .work/requests/<id>/logs/*.log and return tail pointers.
- If approve=false on apply/destroy, return preview-only.

Add a basic smoke test using moto for AWS API mocking (just for generation, not for real apply).


Run / Test (dry run + real in sandbox):

# Generate
curl -X POST localhost:8000/infra/generate -H "content-type: application/json" \
  -d '{"text":"create one ec2 in ap-south-1", "region":"ap-south-1", "instance_type":"t3.micro","count":1}'

# Plan (uses local TF; ensure docker compose is up)
export AWS_PROFILE=sandbox
curl -X POST localhost:8000/infra/plan -H "content-type: application/json" \
  -d '{"request_id":"<COPY_FROM_RESPONSE>","aws_profile":"sandbox"}'

# Apply (approve true)
curl -X POST localhost:8000/infra/apply -H "content-type: application/json" \
  -d '{"request_id":"<ID>","aws_profile":"sandbox","approve":true}'

# Destroy (cleanup)
curl -X POST localhost:8000/infra/destroy -H "content-type: application/json" \
  -d '{"request_id":"<ID>","aws_profile":"sandbox","approve":true}'


Accept when: you can create/destroy a t3.micro in your sandbox from Cursor.

Phase 3 — Config Agent (Ansible) minimal flow

Goal: Install NGINX on the newly created EC2 using SSM or SSH; dry-run then apply.

Paste into Cursor (Prompt 3):

Inside agents/config:
- Implement a playbook generator (playbook.yml) to install and start nginx (Amazon Linux 2).
- Inventory: dynamic via AWS tags (find EC2 by Tag:RequestId=<request_id>) OR by instance_id returned from infra outputs.
- Runner: execute 'ansible-playbook --check' first, then real run if approve=true.
- Endpoint:
  POST /config/generate {request_id, package:"nginx"}
  POST /config/dryrun {request_id}
  POST /config/apply {request_id, approve:boolean}
- Store logs under .work/requests/<id>/config/logs.

Note: Provide both SSH (keypair path from user) and SSM execution option; default to SSM if instance has SSM agent + IAM role.


Run / Test:

# Generate playbook for nginx
curl -X POST localhost:8000/config/generate -H "content-type: application/json" \
  -d '{"request_id":"<ID>","package":"nginx"}'

# Dry-run
curl -X POST localhost:8000/config/dryrun -H "content-type: application/json" \
  -d '{"request_id":"<ID>"}'

# Apply (approve)
curl -X POST localhost:8000/config/apply -H "content-type: application/json" \
  -d '{"request_id":"<ID>","approve":true}'


Accept when: playbook runs and NGINX is installed/running.

Phase 4 — Ops Agent (AWS CLI / SSM narrow allow-list)

Goal: Add a safe operational command runner for read-only and pre-approved mutations (e.g., start/stop tagged instances).

Paste into Cursor (Prompt 4):

Inside agents/ops:
- Implement allow-list policy (YAML/JSON): allowed actions + required filters (e.g., only instances with tag Owner=CTO-Office).
- Endpoint POST /ops/run {command, request_id, aws_profile}
  - Validate against allow-list (deny by default).
  - If allowed, execute inside docker mcp-runner, capture stdout/stderr.
  - For mutating actions, require approve=true field.

Add unit tests for validator.


Run / Test:

curl -X POST localhost:8000/ops/run -H "content-type: application/json" \
  -d '{"command":"aws ec2 describe-instances --filters Name=tag:RequestId,Values=<ID>","request_id":"<ID>","aws_profile":"sandbox"}'


Accept when: read-only commands work; disallowed mutations are blocked.

Phase 5 — Cost Agent (Cost Explorer + Infracost)

Goal: Query current spend and estimate TF changes before apply.

Paste into Cursor (Prompt 5):

Inside agents/cost:
- Implement GET daily EC2 spend by region via Cost Explorer.
- Implement Infracost integration:
  - Given a request_id, run 'infracost breakdown --path .work/requests/<id>'
  - Parse JSON, return monthly estimate and per-resource diffs.

Endpoints:
- POST /cost/query {dimension:"EC2", granularity:"DAILY", region:"ap-south-1"}
- POST /cost/estimate {request_id}


Run / Test:

curl -X POST localhost:8000/cost/query -H "content-type: application/json" \
  -d '{"dimension":"EC2","granularity":"DAILY","region":"ap-south-1"}'

curl -X POST localhost:8000/cost/estimate -H "content-type: application/json" \
  -d '{"request_id":"<ID>"}'


Accept when: you get a numeric estimate JSON from Infracost.

Phase 6 — Security Agent (GuardDuty/Security Hub quick wins)

Goal: Basic posture checks: list Security Hub findings for the account/region; simple S3 public bucket scan via AWS APIs.

Paste into Cursor (Prompt 6):

Inside agents/security:
- Endpoint POST /security/findings {service:"securityhub", severity_min:"LOW"}
  -> returns recent findings summary.
- Endpoint POST /security/s3_public_scan {}
  -> lists buckets and flags public ACLs/Policies (coarse MVP).
- Structure responses with actionable items and resource ARNs.
- Store JSON reports under .work/security/<timestamp>.json


Run / Test:

curl -X POST localhost:8000/security/findings -H "content-type: application/json" -d '{"service":"securityhub","severity_min":"LOW"}'
curl -X POST localhost:8000/security/s3_public_scan -H "content-type: application/json" -d '{}'


Accept when: you see findings / scan results.

Phase 7 — Monitoring Agent (CloudWatch logs + metrics)

Goal: Fetch recent logs from an EC2 or Lambda and basic CPU metric from EC2.

Paste into Cursor (Prompt 7):

Inside agents/monitor:
- Endpoint POST /monitor/logs {log_group, start_minutes}
  -> fetch last N minutes events using filterLogEvents
- Endpoint POST /monitor/metrics {namespace, metric_name, dimensions, period, stat, start_minutes}
  -> fetch metric stats (e.g., CPUUtilization for EC2)
Return JSON plus a small ASCII sparkline summary in text for quick terminal read.


Run / Test:

curl -X POST localhost:8000/monitor/metrics -H "content-type: application/json" \
  -d '{"namespace":"AWS/EC2","metric_name":"CPUUtilization","dimensions":[{"Name":"InstanceId","Value":"<YOUR_INSTANCE_ID>"}],"period":300,"stat":"Average","start_minutes":60}'


Accept when: metrics JSON returns and ASCII summary is shown.

Phase 8 — ML Agent (Bedrock one-shot)

Goal: Call Bedrock to summarize the plan output or generate a policy hint.

Paste into Cursor (Prompt 8):

Inside agents/ml:
- Endpoint POST /ml/bedrock_summarize_plan {request_id}
  -> reads .work/requests/<id>/plan.json, sends to Bedrock model (e.g., Claude) for human-readable summary and risk hints.
- Make model ARN and region configurable via env.
- Return summary text + suggested tags or guardrails.

Add a small unit test with a mocked response.


Run / Test:

curl -X POST localhost:8000/ml/bedrock_summarize_plan -H "content-type: application/json" \
  -d '{"request_id":"<ID>"}'


Accept when: you get a readable summary.

Phase 9 — Audit & Artifacts (local JSON index)

Goal: Minimal audit index without DynamoDB (yet). Track all runs/artifacts to a local JSON db.

Paste into Cursor (Prompt 9):

Implement mcp_server/core/artifacts.py:
- Local artifact index: .work/index.json
- Functions: record_event(type, request_id, path, metadata), list_events(filters)
- Add hooks in each agent to record generation, plan, apply, config runs, ops runs, cost/security/monitor outputs.

Add endpoints:
- GET /audit/list
- GET /audit/request/{request_id}
Return structured records with links to local files.


Run / Test:

curl localhost:8000/audit/list
curl localhost:8000/audit/request/<ID>


Accept when: you can see a history of what you did across phases.

Hardening & Safety (still terminal-only)

Add approval booleans for any mutating action (apply, destroy, ops mutations).

Make region & profile explicit inputs.

Restrict ops allow-list to read-only initially; enable start/stop only for instances with Tag:Owner=you.

Add .env with AWS_PROFILE, default region, Bedrock model.

Add scripts/clean.sh to tear down .work and temporary TF states.

What next (after all phases pass)

Swap local TF state → S3+DynamoDB lock (in a dedicated “platform” bootstrap TF).

Replace local audit index → DynamoDB + S3 artifacts.

Introduce OPA/Checkov/Infracost gates in a CI job (GitHub Actions or local runner container).

Front-end (Next.js) with login + config picker + console + audit tabs.

Tenantization: per-tenant configs (assume-role), per-tenant artifact prefixes, execution isolation.