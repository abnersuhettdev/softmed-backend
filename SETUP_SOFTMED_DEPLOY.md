# Setup Instructions for softmed-deploy User

## Quick Setup Commands

Run these commands on your Digital Ocean Droplet:

### 1. Configure Passwordless Sudo (REQUIRED for CI/CD)

```bash
# SSH into your Droplet as root
ssh root@your-droplet-ip

# Configure passwordless sudo for softmed-deploy user
echo "softmed-deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/softmed-deploy
sudo chmod 0440 /etc/sudoers.d/softmed-deploy

# Verify it works
su - softmed-deploy
sudo whoami  # Should output "root" without asking for password
exit
```

### 2. Update GitHub Secret

Go to: **GitHub Repository → Settings → Secrets → Actions**

Update the `DEPLOY_USER` secret:
- **Name**: `DEPLOY_USER`
- **Value**: `softmed-deploy`

### 3. Verify Systemd Service Configuration

Make sure the systemd service uses the correct user:

```bash
# On your Droplet, check/update the service file
sudo nano /etc/systemd/system/softmed-backend.service
```

Ensure it has:
```ini
User=softmed-deploy
Group=softmed-deploy
```

### 4. Verify Directory Ownership

```bash
# Set correct ownership
sudo chown -R softmed-deploy:softmed-deploy /var/www/softmed-backend
```

### 5. Test Deployment

After configuring passwordless sudo, re-run the GitHub Actions workflow or push your code again.

## Important Notes

- **Username**: `softmed-deploy` (not `deploy`)
- **Authentication**: SSH keys are used (not the password "qwert")
- **Passwordless Sudo**: Required because GitHub Actions runs non-interactively
- **Password "qwert"**: This is just for the user account; SSH keys are used for deployment

