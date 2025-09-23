# 🚀 Production Deployment Guide

This guide provides comprehensive instructions for deploying the SMS Financial Insights Platform in production environments.

## 📋 **Table of Contents**

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Provider Deployment](#cloud-provider-deployment)
6. [Database Setup](#database-setup)
7. [Security Configuration](#security-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Performance Optimization](#performance-optimization)
11. [Troubleshooting](#troubleshooting)

---

## 🔧 **Prerequisites**

### **System Requirements**

- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **CPU**: 4+ cores (8+ cores recommended)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 100GB+ SSD storage
- **Network**: Stable internet connection with adequate bandwidth

### **Software Requirements**

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+
- **MongoDB**: 7.0+ (Atlas recommended)
- **Python**: 3.8+ (if running without Docker)

### **External Services**

- **MongoDB Atlas**: Database hosting
- **Groq API**: Primary AI provider
- **Gemini API**: Fallback AI provider
- **Domain & SSL**: For HTTPS access
- **Email Service**: For notifications (optional)

---

## ⚙️ **Environment Setup**

### **1. Clone Repository**

```bash
git clone https://github.com/yourusername/smsComplete.git
cd smsComplete
```

### **2. Configure Environment Variables**

```bash
# Copy environment template
cp env.example .env

# Edit with your production values
nano .env
```

**Required Environment Variables:**

```bash
# MongoDB Configuration
MONGO_ROOT_USERNAME=your_secure_username
MONGO_ROOT_PASSWORD=your_secure_password
MONGODB_DB=pluto_money

# AI Provider Keys
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

# Security
JWT_SECRET_KEY=your_jwt_secret_key_change_this

# Production Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### **3. SSL Certificate Setup**

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option 1: Use Let's Encrypt (Recommended)
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# Copy certificates
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# Option 2: Self-signed certificates (Development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

---

## 🐳 **Docker Deployment**

### **Production Deployment**

```bash
# Build and start all services
docker-compose -f docker-compose.yml up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### **Development Deployment**

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d
```

### **Service URLs**

- **SMS Processing API**: http://localhost:8000
- **Analytics Dashboard**: http://localhost:8501
- **Financial Chat API**: http://localhost:8001
- **MongoDB**: localhost:27017
- **Nginx (with SSL)**: https://yourdomain.com

### **Scaling Services**

```bash
# Scale specific services
docker-compose up -d --scale sms-processing=3
docker-compose up -d --scale chat-api=2

# Update service configuration
docker-compose up -d --force-recreate sms-processing
```

---

## ☸️ **Kubernetes Deployment**

### **1. Create Namespace**

```bash
kubectl create namespace sms-platform
```

### **2. Deploy MongoDB**

```yaml
# mongodb-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mongodb
  namespace: sms-platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:7.0
        ports:
        - containerPort: 27017
        env:
        - name: MONGO_INITDB_ROOT_USERNAME
          valueFrom:
            secretKeyRef:
              name: mongodb-secret
              key: username
        - name: MONGO_INITDB_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mongodb-secret
              key: password
        volumeMounts:
        - name: mongodb-storage
          mountPath: /data/db
      volumes:
      - name: mongodb-storage
        persistentVolumeClaim:
          claimName: mongodb-pvc
```

### **3. Deploy SMS Processing Service**

```yaml
# sms-processing-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sms-processing
  namespace: sms-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sms-processing
  template:
    metadata:
      labels:
        app: sms-processing
    spec:
      containers:
      - name: sms-processing
        image: yourusername/sms-processing:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: mongodb-uri
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### **4. Deploy Analytics Service**

```yaml
# analytics-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics
  namespace: sms-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: analytics
  template:
    metadata:
      labels:
        app: analytics
    spec:
      containers:
      - name: analytics
        image: yourusername/sms-analytics:latest
        ports:
        - containerPort: 8501
        env:
        - name: MONGODB_URI
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: mongodb-uri
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: groq-api-key
```

### **5. Apply Kubernetes Configurations**

```bash
# Create secrets
kubectl create secret generic mongodb-secret \
  --from-literal=username=admin \
  --from-literal=password=your-secure-password \
  -n sms-platform

kubectl create secret generic app-secrets \
  --from-literal=mongodb-uri=mongodb://admin:password@mongodb:27017/pluto_money \
  --from-literal=groq-api-key=your-groq-key \
  --from-literal=gemini-api-key=your-gemini-key \
  -n sms-platform

# Deploy services
kubectl apply -f k8s/ -n sms-platform

# Check deployment status
kubectl get pods -n sms-platform
kubectl get services -n sms-platform
```

---

## ☁️ **Cloud Provider Deployment**

### **AWS Deployment**

#### **Using ECS Fargate**

```bash
# Install AWS CLI and ECS CLI
pip install awscli
curl -Lo ecs-cli https://amazon-ecs-cli.s3.amazonaws.com/ecs-cli-linux-amd64-latest
chmod +x ecs-cli && sudo mv ecs-cli /usr/local/bin

# Configure ECS CLI
ecs-cli configure --cluster sms-platform --region us-east-1 --default-launch-type FARGATE

# Create cluster
ecs-cli up --cluster-config sms-platform --ecs-profile sms-platform

# Deploy services
ecs-cli compose --project-name sms-platform service up --cluster-config sms-platform
```

#### **Using EKS**

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create EKS cluster
eksctl create cluster --name sms-platform --region us-east-1 --nodegroup-name workers --node-type t3.medium --nodes 3

# Deploy to EKS
kubectl apply -f k8s/
```

### **Google Cloud Deployment**

#### **Using Cloud Run**

```bash
# Build and push images
gcloud builds submit --tag gcr.io/PROJECT-ID/sms-processing extract-sms-email-data/
gcloud builds submit --tag gcr.io/PROJECT-ID/sms-analytics sms/

# Deploy services
gcloud run deploy sms-processing --image gcr.io/PROJECT-ID/sms-processing --platform managed --region us-central1
gcloud run deploy sms-analytics --image gcr.io/PROJECT-ID/sms-analytics --platform managed --region us-central1
```

#### **Using GKE**

```bash
# Create GKE cluster
gcloud container clusters create sms-platform --num-nodes=3 --zone us-central1-a

# Get credentials
gcloud container clusters get-credentials sms-platform --zone us-central1-a

# Deploy services
kubectl apply -f k8s/
```

### **Azure Deployment**

#### **Using Container Instances**

```bash
# Create resource group
az group create --name sms-platform --location eastus

# Deploy container group
az container create --resource-group sms-platform --file azure-container-group.yaml
```

---

## 💾 **Database Setup**

### **MongoDB Atlas Setup**

1. **Create MongoDB Atlas Account**
   - Sign up at [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Create a new project

2. **Create Cluster**
   ```bash
   # Choose cluster configuration
   - Cloud Provider: AWS/Google Cloud/Azure
   - Region: Choose closest to your users
   - Cluster Tier: M10+ for production
   ```

3. **Configure Network Access**
   ```bash
   # Add IP addresses or 0.0.0.0/0 for all access
   # Configure VPC peering for enhanced security
   ```

4. **Create Database User**
   ```bash
   # Create user with read/write permissions
   # Use strong password and store securely
   ```

5. **Get Connection String**
   ```bash
   mongodb+srv://username:password@cluster.mongodb.net/pluto_money?retryWrites=true&w=majority
   ```

### **Local MongoDB Setup**

```bash
# Install MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Create database and user
mongosh
use pluto_money
db.createUser({
  user: "admin",
  pwd: "secure-password",
  roles: ["readWrite", "dbAdmin"]
})
```

### **Database Indexes**

```javascript
// Create performance indexes
db.financial_transactions.createIndex({"user_id": 1})
db.financial_transactions.createIndex({"transaction_date": 1})
db.financial_transactions.createIndex({"user_id": 1, "transaction_date": -1})
db.user_financial_transactions.createIndex({"user_id": 1})
db.user_financial_transactions.createIndex({"transaction_date": 1})
db.sms_data.createIndex({"user_id": 1})
db.sms_fin_rawdata.createIndex({"user_id": 1, "isprocessed": 1})
```

---

## 🔒 **Security Configuration**

### **SSL/TLS Setup**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **Firewall Configuration**

```bash
# Configure UFW
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# For specific services (if not using reverse proxy)
sudo ufw allow 8000/tcp  # SMS Processing API
sudo ufw allow 8501/tcp  # Analytics Dashboard
sudo ufw allow 8001/tcp  # Chat API
```

### **Environment Security**

```bash
# Secure environment files
chmod 600 .env
chown root:root .env

# Use Docker secrets for sensitive data
echo "your-secret-key" | docker secret create jwt_secret -
echo "your-mongodb-password" | docker secret create mongodb_password -
```

### **API Security**

```bash
# Rate limiting (using Nginx)
# Add to nginx.conf:
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;

# API key validation
# Implement in application code or use API gateway
```

---

## 📊 **Monitoring & Logging**

### **Prometheus & Grafana Setup**

```yaml
# monitoring-stack.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  prometheus_data:
  grafana_data:
```

### **Centralized Logging with ELK Stack**

```yaml
# elk-stack.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

### **Application Monitoring**

```python
# Add to your application
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')

# Start metrics server
start_http_server(8080)
```

---

## 💾 **Backup & Recovery**

### **MongoDB Backup**

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backup/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mongodb_backup_$DATE"

# Create backup
mongodump --uri="mongodb://username:password@localhost:27017/pluto_money" --out="$BACKUP_DIR/$BACKUP_NAME"

# Compress backup
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"

# Remove uncompressed backup
rm -rf "$BACKUP_DIR/$BACKUP_NAME"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" s3://your-backup-bucket/mongodb/

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
```

### **Application Data Backup**

```bash
# Backup application data
#!/bin/bash
BACKUP_DIR="/backup/app"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup configuration files
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env docker-compose.yml nginx/

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" */logs/

# Backup models and resources
tar -czf "$BACKUP_DIR/models_$DATE.tar.gz" sms/models/ sms/resources/
```

### **Disaster Recovery Plan**

1. **Database Recovery**
   ```bash
   # Restore from backup
   mongorestore --uri="mongodb://username:password@localhost:27017/pluto_money" /backup/mongodb/latest/
   ```

2. **Application Recovery**
   ```bash
   # Restore configuration
   tar -xzf config_backup.tar.gz
   
   # Restart services
   docker-compose down
   docker-compose up -d
   ```

3. **Monitoring Recovery**
   - Check service health endpoints
   - Verify database connectivity
   - Test API functionality

---

## ⚡ **Performance Optimization**

### **Database Optimization**

```javascript
// MongoDB optimization
db.adminCommand({setParameter: 1, internalQueryPlannerMaxIndexedSolutions: 64})
db.adminCommand({setParameter: 1, internalQueryPlannerEnableIndexIntersection: false})

// Connection pooling
db.adminCommand({setParameter: 1, maxIncomingConnections: 200})
```

### **Application Optimization**

```python
# Connection pooling
from pymongo import MongoClient
client = MongoClient(
    uri,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    waitQueueTimeoutMS=5000
)

# Caching
import redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Async processing
import asyncio
import aiohttp
```

### **Infrastructure Optimization**

```yaml
# Docker resource limits
services:
  sms-processing:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### **CDN Setup**

```bash
# Configure CloudFlare or AWS CloudFront
# Cache static assets
# Enable gzip compression
# Set appropriate cache headers
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Database Connection Issues**

```bash
# Check MongoDB status
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check connection string
echo $MONGODB_URI

# Verify network connectivity
docker-compose exec sms-processing ping mongodb
```

#### **Service Not Starting**

```bash
# Check logs
docker-compose logs sms-processing

# Check resource usage
docker stats

# Verify environment variables
docker-compose exec sms-processing env | grep MONGODB
```

#### **High Memory Usage**

```bash
# Check memory usage
docker stats --no-stream

# Optimize Python applications
# Add to Dockerfile:
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Configure garbage collection
import gc
gc.set_threshold(700, 10, 10)
```

#### **API Timeouts**

```bash
# Increase timeout values
# In docker-compose.yml:
environment:
  - REQUEST_TIMEOUT=60
  - DB_QUERY_TIMEOUT=30
```

### **Performance Issues**

```bash
# Check database performance
db.currentOp()
db.serverStatus()

# Check application performance
# Add monitoring endpoints
# Use profiling tools
```

### **SSL Certificate Issues**

```bash
# Check certificate status
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Renew certificate
certbot renew --dry-run

# Check certificate chain
openssl verify -CAfile ca-bundle.crt nginx/ssl/cert.pem
```

---

## 📞 **Support & Maintenance**

### **Health Checks**

```bash
# Automated health check script
#!/bin/bash
services=("sms-processing:8000" "analytics:8501" "chat-api:8001")

for service in "${services[@]}"; do
    name=${service%%:*}
    port=${service##*:}
    
    if curl -f "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is unhealthy"
        # Send alert
    fi
done
```

### **Maintenance Tasks**

```bash
# Weekly maintenance script
#!/bin/bash

# Update Docker images
docker-compose pull

# Restart services with zero downtime
docker-compose up -d --no-deps sms-processing
docker-compose up -d --no-deps analytics
docker-compose up -d --no-deps chat-api

# Clean up old images
docker image prune -f

# Database maintenance
mongosh --eval "db.runCommand({compact: 'financial_transactions'})"

# Log rotation
find /var/log -name "*.log" -size +100M -delete
```

### **Monitoring Alerts**

```yaml
# alertmanager.yml
groups:
- name: sms-platform
  rules:
  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service {{ $labels.instance }} is down"
      
  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.8
    for: 5m
    labels:
      severity: warning
```

---

## 📈 **Scaling Guide**

### **Horizontal Scaling**

```bash
# Scale services
docker-compose up -d --scale sms-processing=5
docker-compose up -d --scale chat-api=3

# Load balancer configuration
# Use Nginx, HAProxy, or cloud load balancer
```

### **Vertical Scaling**

```yaml
# Increase resource limits
services:
  sms-processing:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
```

### **Database Scaling**

```bash
# MongoDB Atlas auto-scaling
# Configure cluster auto-scaling
# Set up read replicas
# Enable sharding for large datasets
```

---

**🎉 Your SMS Financial Insights Platform is now ready for production!**

For additional support, please refer to:
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Security Best Practices](SECURITY.md)
- [API Documentation](docs/API_GUIDE.md)
- [GitHub Issues](https://github.com/yourusername/smsComplete/issues)

---

*Last Updated: December 2024*
