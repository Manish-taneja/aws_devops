#!/usr/bin/env python3
"""
Create S3 Backend for Terraform State
This script creates the S3 bucket and DynamoDB table for Terraform state management
"""

import boto3
import json
from botocore.exceptions import ClientError

class TerraformBackendSetup:
    def __init__(self):
        self.account_id = "619564767540"
        self.region = "us-east-1"
        self.bucket_name = f"aws-devops-terraform-state-{self.account_id}"
        self.table_name = "aws-devops-terraform-locks"
        
    def create_s3_bucket(self):
        """Create S3 bucket for Terraform state"""
        s3 = boto3.client('s3', region_name=self.region)
        
        try:
            # Check if bucket exists
            s3.head_bucket(Bucket=self.bucket_name)
            print(f"✅ S3 bucket '{self.bucket_name}' already exists")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        s3.create_bucket(Bucket=self.bucket_name)
                    else:
                        s3.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    print(f"✅ Created S3 bucket: {self.bucket_name}")
                    
                    # Enable versioning
                    s3.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    
                    # Enable server-side encryption
                    s3.put_bucket_encryption(
                        Bucket=self.bucket_name,
                        ServerSideEncryptionConfiguration={
                            'Rules': [{
                                'ApplyServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': 'AES256'
                                }
                            }]
                        }
                    )
                    
                    # Block public access
                    s3.put_public_access_block(
                        Bucket=self.bucket_name,
                        PublicAccessBlockConfiguration={
                            'BlockPublicAcls': True,
                            'IgnorePublicAcls': True,
                            'BlockPublicPolicy': True,
                            'RestrictPublicBuckets': True
                        }
                    )
                    
                    print(f"✅ Configured S3 bucket security settings")
                    return True
                    
                except ClientError as create_error:
                    print(f"❌ Failed to create S3 bucket: {create_error}")
                    return False
            else:
                print(f"❌ Error checking S3 bucket: {e}")
                return False
    
    def create_dynamodb_table(self):
        """Create DynamoDB table for state locking"""
        dynamodb = boto3.client('dynamodb', region_name=self.region)
        
        try:
            # Check if table exists
            dynamodb.describe_table(TableName=self.table_name)
            print(f"✅ DynamoDB table '{self.table_name}' already exists")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                try:
                    dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {
                                'AttributeName': 'LockID',
                                'KeyType': 'HASH'
                            }
                        ],
                        AttributeDefinitions=[
                            {
                                'AttributeName': 'LockID',
                                'AttributeType': 'S'
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        Tags=[
                            {
                                'Key': 'Project',
                                'Value': 'aws-devops'
                            },
                            {
                                'Key': 'ManagedBy',
                                'Value': 'terraform'
                            }
                        ]
                    )
                    
                    print(f"✅ Created DynamoDB table: {self.table_name}")
                    print("⏳ Waiting for table to be active...")
                    
                    # Wait for table to be active
                    waiter = dynamodb.get_waiter('table_exists')
                    waiter.wait(TableName=self.table_name)
                    
                    print(f"✅ DynamoDB table is now active")
                    return True
                    
                except ClientError as create_error:
                    print(f"❌ Failed to create DynamoDB table: {create_error}")
                    return False
            else:
                print(f"❌ Error checking DynamoDB table: {e}")
                return False
    
    def setup_backend(self):
        """Set up the complete Terraform backend"""
        print("🚀 Setting up Terraform Backend")
        print("=" * 50)
        print(f"Account ID: {self.account_id}")
        print(f"Region: {self.region}")
        print(f"S3 Bucket: {self.bucket_name}")
        print(f"DynamoDB Table: {self.table_name}")
        print("=" * 50)
        
        # Create S3 bucket
        if not self.create_s3_bucket():
            return False
        
        # Create DynamoDB table
        if not self.create_dynamodb_table():
            return False
        
        print("\n✅ Terraform backend setup completed!")
        print("\nNext steps:")
        print("1. Run 'terraform init' in your Terraform directory")
        print("2. Your state will be stored securely in S3")
        print("3. State locking is enabled via DynamoDB")
        
        return True

if __name__ == "__main__":
    setup = TerraformBackendSetup()
    setup.setup_backend()
