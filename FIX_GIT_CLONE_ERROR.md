# Fix: Git Clone Authentication Error

## Problem

The deployment was failing with this error:
```
fatal: could not read Username for 'https://github.com': No such device or address
```

This occurred because the deployment script was trying to clone the repository from GitHub using HTTPS on the server, which requires authentication credentials that aren't available in a non-interactive environment.

## Solution

Instead of cloning the repository on the server, the workflow now:

1. **Checks out the code** on the GitHub Actions runner (where authentication is automatic)
2. **Transfers the code** to the server using `rsync` (which uses SSH, already configured)
3. **Sets up the environment** on the server

This approach:
- ✅ Avoids GitHub authentication issues
- ✅ Is more efficient (only transfers what's needed)
- ✅ Uses existing SSH infrastructure
- ✅ Excludes unnecessary files (`.git`, `venv`, cache files, etc.)

## Changes Made

1. **Added a new step** "Transfer code to server" that uses `rsync` to copy code from GitHub Actions runner to the server
2. **Removed git clone/fetch logic** from the deployment script
3. **Updated deployment script** to assume code is already transferred

## Workflow Steps (Current Order)

1. Checkout code (GitHub Actions runner)
2. Set up SSH keys
3. Create `.env` file content
4. Create deployment script
5. **Transfer code to server** (using rsync) ← NEW
6. Run deployment script (environment setup)
7. Notify deployment status

## What to Do Next

1. Make sure you've configured passwordless sudo (see `FIX_SUDO_PASSWORD.md`)
2. Ensure GitHub Secret `DEPLOY_USER` is set to: `softmed-deploy`
3. Push your code or manually trigger the workflow
4. The deployment should now succeed!

## Technical Details

The `rsync` command excludes:
- `.git` directory
- `venv` directory (created fresh on server)
- `__pycache__` and `*.pyc` files
- `.env` file (created separately with secrets)
- Cache directories (`.pytest_cache`, `.mypy_cache`)
- `node_modules` (if any)

This ensures only necessary source code and configuration files are transferred.

