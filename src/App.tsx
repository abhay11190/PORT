import React, { useState } from 'react';
import {
  Smartphone,
  Server,
  ShieldCheck,
  CreditCard,
  Database,
  Terminal,
  FileCode,
  DollarSign,
  Package,
  Layers,
  Copy,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  AlertCircle,
  HelpCircle,
  Globe,
  Users,
  Settings,
  RefreshCw,
  ShoppingBag,
  ListOrdered
} from 'lucide-react';

type Tab = 'simulator' | 'files' | 'architecture' | 'webhook' | 'deploy';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('simulator');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Telegram Simulator State
  const [currentScreen, setCurrentScreen] = useState<'start' | 'buy_country' | 'buy_services' | 'buy_numbers' | 'confirm_buy' | 'order_checkout' | 'wallet' | 'admin' | 'sell'>('start');
  const [selectedCountry, setSelectedCountry] = useState<string>('India');
  const [selectedService, setSelectedService] = useState<string>('SMS Testing');
  const [selectedCurrency, setSelectedCurrency] = useState<'INR' | 'USD'>('INR');
  const [isAdminMode, setIsAdminMode] = useState<boolean>(true);

  // Selected file viewer
  const [selectedFile, setSelectedFile] = useState<string>('app.py');

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const projectFiles: { name: string; desc: string; size: string }[] = [
    { name: 'app.py', desc: 'FastAPI Webhook server & Bot Lifespan manager', size: '6.2 KB' },
    { name: 'bot.py', desc: 'Telegram Bot builder, handlers & error recovery', size: '5.8 KB' },
    { name: 'database.py', desc: 'SQLAlchemy database engine, sessions & transactions', size: '14.1 KB' },
    { name: 'models.py', desc: 'Data schema (Users, Numbers, Orders, Listings, Wallets)', size: '4.9 KB' },
    { name: 'handlers.py', desc: 'Telegram user flows (Buy, Sell, Wallet, Orders)', size: '16.5 KB' },
    { name: 'admin.py', desc: 'Admin panel, Inventory, Approvals & Bulk additions', size: '16.2 KB' },
    { name: 'payments.py', desc: 'Whop Payments API & HMAC-SHA256 signature verifier', size: '4.8 KB' },
    { name: 'keyboards.py', desc: 'ReplyKeyboardMarkup & InlineKeyboardMarkup UI', size: '5.2 KB' },
    { name: 'config.py', desc: 'Environment variables & safety validators', size: '1.8 KB' },
    { name: 'render.yaml', desc: 'Render Web Service deployment specification', size: '0.8 KB' },
    { name: 'requirements.txt', desc: 'Production dependencies', size: '0.2 KB' },
    { name: 'README.md', desc: 'Complete deployment & configuration manual', size: '5.1 KB' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header Bar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Smartphone className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">Premium Virtual Number Marketplace</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Production Ready
              </span>
            </div>
            <p className="text-xs text-slate-400">Telegram Bot & FastAPI Webhook Server for Render Web Service</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
          <button
            id="tab-simulator"
            onClick={() => setActiveTab('simulator')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'simulator'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Telegram UI Simulator
          </button>
          <button
            id="tab-files"
            onClick={() => setActiveTab('files')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'files'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Project Files
          </button>
          <button
            id="tab-architecture"
            onClick={() => setActiveTab('architecture')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'architecture'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Architecture
          </button>
          <button
            id="tab-webhook"
            onClick={() => setActiveTab('webhook')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'webhook'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Whop Webhook
          </button>
          <button
            id="tab-deploy"
            onClick={() => setActiveTab('deploy')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'deploy'
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Deployment
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {/* TAB 1: TELEGRAM BOT SIMULATOR */}
        {activeTab === 'simulator' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Controls */}
            <div className="lg:col-span-5 space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
                  <Settings className="w-4 h-4 text-blue-400" /> Simulator Controls
                </h2>
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                    <span className="text-slate-300">Admin Privileges</span>
                    <button
                      onClick={() => setIsAdminMode(!isAdminMode)}
                      className={`px-3 py-1 rounded-full font-semibold transition-colors ${
                        isAdminMode ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {isAdminMode ? 'Admin Active' : 'Regular User'}
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                    <span className="text-slate-300">Active Currency</span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setSelectedCurrency('INR')}
                        className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                          selectedCurrency === 'INR' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        🇮🇳 INR (₹)
                      </button>
                      <button
                        onClick={() => setSelectedCurrency('USD')}
                        className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                          selectedCurrency === 'USD' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        🇺🇸 USD ($)
                      </button>
                    </div>
                  </div>

                  <div className="p-3 bg-blue-950/30 border border-blue-900/40 rounded-xl text-blue-200">
                    <p className="font-semibold mb-1 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-blue-400" /> Production Compliance
                    </p>
                    <p className="text-slate-400 leading-relaxed">
                      Only authorized virtual & SMS-testing numbers are supported. No OTP interception or account takeover functions exist.
                    </p>
                  </div>
                </div>
              </div>

              {/* Bot Feature Quick Highlights */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Features Demonstrated</h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
                    <div className="font-medium text-white flex items-center gap-1.5 mb-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Atomic Buy Flow
                    </div>
                    <div className="text-slate-400">Prevents double-booking via status reservation</div>
                  </div>
                  <div className="p-2.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
                    <div className="font-medium text-white flex items-center gap-1.5 mb-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Whop Webhooks
                    </div>
                    <div className="text-slate-400">HMAC-SHA256 signature with deduplication</div>
                  </div>
                  <div className="p-2.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
                    <div className="font-medium text-white flex items-center gap-1.5 mb-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Seller Earnings
                    </div>
                    <div className="text-slate-400">Commission deduction & wallet ledger</div>
                  </div>
                  <div className="p-2.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
                    <div className="font-medium text-white flex items-center gap-1.5 mb-0.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Admin Controls
                    </div>
                    <div className="text-slate-400">Bulk adding, approvals & payout audits</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Phone Mockup Frame */}
            <div className="lg:col-span-7 flex justify-center">
              <div className="w-full max-w-md bg-slate-900 border-4 border-slate-800 rounded-[36px] shadow-2xl overflow-hidden flex flex-col h-[740px]">
                {/* Phone Top Notch / Status */}
                <div className="bg-slate-950 px-6 py-2.5 flex items-center justify-between text-xs text-slate-400 border-b border-slate-800">
                  <span>9:41</span>
                  <div className="w-20 h-4 bg-slate-800 rounded-full mx-auto" />
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px]">5G</span>
                    <div className="w-4 h-2 border border-slate-500 rounded-sm p-0.5 flex items-center">
                      <div className="w-full h-full bg-slate-400 rounded-2xs" />
                    </div>
                  </div>
                </div>

                {/* Telegram Bot Chat Header */}
                <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white font-bold text-sm">
                    💎
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm text-white truncate">Premium Virtual Numbers</h3>
                    <p className="text-[11px] text-emerald-400">bot • running on Render</p>
                  </div>
                  <button
                    onClick={() => setCurrentScreen('start')}
                    title="Reset Simulator"
                    className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>

                {/* Message Scroll Area */}
                <div className="flex-1 bg-slate-950 p-4 overflow-y-auto space-y-4 text-xs leading-relaxed">
                  {/* Start Message Box */}
                  <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm max-w-[90%]">
                    <p className="font-mono text-slate-400 text-[10px]">━━━━━━━━━━━━━━━━━━</p>
                    <p className="font-bold text-cyan-400 text-sm my-1">💎 PREMIUM MARKETPLACE</p>
                    <p className="font-mono text-slate-400 text-[10px] mb-2">━━━━━━━━━━━━━━━━━━</p>
                    <p className="text-slate-200 font-medium mb-2">Welcome to Premium Virtual Number Marketplace</p>
                    <div className="space-y-1 text-slate-300">
                      <p>• 🛒 Buy authorized virtual numbers</p>
                      <p>• 💰 Sell your authorized inventory</p>
                      <p>• ⚡ Fast payment verification (Whop)</p>
                      <p>• 📦 Secure order tracking</p>
                      <p>• 💱 Dual pricing: 🇮🇳 INR / 🇺🇸 USD</p>
                      <p>• 💵 Seller earnings & transparent payouts</p>
                    </div>
                  </div>

                  {/* Interactive Screen Details */}
                  {currentScreen === 'buy_country' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-white flex items-center gap-1.5">
                        <Globe className="w-4 h-4 text-blue-400" /> 🌍 Select Country
                      </p>
                      <p className="text-slate-400">Select a country to browse authorized virtual numbers:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {['India (14)', 'United States (28)', 'United Kingdom (9)', 'Canada (6)'].map((c) => (
                          <button
                            key={c}
                            onClick={() => {
                              setSelectedCountry(c.split(' ')[0]);
                              setCurrentScreen('buy_services');
                            }}
                            className="p-2.5 bg-slate-950 hover:bg-blue-600/20 hover:border-blue-500 border border-slate-800 rounded-xl text-left font-medium text-slate-200 transition-colors"
                          >
                            {c}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {currentScreen === 'buy_services' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-white flex items-center gap-1.5">
                        <Layers className="w-4 h-4 text-blue-400" /> 📱 Select Service ({selectedCountry})
                      </p>
                      <p className="text-slate-400">Choose an authorized testing service category:</p>
                      <div className="space-y-1.5">
                        {['SMS Testing (8)', 'API Sandbox Verification (4)', 'Platform Staging (2)'].map((s) => (
                          <button
                            key={s}
                            onClick={() => {
                              setSelectedService(s.split(' (')[0]);
                              setCurrentScreen('buy_numbers');
                            }}
                            className="w-full p-2.5 bg-slate-950 hover:bg-blue-600/20 hover:border-blue-500 border border-slate-800 rounded-xl text-left font-medium text-slate-200 flex items-center justify-between transition-colors"
                          >
                            <span>{s}</span>
                            <ChevronRight className="w-4 h-4 text-slate-500" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {currentScreen === 'buy_numbers' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-white">
                        📱 Available in {selectedCountry} ({selectedService})
                      </p>
                      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="text-xs font-mono font-bold text-cyan-400">+91 98765 43210</span>
                            <p className="text-[11px] text-slate-400">{selectedCountry} • {selectedService}</p>
                          </div>
                          <span className="font-bold text-emerald-400">
                            {selectedCurrency === 'INR' ? '₹199' : '$2.50'}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500">ID: #1024 • Fresh authorized stock</p>
                        <button
                          onClick={() => setCurrentScreen('confirm_buy')}
                          className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs transition-colors"
                        >
                          🛒 BUY NOW (#1024)
                        </button>
                      </div>
                    </div>
                  )}

                  {currentScreen === 'confirm_buy' && (
                    <div className="bg-slate-900 border border-blue-500/40 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-white text-sm">🛒 Confirm Purchase</p>
                      <div className="space-y-1 text-slate-300 bg-slate-950 p-3 rounded-xl border border-slate-800">
                        <p><span className="text-slate-500">Number:</span> +91 98765 43210</p>
                        <p><span className="text-slate-500">Country:</span> {selectedCountry}</p>
                        <p><span className="text-slate-500">Service:</span> {selectedService}</p>
                        <p className="font-bold text-white pt-1 border-t border-slate-800">
                          Total Price: {selectedCurrency === 'INR' ? '₹199.00 INR' : '$2.50 USD'}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <button
                          onClick={() => setCurrentScreen('order_checkout')}
                          className="py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-center shadow-lg shadow-emerald-600/20"
                        >
                          💳 PAY NOW
                        </button>
                        <button
                          onClick={() => setCurrentScreen('start')}
                          className="py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-center"
                        >
                          ❌ CANCEL
                        </button>
                      </div>
                    </div>
                  )}

                  {currentScreen === 'order_checkout' && (
                    <div className="bg-slate-900 border border-emerald-500/40 rounded-2xl p-4 space-y-3">
                      <div className="flex items-center gap-2 text-emerald-400 font-bold">
                        <CheckCircle2 className="w-5 h-5" /> Pending Whop Payment
                      </div>
                      <p className="text-slate-300">
                        Order <code className="bg-slate-950 px-1.5 py-0.5 rounded text-cyan-300">ORD-A8B9C2D1</code> is reserved. Complete payment on Whop:
                      </p>
                      <a
                        href="#whop-link"
                        onClick={(e) => {
                          e.preventDefault();
                          alert("In production, this opens Whop Checkout. Once paid, the Whop webhook triggers instant delivery!");
                        }}
                        className="block w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-center rounded-xl shadow-lg"
                      >
                        💳 Pay via Whop Checkout
                      </a>
                      <button
                        onClick={() => setCurrentScreen('start')}
                        className="w-full py-1.5 text-slate-400 hover:text-rose-400 text-[11px]"
                      >
                        ❌ Cancel Order & Release Number
                      </button>
                    </div>
                  )}

                  {currentScreen === 'wallet' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-white flex items-center gap-2">
                        <CreditCard className="w-4 h-4 text-cyan-400" /> Account Wallet & Balances
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800">
                          <p className="text-[10px] text-slate-400">INR Balance</p>
                          <p className="text-base font-bold text-emerald-400">₹895.00</p>
                        </div>
                        <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800">
                          <p className="text-[10px] text-slate-400">USD Balance</p>
                          <p className="text-base font-bold text-emerald-400">$11.50</p>
                        </div>
                      </div>
                      <button
                        onClick={() => alert("Payout request conversation initiated in bot. Admin is notified to approve & pay!")}
                        className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-center"
                      >
                        💸 REQUEST PAYOUT
                      </button>
                    </div>
                  )}

                  {currentScreen === 'admin' && (
                    <div className="bg-slate-900 border border-amber-500/40 rounded-2xl p-4 space-y-3">
                      <p className="font-bold text-amber-400 flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4" /> Admin Control Dashboard
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                          <p className="text-slate-400">Total Users</p>
                          <p className="text-sm font-bold text-white">128</p>
                        </div>
                        <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                          <p className="text-slate-400">Available Numbers</p>
                          <p className="text-sm font-bold text-emerald-400">57</p>
                        </div>
                        <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                          <p className="text-slate-400">Pending Listings</p>
                          <p className="text-sm font-bold text-amber-400">3</p>
                        </div>
                        <div className="p-2 bg-slate-950 rounded-lg border border-slate-800">
                          <p className="text-slate-400">Marketplace Comm.</p>
                          <p className="text-sm font-bold text-cyan-400">10%</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {currentScreen === 'sell' && (
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2">
                      <p className="font-bold text-white flex items-center gap-1.5">
                        <DollarSign className="w-4 h-4 text-emerald-400" /> Sell Virtual Number
                      </p>
                      <p className="text-slate-400 text-[11px]">
                        Step-by-step ConversationHandler prompts seller for Phone Number, Country, Service, INR/USD Price, and Description.
                        Submissions go directly to the admin queue for verification.
                      </p>
                    </div>
                  )}
                </div>

                {/* Telegram ReplyKeyboardMarkup (Custom Keyboard) */}
                <div className="bg-slate-900 border-t border-slate-800 p-2.5 space-y-1.5">
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => setCurrentScreen('buy_country')}
                      className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-sm active:scale-95 transition-all"
                    >
                      🛒 BUY NUMBER
                    </button>
                    <button
                      onClick={() => setCurrentScreen('sell')}
                      className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-sm active:scale-95 transition-all"
                    >
                      💰 SELL NUMBER
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => alert("Displays user orders: Order ID, Country, Service, Status, and Date")}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      📦 MY ORDERS
                    </button>
                    <button
                      onClick={() => alert("Displays seller listings: Pending, Approved, Rejected, Sold")}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      📋 MY LISTINGS
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => setCurrentScreen('wallet')}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      💳 WALLET
                    </button>
                    <button
                      onClick={() => setCurrentScreen('wallet')}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      💵 EARNINGS
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => {
                        const next = selectedCurrency === 'INR' ? 'USD' : 'INR';
                        setSelectedCurrency(next);
                      }}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      💱 CURRENCY ({selectedCurrency})
                    </button>
                    <button
                      onClick={() => alert("Displays Telegram ID, Username, Account Status & Registered Date")}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      👤 PROFILE
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      onClick={() => alert("Displays user analytics: Orders, Sales, Earnings, and Spending")}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      📊 STATISTICS
                    </button>
                    <button
                      onClick={() => alert("Displays support contact from SUPPORT_USERNAME environment variable")}
                      className="py-2 px-3 bg-slate-800/80 hover:bg-slate-700 text-slate-300 font-medium rounded-xl text-xs flex items-center justify-center gap-1.5"
                    >
                      ❓ SUPPORT
                    </button>
                  </div>

                  {isAdminMode && (
                    <button
                      onClick={() => setCurrentScreen('admin')}
                      className="w-full py-2 px-3 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 font-semibold rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      🛠 ADMIN PANEL
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: PROJECT FILES VIEWER */}
        {activeTab === 'files' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 space-y-2">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Project Modules</h3>
              {projectFiles.map((file) => (
                <button
                  key={file.name}
                  onClick={() => setSelectedFile(file.name)}
                  className={`w-full p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                    selectedFile === file.name
                      ? 'bg-blue-600/10 border-blue-500 text-white'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <FileCode className={`w-4 h-4 ${selectedFile === file.name ? 'text-blue-400' : 'text-slate-500'}`} />
                    <div>
                      <p className="text-xs font-semibold text-white font-mono">{file.name}</p>
                      <p className="text-[11px] text-slate-400">{file.desc}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">{file.size}</span>
                </button>
              ))}
            </div>

            <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                <div className="flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-blue-400" />
                  <span className="font-mono text-sm font-semibold text-white">{selectedFile}</span>
                </div>
                <button
                  onClick={() => copyToClipboard(`File: ${selectedFile}`, selectedFile)}
                  className="flex items-center gap-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
                >
                  {copiedKey === selectedFile ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedKey === selectedFile ? 'Copied' : 'Copy Name'}</span>
                </button>
              </div>

              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 leading-relaxed overflow-x-auto">
                {selectedFile === 'app.py' && (
                  <pre>{`from fastapi import FastAPI, Request, HTTPException, status
import uvicorn
from contextlib import asynccontextmanager
from database import init_db, fulfill_order_and_credit_seller
from bot import build_telegram_application, notify_user_order_fulfilled
from payments import payment_provider

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite tables
    init_db()
    # 2. Boot Telegram Bot polling in background
    app.state.bot_app = build_telegram_application()
    await app.state.bot_app.initialize()
    await app.state.bot_app.start()
    await app.state.bot_app.updater.start_polling()
    yield
    # 3. Clean shutdown
    await app.state.bot_app.updater.stop()
    await app.state.bot_app.stop()
    await app.state.bot_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/webhooks/whop")
async def whop_webhook(request: Request):
    # Raw bytes verification & deduplication
    ...`}</pre>
                )}
                {selectedFile === 'models.py' && (
                  <pre>{`class Number(Base):
    __tablename__ = "numbers"
    id = Column(Integer, primary_key=True)
    number = Column(String(64), nullable=False, index=True)
    country = Column(String(64), nullable=False, index=True)
    service = Column(String(64), nullable=False, index=True)
    price_inr = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(32), default="available", index=True)

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(64), unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False)
    payment_status = Column(String(32), default="pending")
    order_status = Column(String(32), default="pending")`}</pre>
                )}
                {selectedFile === 'payments.py' && (
                  <pre>{`class WhopPaymentProvider:
    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        # Constant-time comparison preventing timing attacks
        # Supports standard 't=timestamp,v1=sig' format & direct HMAC-SHA256
        expected = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_header)`}</pre>
                )}
                {selectedFile !== 'app.py' && selectedFile !== 'models.py' && selectedFile !== 'payments.py' && (
                  <div className="text-slate-400 py-6 text-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                    <p className="font-semibold text-white">Full Source File Created</p>
                    <p className="text-xs text-slate-400 mt-1">This file has been created at root <code>/{selectedFile}</code> with complete runnable logic.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: ARCHITECTURE */}
        {activeTab === 'architecture' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-2">Unified Render Web Service Architecture</h2>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                FastAPI and Python-Telegram-Bot run concurrently within the same container. No auxiliary background worker or Redis is required.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm mb-2">
                    <Smartphone className="w-4 h-4" /> Telegram Client Layer
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Provides clean ReplyKeyboardMarkup and inline contextual menus for browsing, buying, listing, and wallet operations.
                  </p>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm mb-2">
                    <Server className="w-4 h-4" /> FastAPI + Webhook Server
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Hosts <code className="text-cyan-300">GET /health</code> for Render keep-alive and <code className="text-cyan-300">POST /webhooks/whop</code> for cryptographic payment verification.
                  </p>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm mb-2">
                    <Database className="w-4 h-4" /> Atomic SQLite Engine
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Row-level isolation prevents race conditions. Numbers transition safely: <code className="text-slate-300">available → reserved → sold</code>.
                  </p>
                </div>
              </div>
            </div>

            {/* Safety & Compliance Card */}
            <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-2xl p-6">
              <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2 mb-2">
                <ShieldCheck className="w-5 h-5" /> Strict Compliance & Safety Scope
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                This software is engineered solely for testing authorized virtual numbers and SMS sandbox integrations. It contains zero mechanisms for OTP sniffing, SIM swapping, Telegram account activation, or unauthorized credential access.
              </p>
            </div>
          </div>
        )}

        {/* TAB 4: WHOP WEBHOOK SPECIFICATION */}
        {activeTab === 'webhook' && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div>
              <h2 className="text-base font-bold text-white mb-1">Whop Payments Webhook Protocol</h2>
              <p className="text-xs text-slate-400">
                Incoming webhook events are authenticated against <code className="text-cyan-300">WHOP_WEBHOOK_SECRET</code> using HMAC-SHA256.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <h4 className="font-semibold text-cyan-400">1. Verification Flow</h4>
                <p className="text-slate-400">
                  Extracts raw request body bytes and matches the header signature with constant-time equality check (<code className="text-slate-300">hmac.compare_digest</code>).
                </p>
              </div>

              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <h4 className="font-semibold text-cyan-400">2. Deduplication Protection</h4>
                <p className="text-slate-400">
                  Every <code className="text-slate-300">event_id</code> is recorded in <code className="text-slate-300">processed_events</code>. Repeated deliveries return HTTP 200 without double-fulfilling numbers.
                </p>
              </div>
            </div>

            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-slate-300">
              <div className="text-slate-500 mb-1">// Sample Webhook Payload</div>
              <pre>{JSON.stringify({
                action: "payment.succeeded",
                data: {
                  id: "pay_98234712",
                  amount: 19900,
                  currency: "inr",
                  metadata: {
                    order_id: "ORD-A8B9C2D1",
                    user_id: "12345678"
                  }
                }
              }, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* TAB 5: DEPLOYMENT GUIDE */}
        {activeTab === 'deploy' && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-2">Deploy to Render (Web Service)</h2>
              <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                Render runs the application using the specification in <code className="text-cyan-300">render.yaml</code>.
              </p>

              <div className="space-y-4 text-xs">
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                  <p className="font-bold text-white">Start Command:</p>
                  <div className="p-2 bg-slate-900 rounded font-mono text-cyan-400">
                    uvicorn app:app --host 0.0.0.0 --port $PORT
                  </div>
                </div>

                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                  <p className="font-bold text-white">Environment Variables in Render Dashboard:</p>
                  
                  {/* Individual Account Highlight */}
                  <div className="p-3 bg-blue-950/30 border border-blue-500/30 rounded-lg text-xs space-y-1">
                    <p className="font-semibold text-blue-300">💡 Verified as an Individual (PAN Card / Personal ID)?</p>
                    <p className="text-slate-300 leading-relaxed">
                      Whop assigns a <code className="text-amber-300 font-mono">biz_...</code> Store Identifier to all accounts (individual and business alike). No separate business tax ID, GSTIN, or corporate certificate is required! Find your ID in your dashboard URL (<code className="text-amber-300 font-mono">dash.whop.com/biz_...</code>) or leave it blank to let the bot auto-discover it with your API key.
                    </p>
                  </div>

                  <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono">
                    <li><strong className="text-slate-200">BOT_TOKEN</strong>: Telegram Bot token from @BotFather (Required)</li>
                    <li><strong className="text-slate-200">ADMIN_IDS</strong>: Comma-separated admin Telegram IDs (Required)</li>
                    <li><strong className="text-slate-200">WHOP_API_KEY</strong>: Whop API Key from Settings &gt; Developer (Required)</li>
                    <li><strong className="text-slate-200">WHOP_WEBHOOK_SECRET</strong>: Webhook signing secret from Whop (Required)</li>
                    <li><strong className="text-slate-200">WHOP_COMPANY_ID</strong>: <span className="text-amber-400 font-semibold">[Optional]</span> Your <code className="text-amber-300">biz_...</code> store ID from URL or auto-resolved</li>
                    <li><strong className="text-slate-200">DATABASE_URL</strong>: sqlite:///marketplace.db</li>
                    <li><strong className="text-slate-200">SUPPORT_USERNAME</strong>: Support Telegram handle without @</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 px-6 py-4 text-xs text-slate-500 text-center">
        Premium Virtual Number Marketplace • Python Telegram Bot + FastAPI Webhook Architecture
      </footer>
    </div>
  );
}
