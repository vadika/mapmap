#!/bin/bash

# Generate cloud-init.yaml with current user's SSH key
# This script automatically includes your SSH public key

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔑 Generating cloud-init.yaml with your SSH key...${NC}"

# Find SSH public key
SSH_KEY=""
if [ -f ~/.ssh/id_ed25519.pub ]; then
    SSH_KEY=$(cat ~/.ssh/id_ed25519.pub)
    echo -e "${GREEN}✓ Found ed25519 key${NC}"
elif [ -f ~/.ssh/id_rsa.pub ]; then
    SSH_KEY=$(cat ~/.ssh/id_rsa.pub)
    echo -e "${GREEN}✓ Found RSA key${NC}"
else
    echo -e "${YELLOW}⚠️  No SSH public key found in ~/.ssh/${NC}"
    echo "Please generate one with: ssh-keygen -t ed25519"
    exit 1
fi

# Check if template exists
if [ ! -f cloud-init.template.yaml ]; then
    echo -e "${YELLOW}Creating cloud-init template...${NC}"
    cp cloud-init.yaml cloud-init.template.yaml
fi

# Generate cloud-init.yaml from template
cp cloud-init.template.yaml cloud-init.yaml

# Replace SSH key placeholder with actual key
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|ssh-ed25519.*|$SSH_KEY|" cloud-init.yaml
else
    # Linux
    sed -i "s|ssh-ed25519.*|$SSH_KEY|" cloud-init.yaml
fi

echo -e "${GREEN}✅ Generated cloud-init.yaml with your SSH key${NC}"
echo ""
echo "Your SSH key fingerprint:"
ssh-keygen -lf ~/.ssh/id_ed25519.pub 2>/dev/null || ssh-keygen -lf ~/.ssh/id_rsa.pub

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review cloud-init.yaml"
echo "2. Upload to your VPS provider when creating a new server"
echo "3. Update the domain settings in the configuration"
echo ""
echo -e "${YELLOW}Security reminder:${NC}"
echo "- The cloud-init.yaml now contains your public SSH key"
echo "- This is safe to share and commit to git"
echo "- Never share your private key (~/.ssh/id_ed25519 or ~/.ssh/id_rsa)"