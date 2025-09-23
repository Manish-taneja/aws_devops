# Quick Start Guide

This guide will help you get started with the AWS Super Multi-Agent MCP Server quickly.

## Prerequisites

Before you begin, ensure you have the following installed:

- **AWS CLI** (version 2.x)
- **Terraform** (version >= 1.0)
- **Python** (version 3.8+)
- **Git**

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Manish-taneja/aws-super-mcp.git
cd aws-super-mcp

# Install Python dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

## Step 2: Initial AWS Account Setup

Run the AWS account setup script to configure your AWS account with the necessary services and resources:

```bash
# Check current setup
python scripts/utilities/setup_aws_account.py check-setup

# Setup Terraform backend (S3 bucket and DynamoDB table)
python scripts/utilities/setup_aws_account.py setup-backend

# Setup monitoring and observability
python scripts/utilities/setup_aws_account.py setup-monitoring

# Or run complete setup
python scripts/utilities/setup_aws_account.py setup-all
```

## Step 3: Configure Environment Variables

Copy and customize the environment configuration:

```bash
# Copy the example configuration
cp config/environments/dev.tfvars.example config/environments/dev.tfvars

# Edit the configuration with your specific values
nano config/environments/dev.tfvars
```

## Step 4: Deploy Infrastructure

Deploy the development environment infrastructure:

```bash
# Navigate to the development environment
cd terraform/environments/dev

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

## Step 5: Verify Deployment

Check that all resources were created successfully:

```bash
# View Terraform outputs
terraform output

# Run security compliance checks
python scripts/security/compliance_check.py check-compliance

# Check monitoring setup
aws cloudwatch list-dashboards
```

## Step 6: Set Up CI/CD (Optional)

If you want to use GitHub Actions for automated deployments:

1. **Fork the repository** to your GitHub account
2. **Add AWS credentials** as GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
3. **Push changes** to trigger the CI/CD pipeline

## Step 7: Monitor Your Infrastructure

Access the monitoring dashboards:

1. **CloudWatch Dashboard**: Open AWS Console → CloudWatch → Dashboards
2. **Application Logs**: CloudWatch → Log groups → `/aws/aws-devops-automation/application`
3. **Security Logs**: CloudWatch → Log groups → `/aws/aws-devops-automation/security`

## Common Commands

### Infrastructure Management

```bash
# Deploy to development
cd terraform/environments/dev
terraform apply

# Deploy to staging
cd terraform/environments/staging
terraform apply

# Deploy to production
cd terraform/environments/prod
terraform apply

# Destroy infrastructure (be careful!)
terraform destroy
```

### Security and Compliance

```bash
# Run all security checks
python scripts/security/compliance_check.py check-compliance

# Check specific security aspects
python scripts/security/compliance_check.py check-s3-encryption
python scripts/security/compliance_check.py check-mfa
```

### Monitoring and Observability

```bash
# Deploy monitoring stack
python scripts/monitoring/deploy_monitoring.py

# Check CloudWatch metrics
aws cloudwatch list-metrics --namespace AWS/EC2

# View recent logs
aws logs tail /aws/aws-devops-automation/application --follow
```

### Cost Optimization

```bash
# Generate cost report
python scripts/cost-optimization/generate_report.py

# Check for unused resources
python scripts/cost-optimization/find_unused_resources.py
```

## Troubleshooting

### Common Issues

1. **Terraform Backend Error**
   ```bash
   # Reinitialize with backend config
   terraform init -reconfigure
   ```

2. **AWS Credentials Error**
   ```bash
   # Verify credentials
   aws sts get-caller-identity
   ```

3. **Permission Denied**
   - Ensure your AWS user/role has the necessary permissions
   - Check IAM policies for required services

### Getting Help

- **Documentation**: Check the `docs/` directory for detailed guides
- **Runbooks**: See `docs/runbooks/` for operational procedures
- **Troubleshooting**: Refer to `docs/troubleshooting/` for common issues

## Next Steps

After completing the quick start:

1. **Review the architecture** in `docs/architecture/`
2. **Customize the configuration** for your specific needs
3. **Set up additional environments** (staging, production)
4. **Configure monitoring alerts** based on your requirements
5. **Implement security best practices** from the compliance checks

## Security Notes

- Never commit sensitive information like AWS keys or passwords
- Use AWS Secrets Manager for storing secrets
- Regularly run security compliance checks
- Keep dependencies updated
- Monitor for unusual activity

## Support

For issues or questions:

1. Check the troubleshooting guides
2. Review the documentation
3. Run the diagnostic scripts
4. Contact the DevOps team

---

**Remember**: This is a production-ready setup. Always test changes in development before applying to production environments.
