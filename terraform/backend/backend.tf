# Terraform Backend Configuration
# This file configures the remote backend for storing Terraform state

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 Backend Configuration
  backend "s3" {
    bucket         = "aws-devops-terraform-state"
    key            = "global/s3/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
    
    # Enable state locking and consistency checking
    # This prevents concurrent modifications to the same state
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.tags
  }
}

# Variables for backend configuration
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Default tags for all resources"
  type        = map(string)
  default = {
    Project     = "aws-devops-automation"
    ManagedBy   = "terraform"
    Environment = "global"
  }
}
