#!/bin/bash
# Helper script to package and deploy Lambda function

set -e

LAMBDA_FUNCTION_NAME="saferide-api"
REGION="us-west-2"
ZIP_FILE="lambda-deployment.zip"

echo "📦 Packaging Lambda function..."

cd saferide-api

# Clean previous builds
rm -f ${ZIP_FILE}
rm -rf package/

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t package/

# Copy application code
echo "Copying application code..."
cp -r app package/
cp lambda_handler.py package/ 2>/dev/null || echo "Note: lambda_handler.py not found, create it first"

# Create zip
cd package
zip -r ../${ZIP_FILE} . -x "*.pyc" "__pycache__/*" "*.git*" "*.DS_Store"
cd ..

echo "✅ Package created: ${ZIP_FILE}"

# Deploy to Lambda (uncomment when ready)
# echo "🚀 Deploying to Lambda..."
# aws lambda update-function-code \
#   --function-name ${LAMBDA_FUNCTION_NAME} \
#   --zip-file fileb://${ZIP_FILE} \
#   --region ${REGION}

echo "📝 To deploy, uncomment the deployment commands above or run:"
echo "   aws lambda update-function-code --function-name ${LAMBDA_FUNCTION_NAME} --zip-file fileb://${ZIP_FILE} --region ${REGION}"

cd ..

