#!/bin/bash
# Script to create API Gateway REST API and connect to Lambda

set -e

API_NAME="saferide-api"
LAMBDA_FUNCTION_NAME="saferide-api"
REGION="us-west-2"
STAGE="prod"

echo "🚀 Setting up API Gateway for Safer Ride..."
echo ""

# Get Lambda function ARN
LAMBDA_ARN=$(aws lambda get-function \
    --function-name $LAMBDA_FUNCTION_NAME \
    --region $REGION \
    --query "Configuration.FunctionArn" \
    --output text)

echo "Lambda ARN: $LAMBDA_ARN"
echo ""

# Create REST API
echo "📦 Creating REST API..."
API_ID=$(aws apigateway create-rest-api \
    --name $API_NAME \
    --description "Safer Ride routing API" \
    --endpoint-configuration types=REGIONAL \
    --region $REGION \
    --query "id" \
    --output text 2>/dev/null || \
    aws apigateway get-rest-apis \
        --region $REGION \
        --query "items[?name=='$API_NAME'].id" \
        --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
    echo "❌ Failed to create or find API"
    exit 1
fi

echo "✅ API created/found: $API_ID"
echo ""

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?path=='/'].id" \
    --output text)

echo "Root Resource ID: $ROOT_RESOURCE_ID"
echo ""

# Create /routes resource
echo "📁 Creating /routes resource..."
ROUTES_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part "routes" \
    --region $REGION \
    --query "id" \
    --output text 2>/dev/null || \
    aws apigateway get-resources \
        --rest-api-id $API_ID \
        --region $REGION \
        --query "items[?path=='/routes'].id" \
        --output text)

echo "Routes Resource ID: $ROUTES_RESOURCE_ID"
echo ""

# Create /routes/rank resource
echo "📁 Creating /routes/rank resource..."
RANK_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROUTES_RESOURCE_ID \
    --path-part "rank" \
    --region $REGION \
    --query "id" \
    --output text 2>/dev/null || \
    aws apigateway get-resources \
        --rest-api-id $API_ID \
        --region $REGION \
        --query "items[?path=='/routes/rank'].id" \
        --output text)

echo "Rank Resource ID: $RANK_RESOURCE_ID"
echo ""

# Create POST method for /routes/rank
echo "🔧 Creating POST method for /routes/rank..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE \
    --region $REGION \
    --no-api-key-required 2>/dev/null || echo "Method may already exist"

# Set up Lambda integration
echo "🔗 Setting up Lambda integration..."
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
    --region $REGION 2>/dev/null || echo "Integration may already exist"

# Grant API Gateway permission to invoke Lambda
echo "🔐 Granting API Gateway permission to invoke Lambda..."
aws lambda add-permission \
    --function-name $LAMBDA_FUNCTION_NAME \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$(aws sts get-caller-identity --query Account --output text):$API_ID/*/*" \
    --region $REGION 2>/dev/null || echo "Permission may already exist"

# Create /health resource
echo "📁 Creating /health resource..."
HEALTH_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part "health" \
    --region $REGION \
    --query "id" \
    --output text 2>/dev/null || \
    aws apigateway get-resources \
        --rest-api-id $API_ID \
        --region $REGION \
        --query "items[?path=='/health'].id" \
        --output text)

# Create GET method for /health
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE \
    --region $REGION \
    --no-api-key-required 2>/dev/null || echo "Health method may already exist"

# Set up Lambda integration for /health
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
    --region $REGION 2>/dev/null || echo "Health integration may already exist"

# Enable CORS for /routes/rank
echo "🌐 Enabling CORS..."
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --region $REGION 2>/dev/null || echo "CORS method may already exist"

# Deploy API
echo "🚀 Deploying API to '$STAGE' stage..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $STAGE \
    --region $REGION \
    --description "Initial deployment" 2>/dev/null || \
    aws apigateway create-deployment \
        --rest-api-id $API_ID \
        --stage-name $STAGE \
        --region $REGION \
        --description "Update deployment" 2>/dev/null || echo "Deployment may already exist"

# Get API URL
API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE}"
echo ""
echo "✅ API Gateway setup complete!"
echo ""
echo "📋 API Information:"
echo "   API ID: $API_ID"
echo "   Stage: $STAGE"
echo "   API URL: $API_URL"
echo ""
echo "🔗 Endpoints:"
echo "   GET  $API_URL/health"
echo "   POST $API_URL/routes/rank"
echo ""
echo "📝 Next: Update frontend API_BASE to: $API_URL"

