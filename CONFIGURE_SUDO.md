# Configure Passwordless Sudo for softmed-deploy User

## Quick Fix for Deployment Failure

Your deployment is failing because the `softmed-deploy` user needs passwordless sudo access.

## Steps to Fix

SSH into your Digital Ocean Droplet and run:

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

## Verify Configuration

```bash
# Switch to softmed-deploy user
su - softmed-deploy

# Test sudo without password
sudo mkdir -p /tmp/test
sudo rm -rf /tmp/test

# If both commands work without asking for password, configuration is correct!
```

## Important Notes

- **Username**: Use `softmed-deploy` (not `deploy`)
- **SSH Authentication**: We use SSH keys, not passwords, for secure authentication
- **Passwordless sudo**: Required for automated deployments via GitHub Actions

## After Configuration

1. Update GitHub Secret `DEPLOY_USER` to: `softmed-deploy`
2. Re-run the deployment workflow

