# AWS Account Setup Guide

## Account Information
- **Account ID**: 619564767540
- **Root Email**: aws.paytm-common@paytm.com
- **Default Region**: us-east-1

## Prerequisites
1. AWS CLI installed
2. Terraform installed
3. Python 3.x installed
4. Root credentials for the AWS account

## Setup Steps

### 1. Configure AWS CLI
```bash
aws configure
```
Enter your credentials when prompted:
- AWS Access Key ID: [Your Access Key]
- AWS Secret Access Key: [Your Secret Key]
- Default region name: us-east-1
- Default output format: json

### 2. Create Terraform Backend
```bash
cd scripts/utilities
python3 create_s3_backend.py
```

This will create:
- S3 bucket: `aws-devops-terraform-state-619564767540`
- DynamoDB table: `aws-devops-terraform-locks`

### 3. Initialize Terraform
```bash
cd terraform/environments/dev
terraform init
```

### 4. Plan and Apply Infrastructure
```bash
terraform plan -var-file="../../config/environments/dev.tfvars"
terraform apply -var-file="../../config/environments/dev.tfvars"
```

## Environment Configurations

### Development Environment
- File: `config/environments/dev.tfvars`
- VPC CIDR: 10.0.0.0/16
- Instance Type: t3.micro
- Database: db.t3.micro

### Production Environment
- File: `config/environments/prod.tfvars`
- VPC CIDR: 10.1.0.0/16
- Instance Type: t3.medium
- Database: db.t3.small
- Multi-AZ: Enabled

## Security Best Practices
1. Enable MFA on root account
2. Create IAM users for daily operations
3. Use least privilege principle
4. Enable CloudTrail for audit logging
5. Set up billing alerts

## Next Steps
1. Deploy basic infrastructure
2. Set up monitoring and alerting
3. Configure CI/CD pipelines
4. Implement security compliance checks
5. Set up cost optimization tools

## Support
For any issues or questions, refer to the troubleshooting guide or contact the DevOps team.
