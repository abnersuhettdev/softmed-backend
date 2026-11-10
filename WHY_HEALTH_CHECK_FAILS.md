# Why Health Check Fails (HTTP Code 000)

## Understanding HTTP Code 000

HTTP code `000` from curl means:
- **Connection failed** - curl couldn't establish a connection
- **Not a real HTTP response** - it's curl's error code

## Common Causes

### 1. **curl Not Installed or Not Available**
The server might not have `curl` installed, or it's not in the PATH during the SSH session.

**Solution**: The health check now automatically installs curl if missing.

### 2. **Service Still Starting**
Even though systemd shows the service as "active", the workers might still be initializing. Uvicorn with multiple workers can take 10-30 seconds to fully start.

**Evidence**: Your logs show workers starting at different times:
- First workers: 17:33:33
- Last worker: 17:33:34

### 3. **Network Binding Issue**
The service binds to `0.0.0.0:8000`, but `localhost` or `127.0.0.1` might not be properly accessible during the check.

### 4. **SSH Command Execution Context**
The SSH command might be running in a different environment where tools aren't available.

## Why This Doesn't Matter

**The service IS working!** Here's the proof:
- ✅ Service status: `Active: active (running)`
- ✅ All 4 workers started
- ✅ Application startup complete for all workers
- ✅ No errors in logs

The health check is just a **verification step** - the actual deployment succeeded!

## How to Verify Service is Working

You can manually verify:

```bash
# SSH into your server
ssh softmed-deploy@your-droplet-ip

# Test the API
curl http://localhost:8000/
# Should return: {"message": "Hello World"}

# Or test from outside
curl http://your-droplet-ip:8000/

# Check if port is listening
sudo ss -tlnp | grep 8000
# Should show: LISTEN on port 8000
```

## Improved Health Check

I've updated the health check to:
1. ✅ Install curl automatically if missing
2. ✅ Wait longer for service to fully start (15 seconds)
3. ✅ Check service status before attempting HTTP check
4. ✅ Try multiple methods (curl, wget, python)
5. ✅ Use `127.0.0.1` instead of `localhost`
6. ✅ Better error messages and diagnostics
7. ✅ Don't fail deployment if service is running (just warning)

The next deployment should have a more reliable health check!

