# Why Did This Break?

An experimental AI SRE agent that investigates infrastructure incidents using an LLM and explores how a specialized decision model can be used as a safety layer before consequential actions.

> **This is an engineering experiment, not a production SRE platform.**

## 🎯 Problem

Infrastructure incidents often require engineers to correlate multiple sources of evidence:

- application logs
- metrics
- deployments
- infrastructure state
- IAM configuration
- operational runbooks

The goal of this project is to explore whether an AI agent can perform this investigation systematically and explain its reasoning.

The second goal is to explore a newer model pattern:

> **Reasoning models for investigation + specialized decision models for constrained decisions.**

---

# 🏗️ Architecture

```text
                         Incident
                            |
                            v
                    +---------------+
                    | Strands Agent |
                    +-------+-------+
                            |
                        Groq LLM
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
            Logs         Changes         IAM
              |             |             |
              +-------------+-------------+
                            |
                            v
                       Root Cause
                            |
                            v
                    Proposed Action
                            |
                            v
                  +------------------+
                  |  Strands Decider |
                  |       2B         |
                  +--------+---------+
                           |
                     Decision score
                           |
                    +------+------+
                    |             |
                 Proceed         Deny
                    |
                    v
               Remediation
```

## 🔍 Example Incident

The synthetic incident is:

**Production application cannot write to S3**

Symptoms:

```text
HTTP 403
AccessDenied
PutObject
```

Recent change:

```text
Terraform IAM module modified
```

Infrastructure state:

```text
Expected:
s3:PutObject

Observed:
s3:GetObject
```

Expected root cause:

```text
The production IAM role lost s3:PutObject permission
during a recent Terraform change.
```

---

# 🤖 Agent Investigation

The Strands agent has five investigation tools:

```text
investigate_logs
investigate_metrics
investigate_recent_changes
investigate_infrastructure
investigate_runbook
```

The agent is instructed to:

1. Start from the incident symptoms.
2. Select useful evidence.
3. Generate hypotheses.
4. Confirm or reject hypotheses.
5. Avoid unsupported conclusions.
6. Identify the root cause.
7. Recommend remediation.
8. Explain verification.

The important point is that the agent does not receive every evidence source upfront.

It must decide what evidence to retrieve.

---

# 🧠 Decision Model Experiment

After the investigation, the agent may propose a consequential action.

For example:

```text
Restore s3:PutObject permission
```

Instead of immediately executing the action, the proposal is passed through a decision layer.

The decision model receives:

```text
State
+
Question
```

and returns a typed decision probability.

Example:

```text
Decision:
safe_to_proceed

Probability:
0.8233
```

The application then applies its own policy:

```text
probability >= 0.70
        |
        +----> PROCEED

probability < 0.70
        |
        +----> DENY
```

The important architectural separation is:

```text
LLM
↓
Reasoning

Decision Model
↓
Constrained decision

Application
↓
Policy enforcement
```

The decision model does not replace the reasoning model.

---

# 📊 CPU Benchmark

The Decider 2B experiment was run locally on a CPU-only environment.

Environment:

```text
PyTorch: 2.14.1+cpu
CUDA:    False
Device:  CPU
```

Five consecutive decision requests produced:

| Metric | Result |
|---|---:|
| Minimum | 43.28 sec |
| Maximum | 52.33 sec |
| Average | 48.21 sec |
| P50 | 47.47 sec |
| Decision probability | 0.7893 |

This result is important.

The experiment demonstrated that **model specialization alone does not guarantee useful end-to-end performance**.

On this development environment, placing the decision model before every investigation tool would add substantial latency.

Therefore the architecture uses the decision model selectively for higher-value decisions.

---

# ⚖️ Architectural Trade-off

### Bad approach

```text
LLM
 ↓
Decider
 ↓
logs

LLM
 ↓
Decider
 ↓
metrics

LLM
 ↓
Decider
 ↓
IAM

LLM
 ↓
Decider
 ↓
runbook
```

This introduces unnecessary decision overhead for read-only operations.

### Better approach

```text
LLM
 ↓
Investigation
 ↓
Root cause
 ↓
Proposed consequential action
 ↓
Decider
 ↓
Policy
 ↓
Action
```

Examples of actions that could justify a decision gate:

```text
Terraform apply
IAM modification
Deployment rollback
Resource deletion
Production restart
Security policy change
```

---

# 🔬 Evaluation

The initial evaluation checks whether the agent identifies the expected root cause using criteria such as:

```text
IAM
s3:PutObject
AccessDenied
Terraform
```

The investigation also records:

- tool trajectory
- tool count
- execution time
- Strands metrics
- Strands traces

The next evolution would be a larger evaluation dataset containing multiple incidents.

Potential evaluation metrics:

```text
Root-cause accuracy
Evidence groundedness
Tool-selection accuracy
Unnecessary tool calls
Unsafe actions
Latency
Token usage
Cost
Confidence calibration
```

---

# 🔐 Safety

This repository does **not** modify real AWS infrastructure.

The remediation action is simulated:

```text
SIMULATION ONLY
```

The Decider is used as an experimental policy/safety layer.

A production implementation would require additional controls such as:

- deterministic authorization
- human approval for high-risk actions
- least-privilege IAM
- audit logging
- action allowlists
- rollback mechanisms
- independent verification
- confidence calibration
- comprehensive evaluation

A model confidence score should **not** be treated as a security boundary by itself.

---

# 💡 Key Learning

The main lesson from this project was not simply how to use a new model.

It was understanding the different responsibilities inside an agent system.

```text
Reasoning Model
    |
    | What should I investigate?
    | What could be wrong?
    | What evidence matters?
    |
    v
Decision Model
    |
    | Should this constrained action proceed?
    |
    v
Application Policy
    |
    | Is this decision sufficient?
    |
    v
Tool / Action
```

The experiment also demonstrated an important engineering principle:

> **Don't add an AI component simply because it is new or technically interesting. Measure where it creates enough value to justify its latency, cost and complexity.**

---

# 🚀 Future Experiments

This project is intentionally small.

Potential future experiments include:

### 1. LLM-only vs LLM + Decider

Compare:

```text
LLM only
```

against:

```text
LLM + Decider
```

across multiple incidents.

### 2. More incidents

Add scenarios such as:

```text
IAM regression
Network connectivity failure
Bad deployment
Kubernetes resource issue
Database connectivity
Configuration regression
```

### 3. Better evaluation

Move beyond keyword evaluation toward:

```text
trajectory evaluation
evidence groundedness
tool-selection accuracy
confidence calibration
```

### 4. Hardware comparison

Compare:

```text
CPU
GPU
```

and measure warm/cold latency.

### 5. Real operational integration

Only after sufficient evaluation:

```text
Prometheus
CloudWatch
Kubernetes
AWS APIs
Terraform
GitOps
```

---

# 🧪 Status

**Status: Experimental POC**

The purpose of this project is learning and experimentation around:

- Agentic AI
- Strands Agents
- Tool calling
- Agent observability
- Agent evaluation
- Decision models
- AI safety/policy layers
- AI engineering trade-offs

It is not intended to be deployed directly into production.

---

# 📚 Technologies

- Python
- Strands Agents
- Strands Decider 2B
- Groq
- LiteLLM
- OpenTelemetry / Strands telemetry
- Pydantic
- Hugging Face
- PyTorch

---

# 🎥 Demo

Coming soon:

**Why Did This Break? — AI SRE Agent + Decision Model**

The demo walks through:

1. Production incident
2. Agent investigation
3. Evidence collection
4. Root-cause identification
5. Decision-model safety gate
6. CPU benchmark
7. Architectural lessons