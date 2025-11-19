#!/bin/bash
# Create IAM role for Lambda function with required permissions

set -e

ROLE_NAME="saferide-lambda-role"
POLICY_NAME="saferide-lambda-policy"
REGION="us-west-2"

echo "🔐 Creating IAM role for Lambda..."

# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_DATA="saferide-data-505877"
BUCKET_TILES="saferide-tiles-505877"

# Create trust policy for Lambda
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    --description "IAM role for Safer Ride Lambda function" \
    2>/dev/null || echo "Role may already exist"

echo "✅ Role created: $ROLE_NAME"

# Create policy for S3 access
cat > /tmp/lambda-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_DATA}/*",
        "arn:aws:s3:::${BUCKET_TILES}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:saferide/*"
    }
  ]
}
EOF

# Create the policy
POLICY_ARN=$(aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file:///tmp/lambda-policy.json \
    --query "Policy.Arn" \
    --output text 2>/dev/null || \
    aws iam get-policy --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" --query "Policy.Arn" --output text)

echo "✅ Policy created: $POLICY_ARN"

# Attach policies to role
echo "Attaching policies to role..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    2>/dev/null || echo "Basic execution role may already be attached"

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN \
    2>/dev/null || echo "Custom policy may already be attached"

echo ""
echo "✅ IAM role setup complete!"
echo "Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "📋 Next: Use this role ARN when creating the Lambda function"

