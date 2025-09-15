#!/usr/bin/env python3
"""
Monitoring Deployment Script
This script deploys monitoring and observability stack for the AWS DevOps platform.
"""

import boto3
import click
import json
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringDeployer:
    """Deploys monitoring and observability stack."""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """Initialize the monitoring deployer."""
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
            return True
        except NoCredentialsError:
            logger.error("AWS credentials not found.")
            return False
        except ClientError as e:
            logger.error(f"Error checking credentials: {e}")
            return False
    
    def deploy_cloudwatch_dashboard(self, dashboard_name: str, dashboard_body: str) -> bool:
        """Deploy CloudWatch dashboard."""
        try:
            cloudwatch = self.session.client('cloudwatch')
            
            response = cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=dashboard_body
            )
            
            logger.info(f"Dashboard {dashboard_name} deployed successfully")
            return True
            
        except ClientError as e:
            logger.error(f"Error deploying dashboard {dashboard_name}: {e}")
            return False
    
    def create_log_groups(self, log_groups: List[str]) -> bool:
        """Create CloudWatch log groups."""
        try:
            logs = self.session.client('logs')
            
            for log_group in log_groups:
                try:
                    logs.create_log_group(logGroupName=log_group)
                    logger.info(f"Created log group: {log_group}")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                        logger.info(f"Log group already exists: {log_group}")
                    else:
                        logger.error(f"Error creating log group {log_group}: {e}")
                        return False
            
            return True
            
        except ClientError as e:
            logger.error(f"Error creating log groups: {e}")
            return False
    
    def setup_cloudwatch_alarms(self, alarms_config: List[Dict]) -> bool:
        """Setup CloudWatch alarms."""
        try:
            cloudwatch = self.session.client('cloudwatch')
            
            for alarm_config in alarms_config:
                try:
                    cloudwatch.put_metric_alarm(
                        AlarmName=alarm_config['name'],
                        AlarmDescription=alarm_config.get('description', ''),
                        MetricName=alarm_config['metric_name'],
                        Namespace=alarm_config['namespace'],
                        Statistic=alarm_config.get('statistic', 'Average'),
                        Period=alarm_config.get('period', 300),
                        EvaluationPeriods=alarm_config.get('evaluation_periods', 2),
                        Threshold=alarm_config['threshold'],
                        ComparisonOperator=alarm_config['comparison_operator'],
                        ActionsEnabled=alarm_config.get('actions_enabled', True)
                    )
                    logger.info(f"Created alarm: {alarm_config['name']}")
                except ClientError as e:
                    logger.error(f"Error creating alarm {alarm_config['name']}: {e}")
                    return False
            
            return True
            
        except ClientError as e:
            logger.error(f"Error setting up alarms: {e}")
            return False
    
    def deploy_monitoring_stack(self, project_name: str) -> Dict[str, bool]:
        """Deploy complete monitoring stack."""
        results = {}
        
        if not self.check_credentials():
            return {'error': 'AWS credentials not configured'}
        
        # Create log groups
        log_groups = [
            f'/aws/{project_name}/application',
            f'/aws/{project_name}/security',
            f'/aws/{project_name}/audit',
            f'/aws/{project_name}/access-logs'
        ]
        
        results['log_groups'] = self.create_log_groups(log_groups)
        
        # Setup basic alarms
        alarms_config = [
            {
                'name': f'{project_name}-high-cpu',
                'description': 'High CPU utilization',
                'metric_name': 'CPUUtilization',
                'namespace': 'AWS/EC2',
                'threshold': 80.0,
                'comparison_operator': 'GreaterThanThreshold'
            },
            {
                'name': f'{project_name}-high-memory',
                'description': 'High memory utilization',
                'metric_name': 'MemoryUtilization',
                'namespace': 'AWS/EC2',
                'threshold': 85.0,
                'comparison_operator': 'GreaterThanThreshold'
            }
        ]
        
        results['alarms'] = self.setup_cloudwatch_alarms(alarms_config)
        
        # Deploy dashboard
        try:
            with open('monitoring/dashboards/aws-devops-dashboard.json', 'r') as f:
                dashboard_body = f.read()
            
            results['dashboard'] = self.deploy_cloudwatch_dashboard(
                f'{project_name}-dashboard',
                dashboard_body
            )
        except FileNotFoundError:
            logger.warning("Dashboard file not found, skipping dashboard deployment")
            results['dashboard'] = False
        
        return results


@click.group()
def cli():
    """AWS Monitoring Deployment Tool"""
    pass


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
@click.option('--project-name', default='aws-devops-automation', help='Project name')
def deploy_monitoring(region: str, profile: Optional[str], project_name: str):
    """Deploy monitoring and observability stack."""
    deployer = MonitoringDeployer(region, profile)
    results = deployer.deploy_monitoring_stack(project_name)
    
    if 'error' in results:
        click.echo(f"❌ {results['error']}")
        return
    
    # Display results
    click.echo("\n" + "="*50)
    click.echo("MONITORING DEPLOYMENT RESULTS")
    click.echo("="*50)
    
    for component, success in results.items():
        status_icon = "✅" if success else "❌"
        click.echo(f"{status_icon} {component.replace('_', ' ').title()}")
    
    if all(results.values()):
        click.echo("\n🎉 Monitoring stack deployed successfully!")
    else:
        click.echo("\n⚠️  Some components failed to deploy. Check the logs above.")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def list_dashboards(region: str, profile: Optional[str]):
    """List CloudWatch dashboards."""
    deployer = MonitoringDeployer(region, profile)
    
    if not deployer.check_credentials():
        return
    
    try:
        cloudwatch = deployer.session.client('cloudwatch')
        dashboards = cloudwatch.list_dashboards()
        
        click.echo("CloudWatch Dashboards:")
        for dashboard in dashboards['DashboardEntries']:
            click.echo(f"  - {dashboard['DashboardName']}")
            
    except ClientError as e:
        click.echo(f"❌ Error listing dashboards: {e}")


@cli.command()
@click.option('--region', default='us-east-1', help='AWS region')
@click.option('--profile', help='AWS profile to use')
def list_alarms(region: str, profile: Optional[str]):
    """List CloudWatch alarms."""
    deployer = MonitoringDeployer(region, profile)
    
    if not deployer.check_credentials():
        return
    
    try:
        cloudwatch = deployer.session.client('cloudwatch')
        alarms = cloudwatch.describe_alarms()
        
        click.echo("CloudWatch Alarms:")
        for alarm in alarms['MetricAlarms']:
            status = alarm['StateValue']
            status_icon = "🟢" if status == "OK" else "🔴"
            click.echo(f"  {status_icon} {alarm['AlarmName']} - {status}")
            
    except ClientError as e:
        click.echo(f"❌ Error listing alarms: {e}")


if __name__ == '__main__':
    cli()
