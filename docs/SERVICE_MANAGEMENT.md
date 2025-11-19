# Service Management Guide

## 🛑 Services Stopped to Save Credits

Your AWS services have been stopped (not deleted) to save free tier credits.

---

## 📊 Current Status

### ✅ Stopped (No Charges)
- **RDS Database**: `saferide-db` - **STOPPING** → Will be **STOPPED** in ~5 minutes
  - Status: Stopping (will complete in ~5 minutes)
  - **No charges** when stopped
  - Can be stopped for up to 7 days (AWS auto-restarts after 7 days)

### ✅ Active (No Charges When Idle)
- **Lambda Function**: `saferide-api`
  - Status: Active
  - **No charges** when not invoked
  - Only charges per invocation (very low cost)

- **API Gateway**: `39lch19vrb`
  - Status: Active
  - **No charges** when no requests
  - Only charges per request (very low cost)

### ✅ Active (Minimal Storage Cost)
- **S3 Buckets**: 5 buckets
  - Status: Active
  - **Minimal cost**: ~$0.50/month for storage
  - No action needed (storage is cheap)

---

## 🚀 How to Restart Services

### Quick Start
```bash
./start_services.sh
```

This will:
1. Start the RDS instance (takes ~5-10 minutes)
2. Wait for it to become "available"
3. Your API will automatically work once RDS is available

### Manual Start
```bash
# Start RDS
aws rds start-db-instance \
    --db-instance-identifier saferide-db \
    --region us-west-2

# Check status
aws rds describe-db-instances \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --query 'DBInstances[0].DBInstanceStatus'
```

---

## 📊 Check Service Status

```bash
./check_services_status.sh
```

This shows:
- RDS status (stopped/starting/available)
- Lambda status
- API Gateway status
- S3 buckets status

---

## 💰 Cost Breakdown

### When Stopped (Current State)
- **RDS**: $0.00/month (stopped)
- **Lambda**: $0.00/month (not invoked)
- **API Gateway**: $0.00/month (no requests)
- **S3**: ~$0.50/month (storage only)
- **Total**: ~$0.50/month

### When Running
- **RDS**: ~$15/month (db.t3.micro, after free tier)
- **Lambda**: ~$0.20/month (assuming 10K requests)
- **API Gateway**: ~$3.50/month (assuming 1M requests)
- **S3**: ~$0.50/month (storage)
- **Total**: ~$19/month

---

## ⚠️ Important Notes

### RDS Auto-Restart
- AWS automatically restarts stopped RDS instances after **7 days**
- If you want to keep it stopped longer, you'll need to stop it again

### Data Safety
- ✅ **All data is preserved** when stopped
- ✅ **No data loss** - stopping is safe
- ✅ **Can restart anytime** - nothing is deleted

### Free Tier
- RDS Free Tier: 750 hours/month for 12 months
- When stopped, you're not using free tier hours
- Lambda and API Gateway have generous free tiers

---

## 🔄 Service Lifecycle

```
Stopped → Starting → Available → Stopping → Stopped
   ↑                                        ↓
   └────────────────────────────────────────┘
```

### States:
- **Stopped**: No charges, cannot access
- **Starting**: Transitioning (5-10 minutes)
- **Available**: Running, can access, incurring charges
- **Stopping**: Transitioning (5 minutes)

---

## 📝 Quick Reference

### Stop Services
```bash
./stop_services.sh
```

### Start Services
```bash
./start_services.sh
```

### Check Status
```bash
./check_services_status.sh
```

### Manual RDS Commands
```bash
# Stop
aws rds stop-db-instance --db-instance-identifier saferide-db --region us-west-2

# Start
aws rds start-db-instance --db-instance-identifier saferide-db --region us-west-2

# Status
aws rds describe-db-instances --db-instance-identifier saferide-db --region us-west-2 --query 'DBInstances[0].DBInstanceStatus'
```

---

## ✅ What's Preserved

When services are stopped:
- ✅ Database data (71,000+ crashes)
- ✅ Database schema and PostGIS extensions
- ✅ Lambda function code
- ✅ API Gateway configuration
- ✅ S3 files and buckets
- ✅ IAM roles and security groups
- ✅ All configurations

**Nothing is deleted!** Everything will work exactly as before when you restart.

---

## 🎯 When to Restart

Restart services when you need to:
- Test the application
- Demo the project
- Continue development
- Use the API

**Current Status**: Services stopped, ready to restart anytime! 🛑

---

**Last Stopped**: November 16, 2025  
**Auto-Restart Date**: November 23, 2025 (7 days from stop)

