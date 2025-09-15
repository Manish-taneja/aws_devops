#!/usr/bin/env python3
"""
AWS Account Setup Script
Configures AWS CLI and validates account access
"""

import boto3
import subprocess
import sys
import json
from pathlib import Path

class AWSSetup:
    def __init__(self):
        self.account_id = "619564767540"
        self.region = "us-east-1"
        self.root_email = "aws.paytm-common@paytm.com"
        
    def check_aws_cli(self):
        """Check if AWS CLI is installed"""
        try:
            result = subprocess.run(['aws', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ AWS CLI installed: {result.stdout.strip()}")
                return True
            else:
                print("❌ AWS CLI not found")
                return False
        except FileNotFoundError:
            print("❌ AWS CLI not installed")
            return False
    
    def configure_aws_cli(self):
        """Configure AWS CLI with credentials"""
        print("🔧 Configuring AWS CLI...")
        print("Please run the following command to configure AWS CLI:")
        print("aws configure")
        print(f"Account ID: {self.account_id}")
        print(f"Region: {self.region}")
        print("Access Key ID: [Your Access Key]")
        print("Secret Access Key: [Your Secret Key]")
        
    def validate_aws_access(self):
        """Validate AWS account access"""
        try:
            sts = boto3.client('sts')
            response = sts.get_caller_identity()
            
            if response['Account'] == self.account_id:
                print(f"✅ Successfully connected to AWS Account: {self.account_id}")
                print(f"✅ User ARN: {response['Arn']}")
                return True
            else:
                print(f"❌ Connected to wrong account: {response['Account']}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to connect to AWS: {str(e)}")
            return False
    
    def check_terraform(self):
        """Check if Terraform is installed"""
        try:
            result = subprocess.run(['terraform', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Terraform installed: {result.stdout.strip()}")
                return True
            else:
                print("❌ Terraform not found")
                return False
        except FileNotFoundError:
            print("❌ Terraform not installed")
            return False
    
    def create_terraform_backend(self):
        """Create Terraform backend configuration"""
        backend_config = f"""
terraform {{
  backend "s3" {{
    bucket         = "aws-devops-terraform-state-{self.account_id}"
    key            = "terraform.tfstate"
    region         = "{self.region}"
    encrypt        = true
    dynamodb_table = "aws-devops-terraform-locks"
  }}
}}
"""
        
        backend_file = Path("terraform/backend/backend.tf")
        backend_file.write_text(backend_config)
        print(f"✅ Created Terraform backend configuration: {backend_file}")
    
    def setup_environment(self):
        """Set up the complete environment"""
        print("🚀 Setting up AWS DevOps Environment")
        print("=" * 50)
        
        # Check prerequisites
        if not self.check_aws_cli():
            print("Please install AWS CLI first")
            return False
            
        if not self.check_terraform():
            print("Please install Terraform first")
            return False
        
        # Configure AWS CLI
        self.configure_aws_cli()
        
        # Validate access
        if not self.validate_aws_access():
            print("Please configure AWS credentials correctly")
            return False
        
        # Create Terraform backend
        self.create_terraform_backend()
        
        print("\n✅ Environment setup completed!")
        print("Next steps:")
        print("1. Run 'terraform init' in terraform/environments/dev/")
        print("2. Run 'terraform plan' to review changes")
        print("3. Run 'terraform apply' to deploy infrastructure")
        
        return True

if __name__ == "__main__":
    setup = AWSSetup()
    setup.setup_environment()