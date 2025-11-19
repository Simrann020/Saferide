#!/bin/bash
# Stop AWS services to save credits (without deleting)

set -e

echo "🛑 Stopping AWS services to save credits..."
echo ""

# Stop RDS instance (main cost)
echo "📊 Stopping RDS instance..."
aws rds stop-db-instance \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --output json

echo ""
echo "⏳ RDS instance is stopping (takes ~5 minutes)..."
echo "   You can check status with: aws rds describe-db-instances --db-instance-identifier saferide-db --query 'DBInstances[0].DBInstanceStatus'"
echo ""

# Note: Lambda and API Gateway don't need to be stopped
# - Lambda: Only charges when invoked (no cost when idle)
# - API Gateway: Only charges per request (no cost when idle)
# - S3: Only charges for storage (~$0.50/month for our data)

echo "✅ Services stopped:"
echo "   - RDS: Stopping (will be 'stopped' in ~5 minutes)"
echo ""
echo "ℹ️  Note:"
echo "   - Lambda: No action needed (only charges when used)"
echo "   - API Gateway: No action needed (only charges per request)"
echo "   - S3: No action needed (minimal storage cost)"
echo ""
echo "💡 To restart later, run: ./start_services.sh"
echo ""
echo "⚠️  Important: RDS can be stopped for up to 7 days."
echo "   After 7 days, AWS will automatically start it again."

