# Fix: Sudo Password Required Error

## Problem

Your deployment is failing with this error:
```
sudo: a terminal is required to read the password
sudo: a password is required
```

## Root Cause

The `softmed-deploy` user needs passwordless sudo access because GitHub Actions runs commands non-interactively and cannot enter passwords.

## Quick Fix

SSH into your Digital Ocean Droplet and run these commands:

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

After running the commands above, test that passwordless sudo works:

```bash
# Switch to deploy user
su - deploy

# Test sudo without password
sudo mkdir -p /tmp/test
sudo rm -rf /tmp/test

# If both commands work without asking for password, you're good!
```

## Security Note

Passwordless sudo is necessary for automated deployments. The `softmed-deploy` user should:
- Only be used for deployment purposes
- Have restricted file permissions on sensitive directories
- Not be used for general system administration

## After Fixing

Once you've configured passwordless sudo:
1. Push your code again (or trigger the workflow manually)
2. The deployment should now succeed

