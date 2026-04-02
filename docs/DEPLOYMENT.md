# LexRisk Deployment Guide

Complete guide to deploying LexRisk to FastAPI.com and GitHub.

---

## Prerequisites

- Python 3.11+
- Git
- PostgreSQL (local or managed)
- Redis (local or managed)
- FastAPI.com account
- GitHub account
- Stripe account (for billing)
- Anthropic Claude API key

---

## Step 1: Push to GitHub

### 1.1 Create GitHub Repository

```bash
# Go to https://github.com/new
# Create repository: lexrisk-api
# Don't initialize with README (we already have one)
```

### 1.2 Push Local Repo

```bash
cd lexrisk-api

# Add remote (replace USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/lexrisk-api.git
git branch -M main
git push -u origin main
```

### 1.3 Verify on GitHub

Visit: `https://github.com/YOUR_USERNAME/lexrisk-api`

You should see:
- All source files
- README.md
- .github/workflows/tests.yml
- Full commit history

---

## Step 2: Deploy to FastAPI.com

### 2.1 Create FastAPI.com Project

1. Go to **fastapi.com** → Log in
2. Click **"New Project"** → **"Deploy from GitHub"**
3. Select your GitHub account (authorize if needed)
4. Choose **`lexrisk-api`** repository
5. Click **"Connect"**

### 2.2 Configure Build Settings

In FastAPI.com dashboard:

```
Build Command:     pip install -r requirements.txt
Start Command:     uvicorn app.main:app --host 0.0.0.0 --port 8000
Root Directory:    ./
Python Version:    3.11
```

### 2.3 Set Environment Variables

Go to **Project Settings** → **Environment Variables**

Add each variable:

```
CLAUDE_API_KEY                 sk-ant-...
RECEIPTS_API_KEY              sk_live_...
DATABASE_URL                  postgresql://user:pass@host:5432/lexrisk
REDIS_URL                     redis://host:6379/0
STRIPE_SECRET_KEY             sk_live_...
STRIPE_PUBLISHABLE_KEY        pk_live_...
STRIPE_WEBHOOK_SECRET         whsec_...
SECRET_KEY                    [generate: python -c "import secrets; print(secrets.token_urlsafe(32))"]
ALLOWED_ORIGINS               https://lexrisk.com,https://www.lexrisk.com
ENVIRONMENT                   production
DEBUG                         false
```

### 2.4 Deploy

Click **"Deploy"** → FastAPI.com builds and deploys automatically.

Monitor in **Deployments** tab.

### 2.5 Verify Deployment

```bash
# Get your FastAPI.com URL from dashboard
# Should look like: https://lexrisk-abc123.fastapi.run

curl https://YOUR_FASTAPI_URL/health
# Should return: {"status": "healthy", ...}
```

---

## Step 3: Setup Custom Domain

### 3.1 Point Domain to FastAPI.com

In your domain registrar (Namecheap, GoDaddy, etc.):

```
CNAME: lexrisk.com  →  YOUR_FASTAPI_URL.fastapi.run
A Record: (if required) → FastAPI.com's IP
```

Or use FastAPI.com's nameservers directly (easier).

### 3.2 Verify in FastAPI.com

Go to **Project Settings** → **Custom Domains**

Add domain: `lexrisk.com`

FastAPI.com will provide SSL certificate automatically (Let's Encrypt).

---

## Step 4: Setup Database

### 4.1 Option A: Managed PostgreSQL (Recommended)

Use **Amazon RDS**, **Heroku Postgres**, or **Render**:

```bash
# Example: Amazon RDS
# Endpoint: lexrisk-db.c9akciq32.us-east-1.rds.amazonaws.com:5432
# Username: admin
# Password: [your-secure-password]
# Database: lexrisk

# DATABASE_URL format:
postgresql://admin:password@lexrisk-db.c9akciq32.us-east-1.rds.amazonaws.com:5432/lexrisk
```

### 4.2 Initialize Database

```bash
# From local machine
python -c "from app.database.session import init_db; init_db()"

# Or from FastAPI.com console
# (Settings → Shell → run above command)
```

---

## Step 5: Setup Stripe Webhooks

### 5.1 Get Webhook Endpoint URL

From FastAPI.com dashboard:
```
https://lexrisk-abc123.fastapi.run/v1/webhooks/stripe
```

### 5.2 Add Webhook in Stripe Dashboard

Go to **Developers** → **Webhooks**

Click **"Add endpoint"**

```
Endpoint URL:  https://lexrisk-abc123.fastapi.run/v1/webhooks/stripe
Events:
  ✓ customer.subscription.updated
  ✓ customer.subscription.deleted
  ✓ charge.failed
  ✓ invoice.created
```

Copy **Signing secret** (whsec_...) → Add to env vars

---

## Step 6: GitHub Actions CI/CD

### 6.1 Add Secrets to GitHub

Go to **Settings** → **Secrets and variables** → **Actions**

Click **"New repository secret"**

Add:
```
Name: FASTAPI_TOKEN
Value: [Generate from FastAPI.com → Settings → Deploy Keys]

Name: CLAUDE_API_KEY
Value: sk-ant-...

Name: RECEIPTS_API_KEY
Value: sk_live_...
```

### 6.2 Verify Workflow

Push a test commit:
```bash
git add .
git commit -m "Test CI/CD workflow"
git push origin main
```

Go to **Actions** tab on GitHub:
- Should see **"Tests & Deploy"** workflow running
- Should pass tests and auto-deploy to FastAPI.com

---

## Step 7: Monitoring & Logging

### 7.1 CloudWatch (AWS) or FastAPI.com Logs

```bash
# View logs
fastapi logs

# Follow logs in real-time
fastapi logs --follow
```

### 7.2 Error Tracking (Optional)

Add **Sentry** or **DataDog** for error monitoring:

```bash
# Install Sentry SDK
pip install sentry-sdk

# Add to app/main.py
import sentry_sdk
sentry_sdk.init("https://key@sentry.io/project")
```

---

## Step 8: Post-Deployment Checklist

- [ ] API health check: `GET /health` returns 200
- [ ] API docs: Visit `/docs` → Swagger UI loads
- [ ] Analyze endpoint: Test `POST /v1/analyze-contract`
- [ ] Database: Tables created successfully
- [ ] Environment vars: All set in FastAPI.com
- [ ] Stripe webhooks: Receiving events
- [ ] GitHub Actions: Tests passing
- [ ] Domain: CNAME pointing correctly
- [ ] SSL: Certificate issued and valid
- [ ] Analytics: Set up monitoring

---

## Step 9: Local Development

### 9.1 Setup Local Environment

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/lexrisk-api.git
cd lexrisk-api

# Create venv
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install deps
pip install -r requirements.txt

# Copy env
cp .env.example .env
```

### 9.2 Configure Local .env

```bash
# Edit .env with local credentials
CLAUDE_API_KEY=sk-ant-...
DATABASE_URL=postgresql://localhost/lexrisk
REDIS_URL=redis://localhost:6379/0
# ... other vars
```

### 9.3 Run Locally

```bash
# Start dev server
python -m uvicorn app.main:app --reload

# Visit http://localhost:8000/docs
```

---

## Step 10: Update Website

### 10.1 Deploy Website

The website files are in `/website`:
- `index.html` (landing page)
- `styles.css` (AODA-compliant styling)
- `script.js` (accessibility features)

**Option A: Serve from FastAPI**

```python
# In app/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="website", html=True), name="website")
```

**Option B: Deploy separately to Vercel/Netlify**

```bash
# Create vercel.json
{
  "buildCommand": "echo 'No build needed'",
  "outputDirectory": "website"
}

# Deploy
vercel
```

### 10.2 Update DNS

If deploying website separately:
```
www.lexrisk.com  → Vercel
lexrisk.com      → FastAPI.com (API)
```

Or use subdomain:
```
api.lexrisk.com  → FastAPI.com
lexrisk.com      → Vercel
```

---

## Troubleshooting

### Build Fails

```bash
# Check build logs in FastAPI.com dashboard
# Common issues:
# - Missing requirements.txt dependencies
# - Syntax errors in Python code
# - Missing environment variables

# Fix and push:
git add .
git commit -m "Fix build error"
git push origin main
```

### Database Connection Error

```
psycopg2.OperationalError: could not translate host name
```

Check:
1. DATABASE_URL is correct format
2. Database server is running
3. Firewall allows connection
4. Database exists

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Stripe Webhook Not Received

```bash
# Test webhook manually in Stripe Dashboard
# Settings → Webhooks → Click webhook → Test
# Check logs for errors

# If 401: Check STRIPE_WEBHOOK_SECRET env var
# If 404: Check webhook endpoint URL is correct
```

### API Rate Limiting Issues

Check headers:
```bash
curl -i https://lexrisk-abc123.fastapi.run/v1/analyze-contract
```

Look for:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: [timestamp]
```

If rate limited (429): Wait or upgrade plan.

---

## Scaling

### Add More Resources

As traffic grows:

1. **Upgrade FastAPI.com plan** → More concurrent workers
2. **Scale PostgreSQL** → Larger instance
3. **Scale Redis** → Higher memory, cluster mode
4. **Add CDN** → CloudFlare for static assets

### Monitor Performance

```bash
# Response time
curl -w "@curl-format.txt" https://lexrisk-abc123.fastapi.run/health

# Database connections
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

# Redis memory
redis-cli INFO memory
```

---

## Rollback

If deployment fails:

```bash
# FastAPI.com automatically keeps previous versions
# Go to Deployments tab → Click previous version → Rollback

# Or via Git
git revert HEAD
git push origin main
```

---

## Support

- FastAPI.com Docs: https://docs.fastapi.com
- PostgreSQL Docs: https://www.postgresql.org/docs/
- Stripe Docs: https://stripe.com/docs
- Claude API Docs: https://docs.anthropic.com

Contact: support@lexrisk.com
