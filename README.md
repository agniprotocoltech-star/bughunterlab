# BugHunter Lab — AgniProtocol
**Real-world CTF Platform | Bug Bounty Training | Built by Ganpat N. Darade**

---

## Stack
- **Frontend:** Vanilla HTML/CSS/JS (deployable on Vercel/Netlify free)
- **Backend:** Python Flask + SQLite → upgrade to PostgreSQL for production
- **Auth:** JWT (flask-jwt-extended)
- **Payments:** Razorpay (Indian payment gateway)
- **Certificates:** PIL (PNG) or HTML fallback
- **AI:** Anthropic API (via Claude)

---

## Quick Start (Local)

```bash
# 1. Clone and setup backend
cd backend
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env — add your Razorpay keys

# 3. Run
python app.py
# → http://localhost:5000
```

---

## Razorpay Setup (5 minutes)

1. Go to https://dashboard.razorpay.com
2. Create account → Test mode
3. Settings → API Keys → Generate Key
4. Copy Key ID and Secret to .env
5. Go live when ready → switch to live keys

**Test card:** 4111 1111 1111 1111 | CVV: any | Expiry: any future date

---

## Deploy to Production (Free)

### Backend → Railway.app
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway new
railway up
# Set env vars in Railway dashboard
```

### Frontend → Vercel
```bash
# Change API URL in frontend HTML:
# const API = 'https://your-railway-app.railway.app/api'
npx vercel --prod
```

### Domain
- Buy from GoDaddy/Namecheap: bughunterlab.in (~₹800/year)
- Point to Vercel

**Total infra cost: ₹0-800/month** (free tier covers 500 users easily)

---

## Revenue Model

| Plan | Price | Features |
|------|-------|---------|
| Free | ₹0 | 3 challenges, community |
| Pro | ₹299/mo | All challenges, AI hints, certs, Discord |
| Elite | ₹799/mo | Pro + 1:1 mentorship, live program guidance |

**Break-even:** 50 Pro users = ₹14,950/mo
**5k/day target:** 170 Pro users OR 63 Elite users

---

## Roadmap

- [ ] Add more challenges (IDOR, SSRF, XXE, RCE, JWT, GraphQL)
- [ ] Discord bot integration (auto-role on subscription)
- [ ] Android APK challenges (upload APK, solve in browser)
- [ ] Video writeups (Pro/Elite only)
- [ ] Monthly CTF competitions (prize pool)
- [ ] Corporate training packages (B2B)
- [ ] API for third-party integrations

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/auth/register | No | Create account |
| POST | /api/auth/login | No | Login → JWT |
| GET | /api/auth/me | JWT | Current user info |
| GET | /api/challenges | JWT | List challenges |
| POST | /api/challenges/:id/submit | JWT | Submit flag |
| GET | /api/challenges/:id/hint | JWT (Pro) | Get hint |
| GET | /api/leaderboard | No | Top 50 |
| POST | /api/payment/create-order | JWT | Create Razorpay order |
| POST | /api/payment/verify | JWT | Verify & upgrade plan |
| GET | /api/certificates | JWT | List my certs |
| GET | /api/admin/stats | JWT (Admin) | Revenue & user stats |

---

*Built by Ganpat N. Darade — AgniProtocol Tech*
*HackerOne: agniprotocoltech | Google VRP Hall of Fame*
