#!/bin/bash
# Manual deployment script for Digital Ocean Droplet
# Usage: ./deploy.sh [server-ip] [user]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_HOST="${1:-$DEPLOY_HOST}"
DEPLOY_USER="${2:-${DEPLOY_USER:-deploy}}"
APP_DIR="/var/www/softmed-backend"
BACKUP_DIR="/var/backups/softmed-backend"

# Check if host is provided
if [ -z "$DEPLOY_HOST" ]; then
    echo -e "${RED}Error: Deployment host not specified${NC}"
    echo "Usage: $0 <server-ip> [user]"
    echo "   Or set DEPLOY_HOST environment variable"
    exit 1
fi

echo -e "${GREEN}🚀 Starting deployment to $DEPLOY_USER@$DEPLOY_HOST${NC}"

# Check SSH connection
echo -e "${YELLOW}📡 Checking SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 "$DEPLOY_USER@$DEPLOY_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${RED}❌ Failed to connect to $DEPLOY_USER@$DEPLOY_HOST${NC}"
    echo "Please check:"
    echo "  1. Server is accessible"
    echo "  2. SSH key is added to server"
    echo "  3. User has proper permissions"
    exit 1
fi

# Create backup
echo -e "${YELLOW}📦 Creating backup...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "sudo mkdir -p $BACKUP_DIR && sudo systemctl stop softmed-backend 2>/dev/null || true"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "sudo cp -r $APP_DIR $BACKUP_DIR/backup_\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

# Clone/update repository
echo -e "${YELLOW}📥 Updating code...${NC}"
REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
if [ -z "$REPO_URL" ]; then
    echo -e "${RED}❌ No git remote found. Please configure git remote.${NC}"
    exit 1
fi

ssh "$DEPLOY_USER@$DEPLOY_HOST" << ENDSSH
    set -e
    if [ -d "$APP_DIR/.git" ]; then
        cd $APP_DIR
        echo "Pulling latest changes..."
        git fetch origin
        git reset --hard origin/main
    else
        echo "Cloning repository..."
        sudo mkdir -p $APP_DIR
        sudo chown $DEPLOY_USER:$DEPLOY_USER $APP_DIR
        git clone $REPO_URL $APP_DIR
    fi
ENDSSH

# Set up Python environment
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" << 'ENDSSH'
    set -e
    cd $APP_DIR
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
ENDSSH

# Set permissions
echo -e "${YELLOW}🔒 Setting permissions...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" "sudo chown -R $DEPLOY_USER:$DEPLOY_USER $APP_DIR && sudo chmod 600 $APP_DIR/.env 2>/dev/null || true"

# Run migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" << 'ENDSSH'
    set -e
    cd $APP_DIR
    source venv/bin/activate
    alembic upgrade head
ENDSSH

# Restart service
echo -e "${YELLOW}🔄 Restarting service...${NC}"
ssh "$DEPLOY_USER@$DEPLOY_HOST" << 'ENDSSH'
    sudo systemctl daemon-reload
    sudo systemctl restart softmed-backend
    sleep 3
    sudo systemctl status softmed-backend --no-pager | head -n 10
ENDSSH

# Health check
echo -e "${YELLOW}🏥 Running health check...${NC}"
sleep 5
HTTP_CODE=$(ssh "$DEPLOY_USER@$DEPLOY_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo -e "${GREEN}✅ Health check passed!${NC}"
    echo ""
    echo "🌐 API Documentation: http://$DEPLOY_HOST/docs"
else
    echo -e "${RED}❌ Health check failed! HTTP Code: $HTTP_CODE${NC}"
    echo "Check logs with: ssh $DEPLOY_USER@$DEPLOY_HOST 'sudo journalctl -u softmed-backend -n 50'"
    exit 1
fi

