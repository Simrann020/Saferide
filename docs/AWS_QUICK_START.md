# AWS Deployment Quick Start Checklist

## Prerequisites (One-time setup)
- [ ] AWS account created
- [ ] AWS CLI installed: `brew install awscli`
- [ ] AWS CLI configured: `aws configure`
- [ ] AWS SAM CLI installed: `brew install aws-sam-cli` (optional)

---

## Deployment Order (Follow sequentially)

### 1. Database (RDS) - ~15 minutes
```
1. AWS Console → RDS → Create database
   - PostgreSQL 16, Free tier, Public access: Yes
   - Store password in Secrets Manager
2. Security Group: Allow port 5432 from Lambda/your IP
3. Connect and enable PostGIS:
   psql -h <endpoint> -U postgres
   CREATE DATABASE safer_ride;
   \c safer_ride
   CREATE EXTENSION postgis;
4. Run init scripts from safer-ride/db/init/
5. Load data: python etl/load_*.py (update PGHOST)
```

### 2. S3 Buckets - ~5 minutes
```
1. Create 3 buckets:
   - saferide-ui-<unique>
   - saferide-data-<unique>
   - saferide-tiles-<unique>
2. Enable static website hosting on UI bucket
3. Upload files:
   aws s3 sync safe-ride-ui/ s3://saferide-ui-<name>/
   aws s3 cp data/*.csv s3://saferide-data-<name>/raw/
```

### 3. Lambda Function - ~20 minutes
```
1. Adapt FastAPI for Lambda (add Mangum)
2. Create IAM role with:
   - Lambda execution role
   - S3 read access
   - Secrets Manager read access
   - RDS access (if in VPC)
3. Package and deploy:
   cd saferide-api
   pip install -r requirements.txt -t .
   zip -r lambda.zip . -x "*.pyc" "__pycache__/*"
   aws lambda create-function --function-name saferide-api ...
4. Set environment variables (RDS endpoint, etc.)
```

### 4. API Gateway - ~10 minutes
```
1. Create REST API
2. Create resources: /health, /routes/rank
3. Integrate with Lambda
4. Enable CORS
5. Deploy to 'prod' stage
6. Note the Invoke URL
```

### 5. Update Frontend - ~5 minutes
```
1. Update API_BASE in index.html/app.js to API Gateway URL
2. Re-upload to S3:
   aws s3 sync safe-ride-ui/ s3://saferide-ui-<name>/
```

### 6. CloudFront (Optional) - ~10 minutes
```
1. Create distribution for S3 bucket
2. Wait for deployment (~15 minutes)
3. Update DNS (if using custom domain)
```

---

## Testing
```bash
# Test API
curl https://<api-gateway-url>/health

# Test route ranking
curl -X POST https://<api-gateway-url>/routes/rank \
  -H "Content-Type: application/json" \
  -d '{"start": [-105.0, 39.7], "end": [-104.99, 39.75], "mode": "driving"}'
```

---

## Key Files to Modify

1. **saferide-api/app/main.py** - Add Mangum handler
2. **safe-ride-ui/index.html** or **app.js** - Update API_BASE URL
3. **etl/*.py** - Update PGHOST to RDS endpoint
4. **Environment variables** - Store in Secrets Manager

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Lambda timeout | Increase timeout to 30s, optimize queries |
| RDS connection refused | Check security group, VPC settings |
| CORS errors | Enable CORS in API Gateway |
| 502 Bad Gateway | Check Lambda logs, verify handler name |
| Slow responses | Enable CloudFront, check RDS performance |

---

## Cost Estimate
- **Free tier eligible**: ~$0-5/month (first year)
- **After free tier**: ~$15-30/month (low traffic)

---

See `AWS_DEPLOYMENT_ROADMAP.md` for detailed steps.

