#!/bin/bash

# User data script for EC2 instances
# This script sets up the application environment

# Update system
yum update -y

# Install required packages
yum install -y httpd mysql

# Start and enable Apache
systemctl start httpd
systemctl enable httpd

# Create a simple index page
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>AWS DevOps Application</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { background: #232f3e; color: white; padding: 20px; border-radius: 5px; }
        .content { padding: 20px; }
        .status { background: #f0f8ff; padding: 15px; border-left: 4px solid #0073bb; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AWS DevOps Application</h1>
            <p>Environment: ${environment}</p>
        </div>
        <div class="content">
            <div class="status">
                <h3>Application Status</h3>
                <p>✅ Application is running successfully</p>
                <p>✅ Connected to database: ${db_endpoint}</p>
                <p>✅ Load balancer is healthy</p>
            </div>
            <h3>System Information</h3>
            <ul>
                <li>Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</li>
                <li>Availability Zone: $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)</li>
                <li>Launch Time: $(date)</li>
            </ul>
        </div>
    </div>
</body>
</html>
EOF

# Create a health check endpoint
cat > /var/www/html/health.html << 'EOF'
{
    "status": "healthy",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "environment": "${environment}",
    "instance_id": "$(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
}
EOF

# Set proper permissions
chown -R apache:apache /var/www/html
chmod -R 755 /var/www/html

# Configure Apache to serve the health check
echo "Alias /health /var/www/html/health.html" >> /etc/httpd/conf/httpd.conf

# Restart Apache
systemctl restart httpd

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/httpd/access_log",
                        "log_group_name": "/aws/ec2/${environment}",
                        "log_stream_name": "{instance_id}/apache/access"
                    },
                    {
                        "file_path": "/var/log/httpd/error_log",
                        "log_group_name": "/aws/ec2/${environment}",
                        "log_stream_name": "{instance_id}/apache/error"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "AWS/EC2",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": ["used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["*"]
            },
            "mem": {
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Log completion
echo "User data script completed at $(date)" >> /var/log/user-data.log
