# SafeRide - AWS Deployment Run Guide

This guide explains how to run and access your SafeRide application that's deployed on AWS.

## 🎯 Quick Start

Your application is already deployed on AWS! Here's how to access it:

### 1. Check Service Status

First, check if your services are running:

```bash
cd "/Users/simran/Documents/CUB Assignments/Project DCSC/Saferide Final"
./check_services_status.sh
```

This will show you:
- ✅ RDS Database status (stopped/starting/available)
- ✅ Lambda Function status
- ✅ API Gateway status
- ✅ S3 Buckets status

### 2. Start Services (If Stopped)

If the RDS database is stopped (to save costs), start it:

```bash
./start_services.sh
```

This will:
- Start the RDS database (takes ~5-10 minutes)
- Wait for it to become "available"
- Your API will automatically work once RDS is available

**Note**: RDS takes 5-10 minutes to start. You can check status with:
```bash
./check_services_status.sh
```

### 3. Access Your Application

Once services are running, access your application:

#### 🌐 Frontend (Web UI)
- **URL**: http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com
- Open this URL in your browser to use the SafeRide application

#### 🔌 API Endpoints
- **Health Check**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health
- **API Documentation**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/docs
- **Route Ranking**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/routes/rank

---

## 📊 Service Details

### What's Deployed

| Service | Name | Status | URL/Endpoint |
|---------|------|--------|--------------|
| **RDS Database** | `saferide-db` | May be stopped | `saferide-db.cdiqwk6682ia.us-west-2.rds.amazonaws.com:5432` |
| **Lambda Function** | `saferide-api` | ✅ Always active | Invoked via API Gateway |
| **API Gateway** | `39lch19vrb` | ✅ Always active | `https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod` |
| **S3 Frontend** | `saferide-ui-505877` | ✅ Always active | `http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com` |

### Service States

**RDS Database:**
- **Stopped** 🛑: No charges, cannot access (saves money)
- **Starting** ⏳: Transitioning (5-10 minutes)
- **Available** ✅: Running, can access, incurring charges (~$15/month)

**Lambda & API Gateway:**
- Always active but only charge when used
- Very low cost (free tier covers most usage)

---

## 🚀 Step-by-Step: Running on AWS

### Step 1: Check Current Status

```bash
./check_services_status.sh
```

**Expected Output:**
```
📊 Checking AWS services status...

🗄️  RDS Database:
   Status: 🛑 Stopped (not incurring charges)

⚡ Lambda Function:
   Status: ✅ Active (only charges when invoked)

🌐 API Gateway:
   Status: ✅ Active (only charges per request)
   URL: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod

📦 S3 Buckets:
   ✅ saferide-ui-505877
   ✅ saferide-crash-data-505877
   ...
```

### Step 2: Start RDS (If Stopped)

If RDS is stopped, start it:

```bash
./start_services.sh
```

**What happens:**
1. RDS instance starts (takes 5-10 minutes)
2. Status changes: `stopped` → `starting` → `available`
3. Once `available`, the database is ready to use
4. Lambda can now connect to the database

**Monitor progress:**
```bash
# Check status repeatedly
watch -n 10 './check_services_status.sh'

# Or check manually
aws rds describe-db-instances \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text
```

### Step 3: Verify API is Working

Once RDS is available, test the API:

```bash
# Test health endpoint
curl https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health

# Expected response:
# {"status":"ok","database":"connected"}
```

### Step 4: Access the Frontend

Open your browser and go to:
```
http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com
```

The frontend is already configured to use the AWS API Gateway URL, so it will automatically connect to your deployed API.

---

## 🛑 Stopping Services (To Save Costs)

When you're done using the application, stop the RDS database to save costs:

```bash
./stop_services.sh
```

**What this does:**
- Stops the RDS database (saves ~$15/month)
- **Does NOT delete anything** - all data is preserved
- Lambda and API Gateway remain active (no cost when idle)
- S3 buckets remain active (minimal storage cost ~$0.50/month)

**Note**: AWS automatically restarts stopped RDS instances after 7 days. If you want to keep it stopped longer, run `./stop_services.sh` again.

---

## 🔧 Manual Commands

### Check RDS Status
```bash
aws rds describe-db-instances \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text
```

### Start RDS Manually
```bash
aws rds start-db-instance \
    --db-instance-identifier saferide-db \
    --region us-west-2
```

### Stop RDS Manually
```bash
aws rds stop-db-instance \
    --db-instance-identifier saferide-db \
    --region us-west-2
```

### Test API Endpoints
```bash
# Health check
curl https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health

# Route ranking (example)
curl -X POST https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/routes/rank \
  -H "Content-Type: application/json" \
  -d '{
    "start": [-105.0, 39.7],
    "end": [-104.99, 39.75],
    "mode": "driving",
    "buffer_m": 60,
    "max_alternatives": 3
  }'
```

---

## 💰 Cost Information

### When Services Are Stopped
- **RDS**: $0.00/month (stopped)
- **Lambda**: $0.00/month (not invoked)
- **API Gateway**: $0.00/month (no requests)
- **S3**: ~$0.50/month (storage only)
- **Total**: ~$0.50/month

### When Services Are Running
- **RDS**: ~$15/month (db.t3.micro, after free tier)
- **Lambda**: ~$0.20/month (assuming 10K requests)
- **API Gateway**: ~$3.50/month (assuming 1M requests)
- **S3**: ~$0.50/month (storage)
- **Total**: ~$19/month

**Free Tier**: 
- RDS: 750 hours/month for 12 months (free)
- Lambda: 1M requests/month (free)
- API Gateway: 1M requests/month (free)

---

## 🐛 Troubleshooting

### API Returns 502 or 500 Error

**Possible causes:**
1. RDS database is stopped
   - **Solution**: Start RDS with `./start_services.sh`
   - Wait 5-10 minutes for it to become available

2. Database connection issue
   - **Check**: Lambda environment variables are set correctly
   - **Check**: Security groups allow Lambda to access RDS

3. Lambda timeout
   - **Check**: CloudWatch logs for errors
   - **Solution**: Increase Lambda timeout if needed

### Frontend Can't Connect to API

**Check:**
1. API Gateway is active (always should be)
2. CORS is enabled (should already be configured)
3. Browser console for errors (F12 → Console)

**Test API directly:**
```bash
curl https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health
```

### RDS Won't Start

**Possible causes:**
1. Already starting (wait 5-10 minutes)
2. AWS account limits
3. Billing issues

**Check:**
```bash
aws rds describe-db-instances \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --query 'DBInstances[0].[DBInstanceStatus,DBInstanceStatusReason]' \
    --output table
```

---

## 📝 Quick Reference

### Start Everything
```bash
./start_services.sh
```

### Stop Everything (Save Costs)
```bash
./stop_services.sh
```

### Check Status
```bash
./check_services_status.sh
```

### Access URLs
- **Frontend**: http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com
- **API Health**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health
- **API Docs**: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/docs

---

## ✅ What's Already Configured

Your AWS deployment includes:

- ✅ **RDS PostgreSQL 16** with PostGIS extension
- ✅ **Lambda Function** with FastAPI backend
- ✅ **API Gateway** with CORS enabled
- ✅ **S3 Buckets** for frontend and data
- ✅ **IAM Roles** with proper permissions
- ✅ **Security Groups** configured
- ✅ **Frontend** configured to use API Gateway URL

**Everything is ready to use!** Just start the RDS database if it's stopped.

---

## 🎯 Typical Workflow

1. **Start services**: `./start_services.sh`
2. **Wait 5-10 minutes** for RDS to become available
3. **Check status**: `./check_services_status.sh`
4. **Access frontend**: Open the S3 website URL
5. **Use the application**: Plan routes, see rankings
6. **Stop services** (when done): `./stop_services.sh`

---

## 📞 Need Help?

- **Check logs**: AWS CloudWatch → Log groups → `/aws/lambda/saferide-api`
- **Check RDS**: AWS Console → RDS → `saferide-db`
- **Check API Gateway**: AWS Console → API Gateway → `39lch19vrb`
- **Review documentation**: See `PROJECT_DOCUMENTATION.md` for architecture details

---

**Last Updated**: Based on deployment from November 16, 2025  
**Region**: us-west-2 (Oregon)  
**Status**: ✅ Fully deployed and ready to use

