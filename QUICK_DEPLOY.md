# Quick Deployment Guide

This is a condensed version of the full CI/CD setup guide. For detailed instructions, see [CICD_SETUP.md](CICD_SETUP.md).

## Prerequisites Checklist

- ✅ Digital Ocean Droplet (Ubuntu 22.04+)
- ✅ Domain name (optional but recommended)
- ✅ GitHub repository
- ✅ SSH access to Droplet

## Quick Start (5 Steps)

### 1. Initial Server Setup (One-time)

SSH into your Droplet and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib redis-server nginx git certbot python3-certbot-nginx

# Create deployment user
sudo adduser softmed-deploy
sudo usermod -aG sudo softmed-deploy

# Configure passwordless sudo (REQUIRED for CI/CD)
echo "softmed-deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/softmed-deploy
sudo chmod 0440 /etc/sudoers.d/softmed-deploy

# Set up PostgreSQL
sudo -u postgres psql
# Then in psql:
CREATE DATABASE softmed_db;
CREATE USER softmed_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE softmed_db TO softmed_user;
\c softmed_db
GRANT ALL ON SCHEMA public TO softmed_user;
GRANT CREATE ON SCHEMA public TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO softmed_user;
\q

# Create app directory
sudo mkdir -p /var/www/softmed-backend
sudo chown softmed-deploy:softmed-deploy /var/www/softmed-backend
```

### 2. Set Up SSH Keys

**Recommended: Generate on the server** (more secure):

```bash
# SSH into your Droplet
ssh deploy@your-droplet-ip

# Generate key pair on the server
ssh-keygen -t ed25519 -C "deploy@softmed" -f ~/.ssh/deploy_key -N ""

# Add public key to authorized_keys
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Display private key (copy this to GitHub Secrets)
cat ~/.ssh/deploy_key
```

**Alternative: Generate on local machine** (simpler but less secure):

```bash
# On your local machine
ssh-keygen -t ed25519 -C "deploy@softmed" -f ~/.ssh/softmed_deploy
ssh-copy-id -i ~/.ssh/softmed_deploy.pub deploy@your-droplet-ip
cat ~/.ssh/softmed_deploy  # Copy to GitHub Secrets
```

### 3. Configure GitHub Secrets

Go to: **GitHub Repository → Settings → Secrets → Actions → New repository secret**

Add these secrets:

| Secret Name | Value |
|------------|-------|
| `DEPLOY_HOST` | Your Droplet IP address |
| `DEPLOY_USER` | `softmed-deploy` |
| `DEPLOY_SSH_KEY` | Contents of `~/.ssh/softmed_deploy` (private key) |
| `PRODUCTION_DATABASE_URL` | `postgresql+psycopg2://softmed_user:password@localhost:5432/softmed_db` |
| `PRODUCTION_SECRET_KEY` | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `PRODUCTION_CORS_ORIGINS` | Your frontend URLs (comma-separated) |

### 4. Set Up Systemd Service

On the Droplet:

```bash
sudo nano /etc/systemd/system/softmed-backend.service
```

Paste the contents from `scripts/systemd/softmed-backend.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable softmed-backend
```

### 5. Configure Nginx

```bash
# Copy nginx config
sudo cp scripts/nginx/softmed-backend.conf /etc/nginx/sites-available/softmed-backend

# Edit domain name
sudo nano /etc/nginx/sites-available/softmed-backend
# Replace 'your-domain.com' with your actual domain

# Enable site
sudo ln -s /etc/nginx/sites-available/softmed-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Set Up SSL (Optional but Recommended)

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Deploy!

Once everything is set up:

1. **Push to GitHub**: Your code will automatically deploy when you push to `main` branch
2. **Manual Trigger**: Go to GitHub Actions → Deploy workflow → Run workflow
3. **Check Status**: Monitor deployment in GitHub Actions tab

## Manual Deployment

If you prefer manual deployment:

```bash
# Make script executable (on Linux/Mac)
chmod +x deploy.sh

# Run deployment
./deploy.sh your-droplet-ip softmed-deploy
```

## Verify Deployment

```bash
# Check service status
ssh deploy@your-droplet-ip "sudo systemctl status softmed-backend"

# Test API
curl http://your-droplet-ip:8000/docs
# or
curl https://your-domain.com/docs
```

## Common Commands

```bash
# View logs
ssh deploy@your-droplet-ip "sudo journalctl -u softmed-backend -f"

# Restart service
ssh deploy@your-droplet-ip "sudo systemctl restart softmed-backend"

# Check service status
ssh deploy@your-droplet-ip "sudo systemctl status softmed-backend"

# View Nginx logs
ssh deploy@your-droplet-ip "sudo tail -f /var/log/nginx/error.log"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Service won't start | Check logs: `sudo journalctl -u softmed-backend -n 50` |
| 502 Bad Gateway | Check if service is running: `sudo systemctl status softmed-backend` |
| Database connection error | Verify `.env` file has correct `DATABASE_URL` |
| Permission denied | Fix ownership: `sudo chown -R deploy:deploy /var/www/softmed-backend` |

## Next Steps

- ✅ Complete deployment checklist: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- 📖 Full guide: [CICD_SETUP.md](CICD_SETUP.md)
- 🔒 Set up firewall: `sudo ufw allow 22,80,443/tcp && sudo ufw enable`
- 💾 Set up automated backups

---

**Need help?** Check the detailed guide: [CICD_SETUP.md](CICD_SETUP.md)

