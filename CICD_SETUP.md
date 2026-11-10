# CI/CD Setup Guide for Digital Ocean Droplet

This guide will walk you through setting up a complete CI/CD pipeline for deploying the SoftMed backend to a Digital Ocean Droplet.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Prepare Your Digital Ocean Droplet](#step-1-prepare-your-digital-ocean-droplet)
- [Step 2: Set Up GitHub Repository](#step-2-set-up-github-repository)
- [Step 3: Configure GitHub Secrets](#step-3-configure-github-secrets)
- [Step 4: Set Up SSH Keys](#step-4-set-up-ssh-keys)
- [Step 5: Create Deployment Scripts](#step-5-create-deployment-scripts)
- [Step 6: Set Up Systemd Service](#step-6-set-up-systemd-service)
- [Step 7: Configure Nginx Reverse Proxy](#step-7-configure-nginx-reverse-proxy)
- [Step 8: Set Up SSL with Let's Encrypt](#step-8-set-up-ssl-with-lets-encrypt)
- [Step 9: Test the Deployment](#step-9-test-the-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- A Digital Ocean Droplet (Ubuntu 22.04 LTS or later recommended)
- A GitHub repository for your backend code
- Domain name pointing to your Droplet (optional but recommended)
- SSH access to your Droplet
- Basic knowledge of Linux commands

---

## Step 1: Prepare Your Digital Ocean Droplet

### 1.1 Create a Droplet

1. Log in to Digital Ocean
2. Create a new Droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: At least 1GB RAM (2GB+ recommended for production)
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH keys (recommended) or password
   - **Hostname**: `softmed-backend` (or your preference)

### 1.2 Initial Server Setup

SSH into your Droplet:

```bash
ssh root@your-droplet-ip
```

Update the system:

```bash
apt update && apt upgrade -y
```

### 1.3 Create a Deployment User

Create a dedicated user for deployments (more secure than using root):

```bash
# Create user
adduser deploy

# Add to sudo group
usermod -aG sudo deploy

# Configure passwordless sudo for deploy user (REQUIRED for CI/CD)
# This allows the deploy user to run sudo commands without a password
echo "deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/deploy
sudo chmod 0440 /etc/sudoers.d/deploy

# Verify passwordless sudo works
su - deploy
sudo whoami  # Should output "root" without asking for password

# Switch back to root if needed
exit
```

**Important**: Passwordless sudo is required because GitHub Actions runs commands non-interactively and cannot enter passwords.

### 1.4 Install Required Software

```bash
# Update package list
sudo apt update

# Install Python 3.11+ and pip
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Install Git
sudo apt install -y git

# Install other utilities
sudo apt install -y curl wget build-essential libpq-dev

# Install Certbot for SSL
sudo apt install -y certbot python3-certbot-nginx

# Install Supervisor for process management (optional alternative to systemd)
sudo apt install -y supervisor
```

### 1.5 Set Up PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE softmed_db;
CREATE USER softmed_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE softmed_user SET client_encoding TO 'utf8';
ALTER ROLE softmed_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE softmed_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE softmed_db TO softmed_user;

# Connect to the database to grant schema permissions
\c softmed_db

# Grant schema permissions (required for Alembic migrations)
GRANT ALL ON SCHEMA public TO softmed_user;
GRANT CREATE ON SCHEMA public TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO softmed_user;

\q
```

### 1.6 Configure PostgreSQL for Remote Connections (if needed)

Edit PostgreSQL config:

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Find and uncomment/modify:

```
listen_addresses = 'localhost'
```

Edit pg_hba.conf:

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Add:

```
host    softmed_db    softmed_user    127.0.0.1/32    md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 1.7 Configure Redis

Edit Redis config:

```bash
sudo nano /etc/redis/redis.conf
```

Find and set:

```
bind 127.0.0.1
protected-mode yes
```

Restart Redis:

```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### 1.8 Create Application Directory

```bash
# Create directory structure
sudo mkdir -p /var/www/softmed-backend
sudo chown deploy:deploy /var/www/softmed-backend

# Create uploads directory
sudo mkdir -p /var/www/softmed-backend/uploads/documents
sudo mkdir -p /var/www/softmed-backend/uploads/photos
sudo chown -R deploy:deploy /var/www/softmed-backend/uploads
```

---

## Step 2: Set Up GitHub Repository

Ensure your backend code is in a GitHub repository. If not:

```bash
cd /path/to/backend
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/softmed-backend.git
git push -u origin main
```

---

## Step 3: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

### Required Secrets:

1. **`DEPLOY_HOST`**: Your Droplet IP address
   - Example: `123.456.789.0`

2. **`DEPLOY_USER`**: SSH user for deployment
   - Example: `softmed-deploy` (or your deployment username)

3. **`DEPLOY_SSH_KEY`**: Private SSH key for deployment
   - Generate key pair (see Step 4)
   - Paste the **private** key here

4. **`DEPLOY_SSH_PUBLIC_KEY`**: Public SSH key (for initial setup)
   - Paste the **public** key here

5. **`PRODUCTION_DATABASE_URL`**: Production database connection string
   - Example: `postgresql+psycopg2://softmed_user:your_secure_password_here@localhost:5432/softmed_db`

6. **`PRODUCTION_SECRET_KEY`**: Production secret key
   - Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Optional Secrets (for additional features):

7. **`PRODUCTION_CORS_ORIGINS`**: Comma-separated frontend URLs
   - Example: `https://yourdomain.com,https://admin.yourdomain.com`

8. **`SMTP_SERVER`**: Email server (if using email features)

9. **`SMTP_USERNAME`**: Email username

10. **`SMTP_PASSWORD`**: Email password

11. **`GOOGLE_CLIENT_ID`**: Google OAuth client ID

12. **`GOOGLE_CLIENT_SECRET`**: Google OAuth client secret

13. **`PAGARME_SECRET_KEY`**: Pagar.me secret key

14. **`MEMED_API_KEY`**: Memed API key

---

## Step 4: Set Up SSH Keys

**Why generate SSH keys on the server?** 
- More secure: The private key never leaves the server (except going to GitHub Secrets)
- Better practice: Keys are generated in the environment where they'll be used
- Simpler: No need to transfer keys between machines

### 4.1 Generate SSH Key Pair (on the Droplet - RECOMMENDED)

SSH into your Droplet:

```bash
ssh root@your-droplet-ip
# or
ssh deploy@your-droplet-ip
```

Generate the key pair on the server:

```bash
# Switch to deploy user (if not already)
su - deploy

# Generate SSH key pair
ssh-keygen -t ed25519 -C "deploy@softmed-backend" -f ~/.ssh/deploy_key -N ""

# This creates:
# ~/.ssh/deploy_key (private key)
# ~/.ssh/deploy_key.pub (public key)
```

### 4.2 Add Public Key to Authorized Keys

```bash
# Add public key to authorized_keys
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 4.3 Copy Private Key to GitHub Secrets

1. Display the private key:
   ```bash
   cat ~/.ssh/deploy_key
   ```
2. Copy the **entire** output (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)
3. Go to GitHub → Repository → Settings → Secrets → Actions → New repository secret
4. Name: `DEPLOY_SSH_KEY`
5. Value: Paste the private key
6. Click "Add secret"

**Important**: After copying to GitHub Secrets, you can optionally remove the private key from the server for extra security (GitHub Actions will use the one from Secrets):

```bash
# Optional: Remove private key from server (it's now in GitHub Secrets)
rm ~/.ssh/deploy_key
```

### 4.4 Test SSH Connection (from GitHub Actions)

The GitHub Actions workflow will test the connection automatically. You can also test manually:

```bash
# From your local machine, test that GitHub Actions can connect
# (This simulates what GitHub Actions will do)
ssh -i ~/.ssh/deploy_key deploy@your-droplet-ip "echo 'Connection successful'"
```

---

### Alternative: Generate on Local Machine (if you prefer)

If you prefer to generate keys on your local machine (less secure but simpler for initial setup):

```bash
# On your local machine
ssh-keygen -t ed25519 -C "deploy@softmed-backend" -f ~/.ssh/softmed_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/softmed_deploy.pub deploy@your-droplet-ip

# Add private key to GitHub Secrets
cat ~/.ssh/softmed_deploy
# Copy output to GitHub Secrets → DEPLOY_SSH_KEY
```

**Note**: This approach is acceptable but less secure because the private key exists on your local machine. The server-based approach above is recommended for production.

---

## Step 5: Create Deployment Scripts

The GitHub Actions workflow (`.github/workflows/deploy.yml`) will handle the deployment automatically. See the workflow file for details.

---

## Step 6: Set Up Systemd Service

Create a systemd service file for the FastAPI application:

```bash
sudo nano /etc/systemd/system/softmed-backend.service
```

Paste the following:

```ini
[Unit]
Description=SoftMed Backend API
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/var/www/softmed-backend
Environment="PATH=/var/www/softmed-backend/venv/bin"
ExecStart=/var/www/softmed-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Reload systemd and enable service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable softmed-backend
```

**Note**: The service will be started by the deployment script.

---

## Step 7: Configure Nginx Reverse Proxy

Create Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/softmed-backend
```

Paste the following (replace `your-domain.com` with your actual domain):

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/softmed-backend /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## Step 8: Set Up SSL with Let's Encrypt

After configuring Nginx and DNS:

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts. Certbot will automatically:
- Obtain SSL certificates
- Update Nginx configuration
- Set up auto-renewal

---

## Step 9: Test the Deployment

### 9.1 Manual Test

After pushing to GitHub, the workflow should automatically deploy. Check:

```bash
# Check service status
sudo systemctl status softmed-backend

# Check logs
sudo journalctl -u softmed-backend -f

# Test API
curl http://localhost:8000/docs
```

### 9.2 Verify Deployment

1. Check GitHub Actions: Repository → Actions tab
2. Check API: Visit `https://your-domain.com/docs`
3. Test endpoints: Use the Swagger UI to test API calls

---

## Troubleshooting

### Sudo Password Required Error

**Error**: `sudo: a terminal is required to read the password`

**Solution**: Configure passwordless sudo for the deploy user:

```bash
# SSH into your Droplet as root
ssh root@your-droplet-ip

# Add passwordless sudo configuration
echo "deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/deploy
sudo chmod 0440 /etc/sudoers.d/deploy

# Test it works
su - deploy
sudo whoami  # Should output "root" without password
```

### Service Won't Start

```bash
# Check logs
sudo journalctl -u softmed-backend -n 50

# Check if port is in use
sudo netstat -tlnp | grep 8000

# Restart service
sudo systemctl restart softmed-backend
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
sudo -u postgres psql -d softmed_db -U softmed_user

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Nginx Issues

```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Deployment Script Issues

Check GitHub Actions logs:
- Repository → Actions → Latest workflow run → View logs

### Permission Issues

```bash
# Fix ownership
sudo chown -R deploy:deploy /var/www/softmed-backend
```

### Environment Variables

Ensure all environment variables are set in `/var/www/softmed-backend/.env`:

```bash
cd /var/www/softmed-backend
nano .env
```

---

## Security Best Practices

1. **Firewall**: Set up UFW firewall
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Fail2ban**: Install fail2ban for brute-force protection
   ```bash
   sudo apt install fail2ban
   ```

3. **Regular Updates**: Keep system updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. **Backups**: Set up automated database backups
   ```bash
   # Add to crontab
   0 2 * * * pg_dump -U softmed_user softmed_db > /var/backups/softmed_db_$(date +\%Y\%m\%d).sql
   ```

5. **Monitor Logs**: Regularly check application and system logs

---

## Next Steps

- Set up monitoring (e.g., Sentry, DataDog)
- Configure automated backups
- Set up staging environment
- Add health check endpoints
- Configure log aggregation
- Set up CI/CD for staging deployments

---

## Support

If you encounter issues, check:
1. GitHub Actions logs
2. System logs: `sudo journalctl -u softmed-backend`
3. Nginx logs: `/var/log/nginx/error.log`
4. Application logs in `/var/www/softmed-backend/logs` (if configured)

