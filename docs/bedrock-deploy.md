# Runbook — Amazon Bedrock via the Converse API (managed provider)

Velocity's Bedrock backend uses the **Converse API**, which is foundation-model agnostic:
the same code path serves **any Converse-capable foundation model** with only a model-id
change (a config change, never a code change). This is the managed alternative to the
official self-hosted open-weights deployment — both are supported.

> **Status on our account (011531955488):** Bedrock is fully operational. **Amazon Nova
> Lite invokes successfully.** Some foundation models are entitlement-gated (403 "not
> available for this account") — so we run **Nova** here and **self-hosted open weights**
> as the official production path. Model choice is configuration only.

## 1. Pick a Converse-capable model
Default is **`amazon.nova-lite-v1:0`** (fast, cheap, available). For more headroom use
`amazon.nova-pro-v1:0`. Copy the exact id from Bedrock → Model catalog if unsure.

## 2. Least-privilege IAM
Dedicated user `velocity-hos-bedrock`, programmatic access, inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:Converse"],
    "Resource": ["arn:aws:bedrock:*::foundation-model/amazon.nova-*"]
  }]
}
```
(Add other model ARNs later if you enable them.) Create an access key; keep it secret.

## 3. Point Velocity at Bedrock
```bash
pip install boto3
export AWS_ACCESS_KEY_ID=...   AWS_SECRET_ACCESS_KEY=...   AWS_REGION=us-east-1
export VHOS_LLM_BACKEND=bedrock
export VHOS_EMBED_BACKEND=local          # go live without a Bedrock embeddings model
export BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
```

## 4. Prove it's live (evidence)
```bash
cd velocity-hospitality-os
python scripts/bedrock_smoketest.py                 # Nova answers through Velocity
VHOS_LLM_BACKEND=bedrock python demo/run_demo.py    # the hero loop on Nova
python eval/run_eval.py                              # accuracy on the managed model
```
Green = a real managed cloud model answered through Velocity. Screenshot for the logbook.

## Troubleshooting
- **AccessDeniedException "not available for this account"** → that foundation model is
  entitlement-gated on this account. Use an available one, e.g. `amazon.nova-lite-v1:0`.
- **ValidationException** → the model id isn't Converse-capable or is wrong; copy it from the console.
- **NoCredentials / ExpiredToken** → export/refresh the access key.

## Positioning
Official production = **self-hosted open weights on H200** (`docs/openweights-runbook.md`).
Bedrock/Nova is a **validated managed provider** proving the abstraction with a real cloud
model today. The choice is one env var — that's the point.
