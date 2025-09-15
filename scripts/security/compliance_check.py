#!/usr/bin/env python3
"""
AWS Security Compliance Check Script
This script performs various security compliance checks on AWS resources.
"""

import boto3
import click
import json
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityComplianceChecker:
    """Performs security compliance checks on AWS resources."""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """Initialize the security compliance checker."""
        self.region = region
        self.profile = profile
        self.session = self._create_session()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'region': region,
            'checks': {}
        }
        
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
            return True
        except NoCredentialsError:
            logger.error("AWS credentials not found.")
            return False
        except ClientError as e:
            logger.error(f"Error checking credentials: {e}")
            return False
    
    def check_s3_bucket_encryption(self) -> Dict[str, Any]:
        """Check S3 bucket encryption settings."""
        result = {
            'status': 'PASS',
            'issues': [],
            'details': {}
        }
        
        try:
            s3 = self.session.client('s3')
            buckets = s3.list_buckets()
            
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                try:
                    # Check encryption configuration
                    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                    result['details'][bucket_name] = {
                        'encryption_enabled': True,
                        'encryption_rules': encryption['ServerSideEncryptionConfiguration']['Rules']
                    }
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                        result['status'] = 'FAIL'
                        result['issues'].append(f"Bucket {bucket_name} does not have encryption enabled")
                        result['details'][bucket_name] = {
                            'encryption_enabled': False
                        }
                    else:
                        logger.error(f"Error checking bucket {bucket_name}: {e}")
                        
        except ClientError as e:
            logger.error(f"Error listing buckets: {e}")
            result['status'] = 'ERROR'
            
        return result
    
    def check_iam_password_policy(self) -> Dict[str, Any]:
        """Check IAM password policy compliance."""
        result = {
            'status': 'PASS',
            'issues': [],
            'details': {}
        }
        
        try:
            iam = self.session.client('iam')
            policy = iam.get_account_password_policy()
            password_policy = policy['PasswordPolicy']
            
            # Check minimum password length
            if password_policy.get('MinimumPasswordLength', 0) < 12:
                result['status'] = 'FAIL'
                result['issues'].append("Minimum password length should be at least 12 characters")
            
            # Check password complexity requirements
            if not password_policy.get('RequireUppercaseCharacters', False):
                result['status'] = 'FAIL'
                result['issues'].append("Password policy should require uppercase characters")
                
            if not password_policy.get('RequireLowercaseCharacters', False):
                result['status'] = 'FAIL'
                result['issues'].append("Password policy should require lowercase characters")
                
            if not password_policy.get('RequireNumbers', False):
                result['status'] = 'FAIL'
                result['issues'].append("Password policy should require numbers")
                
            if not password_policy.get('RequireSymbols', False):
                result['status'] = 'FAIL'
                result['issues'].append("Password policy should require symbols")
            
            result['details'] = password_policy
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                result['status'] = 'FAIL'
                result['issues'].append("No password policy configured")
            else:
                logger.error(f"Error checking password policy: {e}")
                result['status'] = 'ERROR'
                
        return result
    
    def check_root_account_usage(self) -> Dict[str, Any]:
        """Check for root account usage."""
        result = {
            'status': 'PASS',
            'issues': [],
            'details': {}
        }
        
        try:
            cloudtrail = self.session.client('cloudtrail')
            
            # Look for root account usage in the last 30 days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            
            events = cloudtrail.lookup_events(
                StartTime=start_time,
                EndTime=end_time,
                LookupAttributes=[
                    {
                        'AttributeKey': 'Username',
                        'AttributeValue': 'root'
                    }
                ]
            )
            
            if events['Events']:
                result['status'] = 'FAIL'
                result['issues'].append(f"Root account used {len(events['Events'])} times in the last 30 days")
                result['details']['root_events'] = [
                    {
                        'EventTime': event['EventTime'].isoformat(),
                        'EventName': event['EventName'],
                        'EventSource': event['EventSource']
                    }
                    for event in events['Events'][:10]  # Limit to first 10 events
                ]
            else:
                result['details']['root_events'] = []
                
        except ClientError as e:
            logger.error(f"Error checking root account usage: {e}")
            result['status'] = 'ERROR'
            
        return result
    
    def check_mfa_enabled(self) -> Dict[str, Any]:
        """Check if MFA is enabled for IAM users."""
        result = {
            'status': 'PASS',
            'issues': [],
            'details': {
                'users_without_mfa': [],
                'users_with_mfa': []
            }
        }
        
        try:
            iam = self.session.client('iam')
            users = iam.list_users()
            
            for user in users['Users']:
                username = user['UserName']
                
                # Skip service accounts
                if username.startswith('aws-') or username.startswith('service-'):
                    continue
                
                try:
                    mfa_devices = iam.list_mfa_devices(UserName=username)
                    
                    if mfa_devices['MFADevices']:
                        result['details']['users_with_mfa'].append(username)
                    else:
                        result['status'] = 'FAIL'
                        result['issues'].append(f"User {username} does not have MFA enabled")
                        result['details']['users_without_mfa'].append(username)
                        
                except ClientError as e:
                    logger.error(f"Error checking MFA for user {username}: {e}")
                    
        except ClientError as e:
            logger.error(f"Error listing users: {e}")
            result['status'] = 'ERROR'
            
        return result
    
    def check_public_s3_buckets(self) -> Dict[str, Any]:
        """Check for publicly accessible S3 buckets."""
        result = {
            'status': 'PASS',
            'issues': [],
            'details': {
                'public_buckets': []
            }
        }
        
        try:
            s3 = self.session.client('s3')
            buckets = s3.list_buckets()
            
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                try:
                    # Check bucket ACL
                    acl = s3.get_bucket_acl(Bucket=bucket_name)
                    
                    for grant in acl['Grants']:
                        grantee = grant.get('Grantee', {})
                        if grantee.get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers':
                            result['status'] = 'FAIL'
                            result['issues'].append(f"Bucket {bucket_name} has public read access")
                            result['details']['public_buckets'].append({
                                'bucket': bucket_name,
                                'permission': 'READ'
                            })
                            break
                            
                except ClientError as e:
                    logger.error(f"Error checking bucket ACL for {bucket_name}: {e}")
                    
        except ClientError as e:
            logger.error(f"Error listing buckets: {e}")
            result['status'] = 'ERROR'
            
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all security compliance checks."""
        logger.info("Starting security compliance checks...")
        
        if not self.check_credentials():
            return {'error': 'AWS credentials not configured'}
        
        # Run all checks
        self.results['checks']['s3_encryption'] = self.check_s3_bucket_encryption()
        self.results['checks']['iam_password_policy'] = self.check_iam_password_policy()
        self.results['checks']['root_account_usage'] = self.check_root_account_usage()
        self.results['checks']['mfa_enabled'] = self.check_mfa_enabled()
        self.results['checks']['public_s3_buckets'] = self.check_public_s3_buckets()
        
        # Calculate overall status
        failed_checks = [check for check in self.results['checks'].values() 
                        if check['status'] == 'FAIL']
        error_checks = [check for check in self.results['checks'].values() 
                       if check['status'] == 'ERROR']
        
        if error_checks:
            self.results['overall_status'] = 'ERROR'
        elif failed_checks:
            self.results['overall_status'] = 'FAIL'
        else:
            self.results['overall_status'] = 'PASS'
        
        return self.results


@click.group()
def cli():
    """AWS Security Compliance Check Tool"""
    pass


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
@click.option('--output', type=click.Path(), help='Output file for results')
def check_compliance(region: str, profile: Optional[str], output: Optional[str]):
    """Run all security compliance checks."""
    checker = SecurityComplianceChecker(region, profile)
    results = checker.run_all_checks()
    
    if 'error' in results:
        click.echo(f"❌ {results['error']}")
        return
    
    # Display results
    click.echo("\n" + "="*60)
    click.echo("AWS SECURITY COMPLIANCE CHECK RESULTS")
    click.echo("="*60)
    click.echo(f"Timestamp: {results['timestamp']}")
    click.echo(f"Region: {results['region']}")
    click.echo(f"Overall Status: {results['overall_status']}")
    
    for check_name, check_result in results['checks'].items():
        status_icon = "✅" if check_result['status'] == 'PASS' else "❌"
        click.echo(f"\n{status_icon} {check_name.replace('_', ' ').title()}: {check_result['status']}")
        
        if check_result['issues']:
            for issue in check_result['issues']:
                click.echo(f"   ⚠️  {issue}")
    
    # Save results to file if specified
    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        click.echo(f"\n📄 Results saved to: {output}")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def check_s3_encryption(region: str, profile: Optional[str]):
    """Check S3 bucket encryption."""
    checker = SecurityComplianceChecker(region, profile)
    result = checker.check_s3_bucket_encryption()
    
    click.echo(f"S3 Encryption Check: {result['status']}")
    if result['issues']:
        for issue in result['issues']:
            click.echo(f"  ⚠️  {issue}")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def check_mfa(region: str, profile: Optional[str]):
    """Check MFA configuration for IAM users."""
    checker = SecurityComplianceChecker(region, profile)
    result = checker.check_mfa_enabled()
    
    click.echo(f"MFA Check: {result['status']}")
    if result['issues']:
        for issue in result['issues']:
            click.echo(f"  ⚠️  {issue}")
    
    click.echo(f"\nUsers with MFA: {len(result['details']['users_with_mfa'])}")
    click.echo(f"Users without MFA: {len(result['details']['users_without_mfa'])}")


if __name__ == '__main__':
    cli()
