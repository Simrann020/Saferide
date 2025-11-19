#!/bin/bash
# Rebuild Lambda package for Linux (x86_64) using Docker

set -e

echo "🐳 Building Lambda package for Linux using Docker..."
echo ""

cd saferide-api

# Clean previous builds
rm -f lambda-deployment.zip
rm -rf package-linux/

# Use Docker to build for Linux
echo "Using Docker to install dependencies for Linux..."
docker run --rm --entrypoint="" \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.11 \
    /bin/bash -c "
        pip install --platform manylinux2014_x86_64 --only-binary=:all: --no-cache-dir -r requirements.txt -t package-linux/ && \
        pip install --platform manylinux2014_x86_64 --no-cache-dir -r requirements.txt -t package-linux/ --upgrade && \
        cp -r app package-linux/ && \
        cp lambda_handler.py package-linux/ 2>/dev/null || true
    "

# Create zip
echo "Creating deployment package..."
cd package-linux
zip -r ../lambda-deployment-linux.zip . -x "*.pyc" "__pycache__/*" "*.git*" "*.DS_Store"
cd ..

echo "✅ Lambda package built: lambda-deployment-linux.zip"
echo "📦 Package size: $(du -h lambda-deployment-linux.zip | cut -f1)"
echo ""
echo "🚀 Deploying to Lambda..."
aws lambda update-function-code \
    --function-name saferide-api \
    --zip-file fileb://lambda-deployment-linux.zip \
    --region us-west-2 \
    --query "[FunctionName,CodeSize,LastUpdateStatus]" \
    --output table

echo ""
echo "✅ Lambda function updated!"
echo "⏳ Wait a few seconds for the update to complete, then test the API."

cd ..

