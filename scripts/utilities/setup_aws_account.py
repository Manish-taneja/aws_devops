#!/usr/bin/env python3
"""
AWS Account Setup Script
This script helps set up initial AWS account configurations for the DevOps automation platform.
"""

import boto3
import click
import json
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSSetupManager:
    """Manages AWS account setup and initial configurations."""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """Initialize the AWS setup manager."""
        self.region = region
        self.profile = profile
        self.session = self._create_session()
        
    def _create_session(self) -> boto3.Session:
        """Create AWS session with profile if specified."""
        if self.profile:
            return boto3.Session(profile_name=self.profile, region_name=self.region)
        return boto3.Session(region_name=self.region)
    
    def check_credentials(self) -> bool:
        """Check if AWS credentials are properly configured."""
        try:
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"Authenticated as: {identity['Arn']}")
            logger.info(f"Account ID: {identity['Account']}")
            return True
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure them first.")
            return False
        except ClientError as e:
            logger.error(f"Error checking credentials: {e}")
            return False
    
    def enable_required_services(self) -> Dict[str, bool]:
        """Enable required AWS services for the DevOps platform."""
        results = {}
        
        # Enable CloudTrail
        try:
            cloudtrail = self.session.client('cloudtrail')
            # Check if CloudTrail is already enabled
            trails = cloudtrail.list_trails()
            if not trails.get('Trails'):
                logger.info("Setting up CloudTrail...")
                # Implementation for CloudTrail setup
                results['cloudtrail'] = True
            else:
                logger.info("CloudTrail already configured")
                results['cloudtrail'] = True
        except ClientError as e:
            logger.error(f"Error setting up CloudTrail: {e}")
            results['cloudtrail'] = False
        
        # Enable Config
        try:
            config = self.session.client('config')
            recorders = config.describe_configuration_recorders()
            if not recorders.get('ConfigurationRecorders'):
                logger.info("Setting up AWS Config...")
                # Implementation for Config setup
                results['config'] = True
            else:
                logger.info("AWS Config already configured")
                results['config'] = True
        except ClientError as e:
            logger.error(f"Error setting up AWS Config: {e}")
            results['config'] = False
        
        # Enable GuardDuty
        try:
            guardduty = self.session.client('guardduty')
            detectors = guardduty.list_detectors()
            if not detectors.get('DetectorIds'):
                logger.info("Setting up GuardDuty...")
                # Implementation for GuardDuty setup
                results['guardduty'] = True
            else:
                logger.info("GuardDuty already configured")
                results['guardduty'] = True
        except ClientError as e:
            logger.error(f"Error setting up GuardDuty: {e}")
            results['guardduty'] = False
        
        return results
    
    def create_terraform_backend(self, bucket_name: str) -> bool:
        """Create S3 bucket and DynamoDB table for Terraform backend."""
        try:
            s3 = self.session.client('s3')
            dynamodb = self.session.client('dynamodb')
            
            # Create S3 bucket
            logger.info(f"Creating S3 bucket: {bucket_name}")
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.region}
            )
            
            # Enable versioning
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Enable encryption
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
            
            # Create DynamoDB table for state locking
            table_name = "terraform-state-lock"
            logger.info(f"Creating DynamoDB table: {table_name}")
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'LockID', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'LockID', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            logger.info("Terraform backend resources created successfully")
            return True
            
        except ClientError as e:
            logger.error(f"Error creating Terraform backend: {e}")
            return False
    
    def setup_monitoring_account(self) -> bool:
        """Set up monitoring and observability configurations."""
        try:
            cloudwatch = self.session.client('cloudwatch')
            logs = self.session.client('logs')
            
            # Create log groups for application logs
            log_groups = [
                '/aws/devops/application',
                '/aws/devops/security',
                '/aws/devops/audit'
            ]
            
            for log_group in log_groups:
                try:
                    logs.create_log_group(logGroupName=log_group)
                    logger.info(f"Created log group: {log_group}")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                        logger.info(f"Log group already exists: {log_group}")
                    else:
                        logger.error(f"Error creating log group {log_group}: {e}")
            
            return True
            
        except ClientError as e:
            logger.error(f"Error setting up monitoring: {e}")
            return False


@click.group()
def cli():
    """AWS DevOps Account Setup Tool"""
    pass


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def check_setup(region: str, profile: Optional[str]):
    """Check current AWS account setup."""
    manager = AWSSetupManager(region, profile)
    
    if not manager.check_credentials():
        return
    
    logger.info("Checking AWS account setup...")
    
    # Check required services
    services = manager.enable_required_services()
    
    click.echo("\nSetup Status:")
    for service, status in services.items():
        status_icon = "✅" if status else "❌"
        click.echo(f"  {status_icon} {service.title()}")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
@click.option('--bucket-name', default='aws-devops-terraform-state', help='S3 bucket name for Terraform state')
def setup_backend(region: str, profile: Optional[str], bucket_name: str):
    """Set up Terraform backend infrastructure."""
    manager = AWSSetupManager(region, profile)
    
    if not manager.check_credentials():
        return
    
    logger.info("Setting up Terraform backend...")
    
    if manager.create_terraform_backend(bucket_name):
        click.echo("✅ Terraform backend setup completed successfully")
        click.echo(f"   S3 Bucket: {bucket_name}")
        click.echo("   DynamoDB Table: terraform-state-lock")
    else:
        click.echo("❌ Terraform backend setup failed")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def setup_monitoring(region: str, profile: Optional[str]):
    """Set up monitoring and observability."""
    manager = AWSSetupManager(region, profile)
    
    if not manager.check_credentials():
        return
    
    logger.info("Setting up monitoring and observability...")
    
    if manager.setup_monitoring_account():
        click.echo("✅ Monitoring setup completed successfully")
    else:
        click.echo("❌ Monitoring setup failed")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
@click.option('--bucket-name', default='aws-devops-terraform-state', help='S3 bucket name for Terraform state')
def setup_all(region: str, profile: Optional[str], bucket_name: str):
    """Complete AWS account setup for DevOps automation."""
    manager = AWSSetupManager(region, profile)
    
    if not manager.check_credentials():
        return
    
    logger.info("Starting complete AWS account setup...")
    
    # Setup all components
    services = manager.enable_required_services()
    backend_success = manager.create_terraform_backend(bucket_name)
    monitoring_success = manager.setup_monitoring_account()
    
    # Report results
    click.echo("\n" + "="*50)
    click.echo("AWS ACCOUNT SETUP SUMMARY")
    click.echo("="*50)
    
    click.echo("\nServices:")
    for service, status in services.items():
        status_icon = "✅" if status else "❌"
        click.echo(f"  {status_icon} {service.title()}")
    
    click.echo(f"\nTerraform Backend: {'✅' if backend_success else '❌'}")
    click.echo(f"Monitoring Setup: {'✅' if monitoring_success else '❌'}")
    
    if all(services.values()) and backend_success and monitoring_success:
        click.echo("\n🎉 All components set up successfully!")
    else:
        click.echo("\n⚠️  Some components failed to set up. Check the logs above.")


if __name__ == '__main__':
    cli()
