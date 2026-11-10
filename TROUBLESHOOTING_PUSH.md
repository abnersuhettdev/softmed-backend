# Troubleshooting Git Push Issues

## Common Causes of "Connection was reset" Error

### 1. Authentication Issues (Most Common)

GitHub no longer accepts passwords for HTTPS. You need to use either:
- **Personal Access Token (PAT)** - Recommended
- **SSH keys**

### Solution A: Use Personal Access Token (HTTPS)

1. **Create a Personal Access Token on GitHub:**
   - Go to: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Name it (e.g., "SoftMed Backend")
   - Select scopes: Check `repo` (full control of private repositories)
   - Click "Generate token"
   - **Copy the token immediately** (you won't see it again!)

2. **Use the token when pushing:**
   ```powershell
   git push https://<YOUR_TOKEN>@github.com/gagan-d-g/softmed-backend.git master
   ```

3. **Or configure Git Credential Manager:**
   ```powershell
   git config --global credential.helper manager-core
   ```
   Then when you push, enter your GitHub username and use the token as the password.

### Solution B: Switch to SSH (More Secure)

1. **Check if you have SSH keys:**
   ```powershell
   ls ~/.ssh
   ```

2. **Generate SSH key if needed:**
   ```powershell
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

3. **Add SSH key to GitHub:**
   - Copy public key: `cat ~/.ssh/id_ed25519.pub`
   - Go to: GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste the public key

4. **Change remote URL to SSH:**
   ```powershell
   git remote set-url origin git@github.com:gagan-d-g/softmed-backend.git
   ```

5. **Test SSH connection:**
   ```powershell
   ssh -T git@github.com
   ```

6. **Push again:**
   ```powershell
   git push
   ```

### 2. Increase Git Buffer Size

Large files or commits can cause connection timeouts:

```powershell
git config --global http.postBuffer 524288000
git config --global http.maxRequestBuffer 100M
git config --global core.compression 0
```

### 3. Use SSH Instead of HTTPS

```powershell
# Change remote URL
git remote set-url origin git@github.com:gagan-d-g/softmed-backend.git

# Verify
git remote -v

# Push
git push
```

### 4. Check Proxy Settings

If you're behind a corporate firewall/proxy:

```powershell
# Check if proxy is configured
git config --global --get http.proxy
git config --global --get https.proxy

# If proxy is set incorrectly, unset it:
git config --global --unset http.proxy
git config --global --unset https.proxy

# Or set correct proxy:
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy http://proxy.example.com:8080
```

### 5. Use Git Credential Manager

Windows Credential Manager can cache credentials:

```powershell
# Install Git Credential Manager (usually comes with Git for Windows)
# Or download from: https://github.com/GitCredentialManager/git-credential-manager

# Configure it
git config --global credential.helper manager-core

# Try pushing again - it will prompt for credentials
git push
```

### 6. Try Pushing with Verbose Output

To see more details about what's failing:

```powershell
git push -v
# or
GIT_CURL_VERBOSE=1 GIT_TRACE=1 git push
```

### 7. Test Connection Directly

```powershell
# Test HTTPS connection
curl -I https://github.com/gagan-d-g/softmed-backend.git

# Test SSH connection (if using SSH)
ssh -T git@github.com
```

### 8. Check Firewall/Antivirus

Sometimes firewalls or antivirus software can block Git connections:
- Temporarily disable firewall/antivirus
- Add Git to firewall exceptions
- Add GitHub to firewall whitelist

### 9. Update Git

Outdated Git versions can have connection issues:

```powershell
# Check Git version
git --version

# Update Git (download from https://git-scm.com/download/win)
```

### 10. Alternative: Use GitHub CLI

If all else fails, you can use GitHub CLI:

```powershell
# Install GitHub CLI
winget install GitHub.cli

# Authenticate
gh auth login

# Push using GitHub CLI (if needed)
```

## Quick Fix Summary

**Most likely solution for HTTPS:**

1. Generate Personal Access Token on GitHub
2. Configure credential helper:
   ```powershell
   git config --global credential.helper manager-core
   ```
3. Push and enter username + token when prompted

**Or switch to SSH (recommended):**

```powershell
git remote set-url origin git@github.com:gagan-d-g/softmed-backend.git
git push
```

