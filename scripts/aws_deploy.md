# AWS Deployment Guide

Deploy bot-trader to AWS EC2 instance without needing browser access.

## Overview

The solution: Create `token.json` **locally** (one-time with browser), then use it on AWS via environment variable. No browser needed on AWS!

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

## Step 2: Extract Token for AWS

```bash
# Extract token content for environment variable
python3 scripts/extract_token.py
```

This will output the `SCHWAB_TOKEN_JSON` value you need.

**Copy that entire output** - you'll need it for AWS.

## Step 3: Create AWS EC2 Instance

1. **Launch EC2 Instance**
   - **AMI**: Ubuntu 22.04 LTS or Amazon Linux 2023
   - **Instance Type**: t3.micro or t3.small (Free tier eligible: t2.micro)
   - **Security Group**: Open ports:
     - 22 (SSH)
     - 8000 (FastAPI - optional, restrict to your IP)

2. **Connect to Instance**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   # Or for Amazon Linux:
   ssh -i your-key.pem ec2-user@your-ec2-ip
   ```

## Step 4: Install Dependencies on AWS

```bash
# Update system
sudo apt-get update  # Ubuntu
# OR
sudo yum update -y   # Amazon Linux

# Install Python 3.10+
sudo apt-get install -y python3 python3-pip python3-venv git  # Ubuntu
# OR
sudo yum install -y python3 python3-pip git  # Amazon Linux

# Install system dependencies
sudo apt-get install -y build-essential  # Ubuntu
```

## Step 5: Deploy Application

```bash
# Clone or copy your repository
git clone <your-repo-url> bot-trader
cd bot-trader

# OR copy via SCP from local machine:
# scp -r /path/to/bot-trader/* ubuntu@ec2-ip:~/bot-trader/
```

## Step 6: Set Up Environment

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

## Step 7: Install Application

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 8: Test Locally

```bash
# Test that everything works
source venv/bin/activate
python3 start.py
```

If it starts without errors, you're good! Press Ctrl+C to stop.

## Step 9: Set Up Systemd Service (Optional)

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
ExecStart=/home/ubuntu/bot-trader/venv/bin/python /home/ubuntu/bot-trader/start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

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

## Step 10: Verify Deployment

```bash
# Check if API is responding
curl http://localhost:8000/health

# Check service status
sudo systemctl status bot-trader
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
cd /home/ubuntu/bot-trader
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
- Token should be created locally first (Step 1)

## Token Refresh

The `schwab-py` library automatically refreshes tokens when they expire. As long as:
- Your service runs regularly
- The refresh token hasn't expired (~90 days)
- The service can reach Schwab API

It will automatically refresh without needing browser or manual intervention.

## Security Best Practices

1. **Never commit `.env` or `token.json`** to git
2. **Use AWS Secrets Manager** or **Parameter Store** for sensitive values
3. **Restrict security group** to only necessary IPs
4. **Use IAM roles** instead of hardcoding credentials
5. **Regularly rotate** API credentials if compromised

### Using AWS Secrets Manager (Optional)

Instead of `.env` file, use AWS Secrets Manager:

```bash
# Install AWS CLI
pip install awscli

# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name bot-trader/secrets \
  --secret-string file://secrets.json

# Retrieve in your code or startup script
aws secretsmanager get-secret-value --secret-id bot-trader/secrets
```

## Cost Estimate

- **EC2 t2.micro**: Free tier eligible (750 hours/month)
- **EC2 t3.micro**: ~$7.50/month (~$0.0104/hour)
- **Data Transfer**: First 100GB/month free

**Total**: **$0-$10/month** depending on instance type.

## Next Steps

- Set up nginx reverse proxy for production
- Configure SSL/TLS certificates
- Set up CloudWatch logging
- Configure auto-scaling if needed



