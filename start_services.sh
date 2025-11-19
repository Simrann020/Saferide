#!/bin/bash
# Start AWS services after stopping them

set -e

echo "🚀 Starting AWS services..."
echo ""

# Start RDS instance
echo "📊 Starting RDS instance..."
aws rds start-db-instance \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --output json

echo ""
echo "⏳ RDS instance is starting (takes ~5-10 minutes)..."
echo "   Status will change: 'starting' → 'available'"
echo ""
echo "💡 Check status with:"
echo "   aws rds describe-db-instances --db-instance-identifier saferide-db --query 'DBInstances[0].DBInstanceStatus'"
echo ""
echo "⏱️  Wait for status to be 'available' before using the API."
echo ""
echo "✅ Once RDS is available, your services are ready:"
echo "   - Frontend: http://saferide-ui-505877.s3-website-us-west-2.amazonaws.com"
echo "   - API: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod/health"
echo ""

