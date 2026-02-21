# IshemaLink Production Deployment Manual

## Deploying on Clean Ubuntu 22.04 Server

This guide walks through deploying IshemaLink on a fresh Ubuntu server from scratch.

---

## Step 1: Server Preparation

### 1.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget vim
```

### 1.2 Install Docker

```bash
# Add Docker repository
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
```

### 1.3 Install Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Step 2: Clone Repository

```bash
cd /opt
sudo git clone <repository-url> ishemalink
cd ishemalink
sudo chown -R $USER:$USER .
```

---

## Step 3: Environment Configuration

### 3.1 Create Production Environment File

```bash
cp .env.example .env
vim .env
```

### 3.2 Configure Environment Variables

```bash
# Security
DEBUG=False
SECRET_KEY=<generate-with-python-secrets>
FIELD_ENCRYPTION_KEY=<generate-with-cryptography.fernet>

# Domain
ALLOWED_HOSTS=ishemalink.rw,www.ishemalink.rw,api.ishemalink.rw

# Database
DB_NAME=ishemalink_db
DB_USER=ishemalink
DB_PASSWORD=<strong-password>
DB_HOST=pgbouncer
DB_PORT=6432

# Redis
REDIS_URL=redis://redis:6379/0

# SSL
SECURE_SSL_REDIRECT=True

# CORS
CORS_ALLOWED_ORIGINS=https://ishemalink.rw,https://www.ishemalink.rw
```

### 3.3 Generate Secret Keys

```bash
# Generate Django SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(50))"

# Generate Fernet encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Step 4: SSL Certificate Setup

### 4.1 Install Certbot

```bash
sudo apt install -y certbot
```

### 4.2 Obtain SSL Certificate

```bash
# Stop any service on port 80
sudo systemctl stop nginx

# Get certificate
sudo certbot certonly --standalone -d ishemalink.rw -d www.ishemalink.rw

# Certificates will be in /etc/letsencrypt/live/ishemalink.rw/
```

### 4.3 Copy Certificates to Project

```bash
mkdir -p ssl
sudo cp /etc/letsencrypt/live/ishemalink.rw/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/ishemalink.rw/privkey.pem ssl/
sudo chown $USER:$USER ssl/*
```

---

## Step 5: Build and Deploy

### 5.1 Build Docker Images

```bash
docker-compose -f docker-compose.prod.yml build
```

### 5.2 Start Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5.3 Verify Services Running

```bash
docker-compose -f docker-compose.prod.yml ps

# Expected output:
# NAME                COMMAND                  STATUS
# ishemalink-web      "gunicorn ..."           Up
# ishemalink-db       "postgres"               Up (healthy)
# ishemalink-redis    "redis-server"           Up (healthy)
# ishemalink-nginx    "nginx"                  Up
# ishemalink-celery   "celery worker"          Up
```

---

## Step 6: Database Initialization

### 6.1 Run Migrations

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 6.2 Create Superuser

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
# Enter phone: +250788000000
# Enter password: <admin-password>
```

### 6.3 Collect Static Files

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 6.4 Seed Initial Data

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
```

```python
from core.models import ShippingZone
from decimal import Decimal

ShippingZone.objects.create(
    code='ZONE_1',
    name='Kigali',
    base_rate=Decimal('1500'),
    per_kg_rate=Decimal('200'),
    description='Kigali city area'
)

ShippingZone.objects.create(
    code='ZONE_2',
    name='Provinces',
    base_rate=Decimal('3000'),
    per_kg_rate=Decimal('300'),
    description='Other Rwanda provinces'
)

ShippingZone.objects.create(
    code='ZONE_3',
    name='EAC Countries',
    base_rate=Decimal('10000'),
    per_kg_rate=Decimal('500'),
    description='Uganda, Kenya, Tanzania, Burundi'
)
exit()
```

---

## Step 7: Verification

### 7.1 Health Checks

```bash
# Basic health
curl https://ishemalink.rw/api/status/

# Deep health check
curl https://ishemalink.rw/api/health/deep/

# Expected: {"status": "healthy", ...}
```

### 7.2 API Documentation

Visit: https://ishemalink.rw/api/docs/

### 7.3 Admin Dashboard

Visit: https://ishemalink.rw/admin/

---

## Step 8: Monitoring Setup

### 8.1 Access Prometheus

Visit: http://ishemalink.rw:9090

### 8.2 Access Grafana

Visit: http://ishemalink.rw:3000
- Default login: admin / admin
- Change password on first login

### 8.3 Configure Alerts

Edit `prometheus.yml` to add alerting rules.

---

## Step 9: Backup Configuration

### 9.1 Setup Automated Backups

```bash
# Make backup script executable
chmod +x backup_database.sh

# Test backup
./backup_database.sh

# Add to crontab (every 6 hours)
crontab -e
```

Add line:
```
0 */6 * * * /opt/ishemalink/backup_database.sh >> /var/log/ishemalink-backup.log 2>&1
```

### 9.2 Configure Remote Backup Storage

```bash
# Install AWS CLI for S3 backups
sudo apt install -y awscli

# Configure AWS credentials
aws configure
# Enter Access Key, Secret Key, Region: rw-kigali-1
```

---

## Step 10: Firewall Configuration

### 10.1 Setup UFW

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

---

## Step 11: System Service (Optional)

Create systemd service for auto-restart:

```bash
sudo vim /etc/systemd/system/ishemalink.service
```

```ini
[Unit]
Description=IshemaLink Logistics Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ishemalink
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl enable ishemalink
sudo systemctl start ishemalink
```

---

## Step 12: Post-Deployment Verification

### 12.1 Run Test Suite

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py test
```

### 12.2 Load Test

```bash
# Install Locust
pip3 install locust

# Run load test
locust -f tests/locustfile.py --host=https://ishemalink.rw --users=100 --spawn-rate=10
```

### 12.3 Security Scan

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py check --deploy
```

---

## Troubleshooting

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f web

# Application logs
tail -f logs/async_tasks.log
tail -f logs/security.log
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart web
```

### Database Connection Issues

```bash
# Check PgBouncer
docker-compose -f docker-compose.prod.yml exec pgbouncer psql -h localhost -p 6432 -U ishemalink

# Check PostgreSQL
docker-compose -f docker-compose.prod.yml exec db psql -U ishemalink -d ishemalink_db
```

---

## Maintenance

### Update Application

```bash
cd /opt/ishemalink
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### Renew SSL Certificate

```bash
sudo certbot renew
sudo cp /etc/letsencrypt/live/ishemalink.rw/*.pem ssl/
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## Production Checklist

- [ ] Server updated and secured
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] Environment variables configured
- [ ] SSL certificates obtained and configured
- [ ] Services built and running
- [ ] Database migrated and seeded
- [ ] Superuser created
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backups automated
- [ ] Firewall configured
- [ ] Load testing completed
- [ ] Security scan passed

---

## Support

For issues during deployment:
- Check logs: `docker-compose logs`
- Review health: `curl /api/health/deep/`
- Consult: DISASTER_RECOVERY.md
