# DNS Configuration for lexara.tech

Guide to set up your domain with FastAPI.com

---

## 🌐 Domain: lexara.tech

Your free domain is ready to use!

---

## 🚀 FastAPI.com Deployment with Custom Domain

### Step 1: Deploy to FastAPI.com First

1. Go to **fastapi.com** → **New Project**
2. Select GitHub → **lexrisk-api**
3. Click **Deploy**
4. FastAPI.com will give you a temporary URL:
   ```
   https://lexara-abc123.fastapi.run
   ```

### Step 2: Add Custom Domain to FastAPI.com

1. In FastAPI.com dashboard → **Settings** → **Custom Domains**
2. Click **"Add Domain"**
3. Enter: `lexara.tech`
4. FastAPI.com will show you nameserver instructions or CNAME

### Step 3: Configure DNS at Your Domain Registrar

Since you have a **free domain** (likely from a free domain service), the process depends on where it's hosted.

#### Option A: If hosted at Freenom, Name.com, etc.

**Using Nameservers (Easiest):**

1. Get FastAPI.com's nameservers (they'll provide 4):
   ```
   ns1.fastapi.com
   ns2.fastapi.com
   ns3.fastapi.com
   ns4.fastapi.com
   ```

2. Go to your domain provider's dashboard
3. Find **Nameserver Settings** or **DNS Settings**
4. Replace all nameservers with FastAPI.com's
5. Save and wait 24-48 hours for propagation

**Using CNAME (If nameservers not available):**

1. Get your FastAPI.com URL: `lexara-abc123.fastapi.run`
2. Go to your domain provider's DNS settings
3. Create a CNAME record:
   ```
   Type:   CNAME
   Name:   www
   Value:  lexara-abc123.fastapi.run
   TTL:    3600
   ```

4. Create an A record for the root:
   ```
   Type:   A
   Name:   @
   Value:  [FastAPI.com IP, they'll provide]
   TTL:    3600
   ```

#### Option B: If using a Free Domain Service

**Freenom (freenom.com):**
1. Log in to your Freenom account
2. Go to **My Domains** → **Manage Domain** → **Management Tools** → **Nameservers**
3. Change to FastAPI.com's nameservers
4. Save

**Name.com (name.com):**
1. Log in to Name.com
2. Go to your domain → **DNS Settings**
3. Set nameservers to FastAPI.com's
4. Save

---

## ✅ Verify DNS Setup

```bash
# Check if DNS is pointing to FastAPI.com
nslookup lexara.tech
# Should resolve to FastAPI.com's IP

# Test your API
curl https://lexara.tech/health
# Should return: {"status": "healthy"}
```

---

## 🔒 SSL Certificate

FastAPI.com will **automatically issue an SSL certificate** (via Let's Encrypt) once DNS is configured.

This happens automatically — no extra action needed!

Once verified:
- ✅ `https://lexara.tech` will work
- ✅ Browser shows 🔒 secure
- ✅ No warnings

---

## 📝 Quick DNS Checklist

- [ ] Deploy to FastAPI.com
- [ ] Add `lexara.tech` as custom domain in FastAPI.com settings
- [ ] Get nameservers/CNAME from FastAPI.com
- [ ] Update DNS at domain registrar
- [ ] Wait 24-48 hours for propagation
- [ ] Test with `curl https://lexara.tech/health`
- [ ] Verify SSL certificate issued
- [ ] Update links in documentation

---

## 🎯 Final URLs

Once DNS is configured:

| URL | Purpose |
|-----|---------|
| `https://lexara.tech` | Landing page |
| `https://lexara.tech/docs` | API documentation (Swagger) |
| `https://lexara.tech/health` | Health check |
| `https://api.lexara.tech` | API endpoint (optional subdomain) |

---

## 🚨 Troubleshooting

### DNS Not Resolving

```bash
# Check DNS propagation
nslookup lexara.tech

# Check globally
host lexara.tech

# Use online tool: whatsmydns.net
```

### SSL Certificate Not Issued

1. Ensure DNS is propagated (24-48 hours)
2. Check FastAPI.com dashboard for certificate status
3. Try manually triggering certificate renewal

### Domain Points to Wrong Server

1. Verify nameservers with `nslookup -type=NS lexara.tech`
2. Should return FastAPI.com's nameservers
3. Clear your browser DNS cache (or restart)

---

## 📊 DNS Configuration Example

If using **Freenom** + **FastAPI.com**:

```
Domain:    lexara.tech
Registrar: Freenom
Hosting:   FastAPI.com

Nameservers (at Freenom):
  1. ns1.fastapi.com
  2. ns2.fastapi.com
  3. ns3.fastapi.com
  4. ns4.fastapi.com

FastAPI.com Settings:
  - Custom Domain: lexara.tech
  - SSL: Auto-issued
```

---

## ✨ Expected Timeline

- **Now**: Deploy to FastAPI.com
- **5 min**: Add custom domain to FastAPI.com
- **5 min**: Update DNS at registrar
- **5-30 min**: First DNS propagation
- **1-24 hours**: Full global propagation
- **30 min-2 hours**: SSL certificate issued

**Total time to production: 1-2 hours**

---

## 🎉 Success Indicators

You'll know it's working when:

✅ `nslookup lexara.tech` returns FastAPI.com's IP
✅ `https://lexara.tech` loads your site (no SSL warning)
✅ `https://lexara.tech/docs` shows Swagger API docs
✅ `curl -i https://lexara.tech/health` returns 200 OK

---

Need help? Check FastAPI.com docs or contact support@fastapi.com

