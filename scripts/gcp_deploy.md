# Google Cloud Deployment Guide

Deploy bot-trader to Google Cloud Platform (Compute Engine) without needing browser access.

## Overview

The solution: Create `token.json` **locally** (one-time with browser), then use it on GCP via environment variable. No browser needed on GCP!

## Step 1: Create Token Locally (One-Time)

On your **local machine**, create the token:

```bash
# 1. Set up your .env file with Schwab credentials
cp .env.example .env
# Edit .env and add SCHWAB_APP_KEY and SCHWAB_APP_SECRET

# 2. Install dependencies locally
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Run the streamer - this will open browser for OAuth
python3 schwab_streamer.py
```

After OAuth completes, `token.json` will be created in your project directory.

## Step 2: Extract Token for GCP

```bash
# Extract token content for environment variable
python3 scripts/extract_token.py
```

This will output the `SCHWAB_TOKEN_JSON` value you need.

**Copy that entire output** - you'll need it for GCP.

## Step 3: Create GCP Compute Engine Instance

### Option A: Via Console

1. **Go to Google Cloud Console**
   - Navigate to Compute Engine → VM instances
   - Click "Create Instance"

2. **Configure Instance**
   - **Name**: `bot-trader-vm`
   - **Region**: Choose closest region (e.g., `us-central1`)
   - **Machine type**: `e2-micro` or `e2-small` (free tier: e2-micro)
   - **Boot disk**: 
     - **OS**: Ubuntu 22.04 LTS
     - **Size**: 10 GB (default is fine)
   - **Firewall**: Allow HTTP and HTTPS traffic (if needed)
     - Or manually create firewall rule for port 8000

3. **Network Tags** (Optional):
   - Add tag: `http-server` or `bot-trader`

4. **Create** the instance

### Option B: Via gcloud CLI

```bash
# Set project (replace with your project ID)
gcloud config set project YOUR_PROJECT_ID

# Create instance
gcloud compute instances create bot-trader-vm \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=10GB \
  --tags=http-server
```

### Create Firewall Rule (if needed)

```bash
# Allow port 8000 (optional - restrict to your IP for security)
gcloud compute firewall-rules create allow-bot-trader \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow bot-trader API port"
```

Or restrict to your IP:

```bash
gcloud compute firewall-rules create allow-bot-trader \
  --allow tcp:8000 \
  --source-ranges YOUR_IP_ADDRESS/32 \
  --description "Allow bot-trader API port from my IP"
```

## Step 4: Connect to Instance

```bash
# SSH into instance
gcloud compute ssh bot-trader-vm --zone=us-central1-a

# OR use standard SSH with your SSH key
ssh -i ~/.ssh/google_compute_engine ubuntu@EXTERNAL_IP
```

## Step 5: Install Dependencies on GCP

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.10+
sudo apt-get install -y python3 python3-pip python3-venv git build-essential
```

## Step 6: Deploy Application

### Option A: Clone from Git

```bash
# Clone repository
git clone <your-repo-url> bot-trader
cd bot-trader
```

### Option B: Copy via gcloud

On your local machine:

```bash
# Copy files to GCP instance
gcloud compute scp --recurse . bot-trader-vm:~/bot-trader --zone=us-central1-a
```

Then on the instance:

```bash
cd ~/bot-trader
```

## Step 7: Set Up Environment

```bash
# Create .env file
nano .env
```

Add these variables:

```bash
# Schwab API Credentials
SCHWAB_APP_KEY=your_app_key_here
SCHWAB_APP_SECRET=your_app_secret_here
SCHWAB_CALLBACK_URL=http://127.0.0.1

# Server Configuration
PORT=8000
HOST=0.0.0.0

# CRITICAL: Paste the token JSON from Step 2
# This is the token you extracted locally
SCHWAB_TOKEN_JSON='{"access_token":"...","refresh_token":"...","token_type":"Bearer",...}'
```

**Important**: The `SCHWAB_TOKEN_JSON` value should be the **entire JSON object** as a single-line string (exactly as output by `scripts/extract_token.py`).

### Alternative: Use Google Secret Manager (Recommended)

For better security, use Google Secret Manager:

```bash
# Install gcloud CLI on GCP instance (if not already installed)
curl https://sdk.cloud.google.com | bash

# Store secrets in Secret Manager (from local machine or GCP)
gcloud secrets create bot-trader-secrets --data-file=secrets.json

# Grant access to the service account
gcloud secrets add-iam-policy-binding bot-trader-secrets \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

Then in your startup script, retrieve secrets:

```python
from google.cloud import secretmanager

def get_secret(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

## Step 8: Install Application

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 9: Test Locally

```bash
# Test that everything works
source venv/bin/activate
python3 start.py
```

If it starts without errors, you're good! Press Ctrl+C to stop.

## Step 10: Set Up Systemd Service

Create a service to run automatically on boot:

```bash
sudo nano /etc/systemd/system/bot-trader.service
```

Add:

```ini
[Unit]
Description=Bot Trader Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot-trader
Environment="PATH=/home/ubuntu/bot-trader/venv/bin"
Environment="PRODUCTION=true"
ExecStart=/home/ubuntu/bot-trader/venv/bin/python /home/ubuntu/bot-trader/start.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Note**: The `Environment="PRODUCTION=true"` ensures the code knows it's in production.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bot-trader
sudo systemctl start bot-trader
sudo systemctl status bot-trader
```

View logs:

```bash
sudo journalctl -u bot-trader -f
```

## Step 11: Verify Deployment

```bash
# Check if API is responding
curl http://localhost:8000/health

# Check external access (replace with your external IP)
curl http://EXTERNAL_IP:8000/health

# Check service status
sudo systemctl status bot-trader
```

## Step 12: Set Up Load Balancer (Optional)

For production with HTTPS:

```bash
# Create health check
gcloud compute health-checks create http bot-trader-health-check \
  --port=8000 \
  --request-path=/health

# Create instance group
gcloud compute instance-groups unmanaged create bot-trader-group \
  --zone=us-central1-a

gcloud compute instance-groups unmanaged add-instances bot-trader-group \
  --instances=bot-trader-vm \
  --zone=us-central1-a

# Create backend service
gcloud compute backend-services create bot-trader-backend \
  --health-checks=bot-trader-health-check \
  --global

gcloud compute backend-services add-backend bot-trader-backend \
  --instance-group=bot-trader-group \
  --instance-group-zone=us-central1-a \
  --global
```

## Troubleshooting

### Token Authentication Fails

- **Check SCHWAB_TOKEN_JSON format**: Must be valid JSON, single-line, properly escaped
- **Verify token hasn't expired**: Tokens last ~90 days if not used
- **Check logs**: `sudo journalctl -u bot-trader -n 50`

### Service Won't Start

```bash
# Check logs
sudo journalctl -u bot-trader -n 50

# Check .env file has all required variables
cat .env

# Test manually
cd ~/bot-trader
source venv/bin/activate
python3 start.py
```

### Port Already in Use

```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill the process if needed
sudo kill -9 <PID>
```

### OAuth Error in Production

If you see "OAuth flow not available in production":
- This is **expected** - OAuth only works locally
- Make sure `SCHWAB_TOKEN_JSON` is set in `.env` or environment
- Make sure `PRODUCTION=true` is set in systemd service file
- Token should be created locally first (Step 1)

### Cannot Connect to Instance

```bash
# Check instance is running
gcloud compute instances list

# Check firewall rules
gcloud compute firewall-rules list

# Check instance has external IP
gcloud compute instances describe bot-trader-vm --zone=us-central1-a
```

## Token Refresh

The `schwab-py` library automatically refreshes tokens when they expire. As long as:
- Your service runs regularly
- The refresh token hasn't expired (~90 days)
- The service can reach Schwab API

It will automatically refresh without needing browser or manual intervention.

## Cost Estimate

### Free Tier (Always Free):
- **e2-micro**: 1 vCPU, 1GB RAM
- **30 GB-months** of standard persistent disk
- **1 GB network egress** per month

### Beyond Free Tier:
- **e2-small**: ~$12/month (~$0.017/hour)
- **e2-medium**: ~$24/month (~$0.033/hour)
- **Network egress**: First 1GB free, then $0.12/GB

**Total**: **$0-$25/month** depending on instance type and usage.

## Security Best Practices

1. **Use Secret Manager** instead of `.env` files for sensitive data
2. **Restrict firewall rules** to only necessary IPs
3. **Use IAM service accounts** with minimal permissions
4. **Enable OS Login** for better SSH security
5. **Regularly update** the system: `sudo apt-get update && sudo apt-get upgrade`
6. **Monitor logs** for suspicious activity

### Using Secret Manager

```bash
# Install Secret Manager client library
pip install google-cloud-secret-manager

# Create secret (from local machine)
echo -n 'your-secret-value' | gcloud secrets create SCHWAB_TOKEN_JSON --data-file=-

# Access secret in Python
from google.cloud import secretmanager

def get_secret(secret_id):
    project_id = "YOUR_PROJECT_ID"
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

## Next Steps

- Set up Cloud Monitoring and alerts
- Configure Cloud Logging for better log management
- Set up automated backups
- Configure auto-scaling if needed
- Set up Cloud CDN for better performance


