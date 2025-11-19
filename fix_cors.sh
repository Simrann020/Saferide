#!/bin/bash
# Fix CORS for API Gateway

set -e

API_ID="39lch19vrb"
REGION="us-west-2"

echo "🌐 Fixing CORS for API Gateway..."

# Get resource IDs
RANK_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?path=='/routes/rank'].id" \
    --output text)

HEALTH_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query "items[?path=='/health'].id" \
    --output text)

echo "Rank Resource ID: $RANK_RESOURCE_ID"
echo "Health Resource ID: $HEALTH_RESOURCE_ID"

# Create OPTIONS method for /routes/rank
echo "Creating OPTIONS method for /routes/rank..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION \
    --no-api-key-required 2>/dev/null || echo "OPTIONS method may already exist"

# Set up MOCK integration for OPTIONS
echo "Setting up MOCK integration for OPTIONS..."
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --integration-http-method OPTIONS \
    --request-templates '{"application/json":"{\"statusCode\":200}"}' \
    --region $REGION 2>/dev/null || echo "Integration may already exist"

# Set method response for OPTIONS
echo "Setting method response for OPTIONS..."
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":true,"method.response.header.Access-Control-Allow-Methods":true,"method.response.header.Access-Control-Allow-Origin":true}' \
    --region $REGION 2>/dev/null || echo "Method response may already exist"

# Set integration response for OPTIONS
echo "Setting integration response for OPTIONS..."
aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,POST,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
    --region $REGION 2>/dev/null || echo "Integration response may already exist"

# Add CORS headers to POST method response
echo "Adding CORS headers to POST method response..."
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method POST \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":true}' \
    --region $REGION 2>/dev/null || echo "POST method response may already exist"

# Add CORS headers to POST integration response
echo "Adding CORS headers to POST integration response..."
aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $RANK_RESOURCE_ID \
    --http-method POST \
    --status-code 200 \
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
    --region $REGION 2>/dev/null || echo "POST integration response may already exist"

# Deploy API
echo "Deploying API..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION \
    --description "CORS fix deployment" 2>/dev/null || echo "Deployment may already exist"

echo ""
echo "✅ CORS configured!"
echo "🔗 Test the API: https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/routes/rank"

