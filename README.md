# Premium Virtual Number Marketplace (Telegram Bot & FastAPI)

A complete, production-grade marketplace bot for Telegram that allows buying and selling authorized virtual numbers and SMS-testing inventory with integrated Whop payments, dual-currency pricing (INR/USD), seller earnings, commission management, and an admin approval workflow.

Designed to run as a single unified **Render Web Service** running FastAPI and the Telegram Bot concurrently.

---

## 📑 Project Structure

```text
├── app.py              # FastAPI server (lifespan manager, /health, /webhooks/whop)
├── bot.py              # Telegram Bot builder, handler registrations, error handling
├── config.py           # Environment variables, security validators, admin resolution
├── database.py         # SQLAlchemy database engine, sessions, atomic order fulfillment
├── models.py           # SQLite tables (Users, Numbers, Orders, Listings, Wallets, etc.)
├── payments.py         # Whop payment checkout abstraction & HMAC-SHA256 webhook validator
├── keyboards.py        # Reusable ReplyKeyboardMarkup & InlineKeyboardMarkup UI components
├── handlers.py         # User-facing bot handlers (Buy, Sell, Wallet, Earnings, Profile)
├── admin.py            # Admin control panel, inventory, approvals, payouts, settings
├── requirements.txt    # Python dependencies
├── render.yaml         # Render Web Service deployment configuration
├── .env.example        # Environment variable template
└── README.md           # Setup and deployment documentation
```

---

## 🔒 Important Safety & Compliance Scope

This project is strictly for **authorized virtual numbers and SMS-testing inventory**.
It explicitly **does not** support or contain:
- Telegram OTP interception
- Account activation or takeover mechanisms
- Stolen or unauthorized credentials
- OTP forwarding or interception loops

---

## 🚀 Setup & Configuration Guide

### 1. Create Telegram Bot with BotFather
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to choose a name and username.
3. Copy the generated HTTP API Token (`BOT_TOKEN`).

### 2. Obtain Your Telegram User ID (`ADMIN_IDS`)
1. In Telegram, search for `@userinfobot` or `@raw_data_bot` and send `/start`.
2. Copy your numerical ID (e.g., `123456789`).
3. If you have multiple administrators, separate them with commas (e.g., `123456789,987654321`).

### 3. Configure Whop Payments (For Individual or Business Accounts)

> **Note for Individual Creators (PAN Card / Personal ID Verification):**
> Whop uses the word "Company" internally to denote your **Store / Merchant Account**. You **do not need a registered company, business registration, or corporate tax ID** (no GSTIN, CIN, EIN, etc.). Whop automatically assigns a unique `biz_...` identifier to your individual store upon personal KYC verification.

1. **Where to find your Whop Company ID (`biz_...`)**:
   - **Method A (Easiest — In the Browser URL)**:
     Log into your Whop dashboard at [dash.whop.com](https://dash.whop.com). Look at your browser address bar:
     `https://dash.whop.com/biz_xxxxxxxxxxxxxx/...`
     The string starting with `biz_` is your Company ID!
   - **Method B (Settings Page)**:
     In Whop dashboard, go to **Settings** > **Developer** or **Settings** > **General**. Your Store/Company ID starting with `biz_` is displayed there.
   - **Method C (Automatic Discovery)**:
     If you leave `WHOP_COMPANY_ID` blank, our bot automatically calls `https://api.whop.com/api/v1/companies` using your `WHOP_API_KEY` to discover and use your individual `biz_...` identifier on startup!

2. **Generate your API Key (`WHOP_API_KEY`)**:
   - In Whop Dashboard, navigate to **Settings** > **Developer** > **API Keys**.
   - Click **Create Key**, give it a name (e.g., `Telegram Marketplace`), and copy the key (e.g., `whop_live_...`).

3. **Configure Webhook (`WHOP_WEBHOOK_SECRET`)**:
   - Go to **Settings** > **Developer** > **Webhooks**.
   - Click **Add Endpoint**.
   - **Endpoint URL**: `https://your-service.onrender.com/webhooks/whop` (or your ngrok / local domain for testing).
   - Select Events:
     - `payment.succeeded`
     - `payment.failed`
     - `checkout.session.completed`
   - Save and copy the **Webhook Secret** (`whop_whsec_...`).

### Summary of Required Credentials for Telegram Bot Payment Integration:
- **`WHOP_API_KEY`** (Required): Authenticates session creation and auto-retrieves store details.
- **`WHOP_WEBHOOK_SECRET`** (Required): Cryptographically validates payment success callbacks so orders are fulfilled safely.
- **`WHOP_COMPANY_ID`** (Optional / Auto-resolved): Your store's `biz_...` identifier (can be pasted from dashboard URL or auto-discovered by the bot).
- **Zero Business Tax IDs Required**: No company registration, tax certificates, or corporate documentation needed.

---

## 💻 Local Development

### Step 1: Clone and Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Create Environment File
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Fill in your `.env` variables:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
ADMIN_IDS=123456789
WHOP_API_KEY=whop_live_xxxxxx
WHOP_WEBHOOK_SECRET=whop_whsec_xxxxxx
WHOP_COMPANY_ID=biz_xxxxxx
DATABASE_URL=sqlite:///marketplace.db
PORT=10000
SUPPORT_USERNAME=YourSupportHandle
```

### Step 3: Run the Application
```bash
python app.py
```
Or via Uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 10000
```

Verify the health endpoint:
```bash
curl http://localhost:10000/health
# {"status":"ok"}
```

---

## 🌐 Deploy to Render Web Service

### Option A: Deploy with Blueprint (`render.yaml`)
1. Push this repository to GitHub or GitLab.
2. Go to the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your repository. Render will automatically parse `render.yaml`.
5. Enter the required environment secrets under Environment Variables.

### Option B: Deploy Manually as a Web Service
1. In Render, click **New +** > **Web Service**.
2. Connect your Git repository.
3. Configure:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `PYTHON_VERSION`: `3.11.9`
   - `BOT_TOKEN`: (Your Telegram bot token)
   - `ADMIN_IDS`: (Comma-separated admin IDs)
   - `WHOP_API_KEY`: (Your Whop API key)
   - `WHOP_WEBHOOK_SECRET`: (Your Whop webhook signing secret)
   - `WHOP_COMPANY_ID`: (Your Whop company ID)
   - `DATABASE_URL`: `sqlite:///marketplace.db` (or persistent disk mount path)
   - `SUPPORT_USERNAME`: (Your Telegram handle without `@`)

---

## 🧪 Testing Checklist

1. **Bot Startup**: Open your bot on Telegram and send `/start`. The menu and welcome message should appear.
2. **Admin Panel Access**: If your ID is in `ADMIN_IDS`, you will see `🛠 ADMIN PANEL`.
3. **Add Inventory**:
   - In Admin Panel, click `➕ ADD NUMBER` and follow the prompts.
   - Or click `📥 BULK ADD` and paste:
     ```text
     +12025550100 | United States | SMS Testing | 199 | 2.50
     +919876543210 | India | API Verification | 149 | 2.00
     ```
4. **Buyer Experience**:
   - Send `🛒 BUY NUMBER`.
   - Select Country > Service > Click on a number.
   - Click `💳 PAY NOW`. The bot creates a pending order and outputs a secure checkout link.
5. **Webhook Confirmation**:
   - When payment completes on Whop, the webhook receives the event, verifies the signature, fulfills the order, and sends the delivery details to the user in Telegram.
6. **Seller Listing**:
   - Non-admin or seller clicks `💰 SELL NUMBER` and fills out the form.
   - Admins receive immediate Telegram alerts with `[✅ APPROVE]` and `[❌ REJECT]` buttons.
7. **Payout Requests**:
   - When seller items sell, net funds (minus commission) are credited to their `💳 WALLET`.
   - Sellers click `💸 REQUEST PAYOUT` to withdraw funds to UPI/Bank/PayPal.
