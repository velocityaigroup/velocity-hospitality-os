# Infrastructure

AWS deployment via SAM. `template.yaml` defines the serverless backbone
(Lambda + API Gateway + DynamoDB + a Step Functions execution loop).

```bash
sam build && sam deploy --guided
```
