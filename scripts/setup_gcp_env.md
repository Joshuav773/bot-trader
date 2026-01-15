# Setting Up Environment Variables in Google Cloud

This guide shows how to set up environment variables for the bot-trader on Google Cloud Platform.

## Option 1: Using Google Cloud Secrets Manager (Recommended)

### 1. Create Secret for All Variables

Create a secrets file locally:
```bash
cat > secrets.json << 'EOF'
{
  "SCHWAB_APP_KEY": "your-schwab-app-key",
  "SCHWAB_APP_SECRET": "your-schwab-app-secret",
  "SCHWAB_CALLBACK_URL": "https://your-domain.com",
  "DATABASE_URL": "postgresql://user:password@host/database",
  "GMAIL_USER": "your-email@gmail.com",
  "GMAIL_PASSWORD": "your-app-password"
}
EOF
```

Create the secret in GCP:
```bash
gcloud secrets create bot-trader-secrets --data-file=secrets.json
```

Grant access:
```bash
gcloud secrets add-iam-policy-binding bot-trader-secrets \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. Use Secret in Compute Engine

In your VM startup script or systemd service:
```bash
# Install secret manager
gcloud secrets versions access latest --secret="bot-trader-secrets" > /tmp/secrets.json

# Export variables (or load into .env file)
export SCHWAB_APP_KEY=$(jq -r '.SCHWAB_APP_KEY' /tmp/secrets.json)
export SCHWAB_APP_SECRET=$(jq -r '.SCHWAB_APP_SECRET' /tmp/secrets.json)
# ... etc
```

## Option 2: Direct .env File on VM

### SSH into your VM:
```bash
gcloud compute ssh YOUR_VM_NAME --zone=YOUR_ZONE
```

### Create .env file:
```bash
cd ~/bot-trader
nano .env
```

### Add these variables:
```bash
SCHWAB_APP_KEY=your-schwab-app-key
SCHWAB_APP_SECRET=your-schwab-app-secret
SCHWAB_CALLBACK_URL=https://your-domain.com
DATABASE_URL=postgresql://user:password@host/database
GMAIL_USER=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
```

Save and exit (Ctrl+X, Y, Enter)

### Secure the file:
```bash
chmod 600 .env
```

## Option 3: Systemd Environment File

### Create environment file:
```bash
sudo nano /etc/systemd/system/bot-trader.env
```

Add:
```bash
SCHWAB_APP_KEY=your-schwab-app-key
SCHWAB_APP_SECRET=your-schwab-app-secret
SCHWAB_CALLBACK_URL=https://your-domain.com
DATABASE_URL=postgresql://user:password@host/database
GMAIL_USER=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
```

### Update systemd service to use it:
```ini
[Service]
EnvironmentFile=/etc/systemd/system/bot-trader.env
```

## Option 4: Metadata Service (for Compute Engine)

Set metadata:
```bash
gcloud compute instances add-metadata YOUR_VM_NAME \
  --metadata SCHWAB_APP_KEY=your-key,SCHWAB_APP_SECRET=your-secret \
  --zone=YOUR_ZONE
```

Access in code:
```python
import requests
metadata_server = "http://metadata/computeMetadata/v1/instance/attributes/"
headers = {"Metadata-Flavor": "Google"}
schwab_key = requests.get(metadata_server + "SCHWAB_APP_KEY", headers=headers).text
```

## Quick Setup Script

```bash
#!/bin/bash
# setup_env.sh - Run this on your GCP VM

cd ~/bot-trader

cat > .env << 'ENVEOF'
SCHWAB_APP_KEY=your-schwab-app-key
SCHWAB_APP_SECRET=your-schwab-app-secret
SCHWAB_CALLBACK_URL=https://your-domain.com
DATABASE_URL=postgresql://user:password@host/database
GMAIL_USER=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
ENVEOF

chmod 600 .env
echo "✅ .env file created"
```

## Verify Setup

Test that variables are loaded:
```bash
cd ~/bot-trader
source .env  # or python3 -c "from dotenv import load_dotenv; load_dotenv()"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('SCHWAB_APP_KEY:', 'Set' if os.getenv('SCHWAB_APP_KEY') else 'Missing')
print('DATABASE_URL:', 'Set' if os.getenv('DATABASE_URL') else 'Missing')
"
```

## Important Notes

1. **Never commit .env to git** - It's in .gitignore
2. **Use secrets manager** for production (most secure)
3. **SCHWAB_CALLBACK_URL** must match your portal settings
4. **DATABASE_URL** should be your Neon connection string
5. **Token file** - You'll need to transfer token.json or generate new one via OAuth


