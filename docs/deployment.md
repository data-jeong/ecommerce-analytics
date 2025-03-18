# Deployment Guide

## Infrastructure Setup

### Cloud Provider Setup (AWS)

1. **VPC Configuration**:

```bash
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ecommerce-analytics-vpc}]'
```

2. **Subnet Creation**:

```bash
# Public subnet
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a

# Private subnet
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1a
```

3. **Security Groups**:

```bash
# API security group
aws ec2 create-security-group --group-name api-sg --description "API Security Group" --vpc-id vpc-xxx

# Database security group
aws ec2 create-security-group --group-name db-sg --description "Database Security Group" --vpc-id vpc-xxx
```

### Database Setup

1. **PostgreSQL (RDS)**:

```bash
aws rds create-db-instance \
    --db-instance-identifier ecommerce-analytics \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --master-username admin \
    --master-user-password <password> \
    --allocated-storage 100 \
    --vpc-security-group-ids sg-xxx \
    --subnet-group-name ecommerce-analytics-subnet-group
```

2. **Redis (ElastiCache)**:

```bash
aws elasticache create-cache-cluster \
    --cache-cluster-id ecommerce-analytics-cache \
    --cache-node-type cache.t3.medium \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids sg-xxx \
    --cache-subnet-group-name ecommerce-analytics-subnet-group
```

### Container Registry

1. **Create ECR Repository**:

```bash
aws ecr create-repository \
    --repository-name ecommerce-analytics \
    --image-scanning-configuration scanOnPush=true
```

2. **Build and Push Docker Image**:

```bash
# Build image
docker build -t ecommerce-analytics .

# Tag image
docker tag ecommerce-analytics:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ecommerce-analytics:latest

# Push image
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/ecommerce-analytics:latest
```

## Application Deployment

### ECS Cluster Setup

1. **Create ECS Cluster**:

```bash
aws ecs create-cluster --cluster-name ecommerce-analytics
```

2. **Task Definition**:

```json
{
  "family": "ecommerce-analytics",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "${ECR_REPO_URL}:latest",
      "cpu": 256,
      "memory": 512,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OLTP_DATABASE_URL",
          "value": "postgresql://user:pass@host:5432/db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ecommerce-analytics",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

3. **Service Creation**:

```bash
aws ecs create-service \
    --cluster ecommerce-analytics \
    --service-name api \
    --task-definition ecommerce-analytics:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

### Load Balancer Setup

1. **Create ALB**:

```bash
aws elbv2 create-load-balancer \
    --name ecommerce-analytics-alb \
    --subnets subnet-xxx subnet-yyy \
    --security-groups sg-xxx
```

2. **Target Group**:

```bash
aws elbv2 create-target-group \
    --name ecommerce-analytics-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id vpc-xxx \
    --target-type ip
```

3. **Listener**:

```bash
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=$CERT_ARN \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

## Monitoring Setup

### CloudWatch

1. **Log Group**:

```bash
aws logs create-log-group --log-group-name /ecs/ecommerce-analytics
```

2. **Metrics**:

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name api-high-cpu \
    --alarm-description "High CPU utilization" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions $SNS_TOPIC_ARN
```

### X-Ray

1. **Enable Tracing**:

```bash
aws xray create-sampling-rule \
    --sampling-rule '{
        "RuleName": "ecommerce-analytics",
        "Priority": 1000,
        "FixedRate": 0.05,
        "ReservoirSize": 1,
        "ServiceName": "ecommerce-analytics",
        "ServiceType": "*",
        "Host": "*",
        "HTTPMethod": "*",
        "URLPath": "*",
        "Version": 1
    }'
```

## CI/CD Pipeline

### CodePipeline Setup

1. **Create Pipeline**:

```bash
aws codepipeline create-pipeline \
    --pipeline-name ecommerce-analytics \
    --pipeline-config file://pipeline-config.json
```

2. **Build Specification**:

```yaml
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
```

## Database Migration

### Initial Setup

1. **Create Migration User**:

```sql
CREATE USER migration_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_analytics TO migration_user;
```

2. **Run Migrations**:

```bash
# Development
alembic upgrade head

# Production
alembic -x env=production upgrade head
```

### Backup Strategy

1. **Daily Backups**:

```bash
# Manual backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup.dump

# Automated backup (cron)
0 0 * * * /usr/local/bin/backup-db.sh
```

2. **Restore Procedure**:

```bash
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME backup.dump
```

## SSL/TLS Setup

1. **Generate Certificate**:

```bash
aws acm request-certificate \
    --domain-name api.ecommerce-analytics.com \
    --validation-method DNS \
    --subject-alternative-names "*.ecommerce-analytics.com"
```

2. **Configure ALB**:

```bash
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --certificates CertificateArn=$CERT_ARN
```

## Environment Variables

1. **Parameter Store**:

```bash
# Store secrets
aws ssm put-parameter \
    --name "/ecommerce-analytics/prod/db-password" \
    --value "your-secure-password" \
    --type SecureString

# Retrieve secrets
aws ssm get-parameter \
    --name "/ecommerce-analytics/prod/db-password" \
    --with-decryption
```

2. **Environment Configuration**:

```bash
# Production
export OLTP_DATABASE_URL="postgresql://user:pass@host:5432/db"
export REDIS_URL="redis://host:6379/0"
export JWT_SECRET="your-jwt-secret"
export API_KEY_SALT="your-api-key-salt"
```

## Rollback Procedure

1. **Service Rollback**:

```bash
# Roll back to previous task definition
aws ecs update-service \
    --cluster ecommerce-analytics \
    --service api \
    --task-definition ecommerce-analytics:$PREVIOUS_VERSION

# Roll back database
alembic downgrade -1
```

2. **Monitoring Rollback**:

```bash
# Watch service events
aws ecs describe-services \
    --cluster ecommerce-analytics \
    --services api

# Check container logs
aws logs get-log-events \
    --log-group-name /ecs/ecommerce-analytics \
    --log-stream-name api/container-id
```
