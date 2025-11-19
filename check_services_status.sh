#!/bin/bash
# Check status of AWS services

echo "📊 Checking AWS services status..."
echo ""

# Check RDS status
echo "🗄️  RDS Database:"
RDS_STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier saferide-db \
    --region us-west-2 \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text 2>/dev/null || echo "ERROR")

if [ "$RDS_STATUS" = "ERROR" ]; then
    echo "   Status: ❌ Could not retrieve status"
else
    case "$RDS_STATUS" in
        "available")
            echo "   Status: ✅ Running"
            ENDPOINT=$(aws rds describe-db-instances \
                --db-instance-identifier saferide-db \
                --region us-west-2 \
                --query 'DBInstances[0].Endpoint.Address' \
                --output text)
            echo "   Endpoint: $ENDPOINT"
            ;;
        "stopped")
            echo "   Status: 🛑 Stopped (not incurring charges)"
            ;;
        "stopping")
            echo "   Status: ⏳ Stopping..."
            ;;
        "starting")
            echo "   Status: ⏳ Starting..."
            ;;
        *)
            echo "   Status: ⚠️  $RDS_STATUS"
            ;;
    esac
fi

echo ""

# Check Lambda status
echo "⚡ Lambda Function:"
LAMBDA_STATUS=$(aws lambda get-function \
    --function-name saferide-api \
    --region us-west-2 \
    --query 'Configuration.State' \
    --output text 2>/dev/null || echo "ERROR")

if [ "$LAMBDA_STATUS" = "ERROR" ]; then
    echo "   Status: ❌ Could not retrieve status"
else
    echo "   Status: ✅ Active (only charges when invoked)"
fi

echo ""

# Check API Gateway status
echo "🌐 API Gateway:"
API_STATUS=$(aws apigateway get-rest-api \
    --rest-api-id 39lch19vrb \
    --region us-west-2 \
    --query 'name' \
    --output text 2>/dev/null || echo "ERROR")

if [ "$API_STATUS" = "ERROR" ]; then
    echo "   Status: ❌ Could not retrieve status"
else
    echo "   Status: ✅ Active (only charges per request)"
    echo "   URL: https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod"
fi

echo ""

# Check S3 buckets
echo "📦 S3 Buckets:"
BUCKETS=("saferide-ui-505877" "saferide-crash-data-505877" "saferide-311-data-505877" "saferide-bikeway-data-505877" "saferide-tiles-505877")
for bucket in "${BUCKETS[@]}"; do
    EXISTS=$(aws s3 ls "s3://$bucket" --region us-west-2 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND")
    if [ "$EXISTS" = "EXISTS" ]; then
        echo "   ✅ $bucket"
    else
        echo "   ❌ $bucket (not found)"
    fi
done

echo ""
echo "💡 Cost Notes:"
echo "   - RDS: Charges only when 'available' (stopped = no charge)"
echo "   - Lambda: Charges only when invoked"
echo "   - API Gateway: Charges only per request"
echo "   - S3: Charges for storage (~$0.50/month for our data)"

