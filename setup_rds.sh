#!/bin/bash
# Script to create RDS PostgreSQL instance with PostGIS for Safer Ride

set -e

DB_INSTANCE_ID="saferide-db"
DB_NAME="safer_ride"
DB_USER="postgres"
DB_PASSWORD="${DB_PASSWORD:-}"  # Set via environment variable
REGION="us-west-2"
DB_INSTANCE_CLASS="db.t3.micro"  # Free tier eligible
STORAGE_SIZE=20
VPC_SECURITY_GROUP_ID="${VPC_SECURITY_GROUP_ID:-}"  # Optional: specify existing SG

echo "🚀 Creating RDS PostgreSQL instance for Safer Ride..."
echo ""

# Check if password is set
if [ -z "$DB_PASSWORD" ]; then
    echo "⚠️  DB_PASSWORD not set. Generating a secure password..."
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "Generated password: $DB_PASSWORD"
    echo "⚠️  SAVE THIS PASSWORD - you'll need it later!"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."
fi

# Get default VPC and subnets if not specified
if [ -z "$VPC_SECURITY_GROUP_ID" ]; then
    echo "📋 Getting default VPC information..."
    DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
    echo "Default VPC: $DEFAULT_VPC"
    
    # Get default subnets
    SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query "Subnets[*].SubnetId" --output text --region $REGION)
    SUBNET_GROUP_NAME="${DB_INSTANCE_ID}-subnet-group"
    
    echo "Creating DB subnet group..."
    aws rds create-db-subnet-group \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --db-subnet-group-description "Subnet group for Safer Ride RDS" \
        --subnet-ids $SUBNET_IDS \
        --region $REGION 2>/dev/null || echo "Subnet group may already exist"
else
    SUBNET_GROUP_NAME="${DB_INSTANCE_ID}-subnet-group"
fi

# Create security group if not provided
if [ -z "$VPC_SECURITY_GROUP_ID" ]; then
    echo "📋 Creating security group..."
    SG_NAME="${DB_INSTANCE_ID}-sg"
    VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)
    
    # Check if security group exists
    EXISTING_SG=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
        --query "SecurityGroups[0].GroupId" --output text --region $REGION 2>/dev/null || echo "None")
    
    if [ "$EXISTING_SG" != "None" ] && [ -n "$EXISTING_SG" ]; then
        VPC_SECURITY_GROUP_ID=$EXISTING_SG
        echo "Using existing security group: $VPC_SECURITY_GROUP_ID"
    else
        VPC_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
            --group-name $SG_NAME \
            --description "Security group for Safer Ride RDS" \
            --vpc-id $VPC_ID \
            --region $REGION \
            --query "GroupId" --output text)
        echo "Created security group: $VPC_SECURITY_GROUP_ID"
        
        # Add rule to allow PostgreSQL from anywhere (for Lambda access)
        echo "Adding inbound rule for PostgreSQL (port 5432)..."
        aws ec2 authorize-security-group-ingress \
            --group-id $VPC_SECURITY_GROUP_ID \
            --protocol tcp \
            --port 5432 \
            --cidr 0.0.0.0/0 \
            --region $REGION 2>/dev/null || echo "Rule may already exist"
    fi
fi

echo ""
echo "📦 Creating RDS instance (this may take 10-15 minutes)..."
echo "Instance ID: $DB_INSTANCE_ID"
echo "Class: $DB_INSTANCE_CLASS"
echo "Storage: ${STORAGE_SIZE}GB"
echo ""

# Check if instance already exists
EXISTING_INSTANCE=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $REGION \
    --query "DBInstances[0].DBInstanceStatus" \
    --output text 2>/dev/null || echo "None")

if [ "$EXISTING_INSTANCE" != "None" ] && [ -n "$EXISTING_INSTANCE" ]; then
    echo "⚠️  RDS instance '$DB_INSTANCE_ID' already exists with status: $EXISTING_INSTANCE"
    echo "Skipping creation. Use 'aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID' to check status."
else
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_ID \
        --db-instance-class $DB_INSTANCE_CLASS \
        --engine postgres \
        --engine-version 16.1 \
        --master-username $DB_USER \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage $STORAGE_SIZE \
        --storage-type gp3 \
        --db-name $DB_NAME \
        --vpc-security-group-ids $VPC_SECURITY_GROUP_ID \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --publicly-accessible \
        --backup-retention-period 7 \
        --region $REGION \
        --no-multi-az \
        --no-storage-encrypted \
        --no-auto-minor-version-upgrade

    echo ""
    echo "✅ RDS instance creation initiated!"
    echo "⏳ This will take 10-15 minutes. You can check status with:"
    echo "   aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --query 'DBInstances[0].DBInstanceStatus'"
    echo ""
    echo "📝 IMPORTANT: Save these credentials!"
    echo "   Database: $DB_NAME"
    echo "   Username: $DB_USER"
    echo "   Password: $DB_PASSWORD"
    echo "   Security Group: $VPC_SECURITY_GROUP_ID"
    echo ""
    echo "🔐 Store password in AWS Secrets Manager:"
    echo "   aws secretsmanager create-secret --name saferide/rds/credentials --secret-string '{\"host\":\"<endpoint>\",\"port\":\"5432\",\"database\":\"$DB_NAME\",\"username\":\"$DB_USER\",\"password\":\"$DB_PASSWORD\"}'"
fi

echo ""
echo "📋 Next steps:"
echo "   1. Wait for RDS instance to be 'available'"
echo "   2. Get endpoint: aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --query 'DBInstances[0].Endpoint.Address'"
echo "   3. Enable PostGIS: Run setup_postgis.sh"
echo "   4. Load data: Run ETL scripts with updated PGHOST"
