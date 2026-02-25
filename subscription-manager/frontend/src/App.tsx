import { useState, useEffect } from 'react';
import { apiFetch } from './api';
import ConnectStep from './components/ConnectStep';
import ScanningStep from './components/ScanningStep';
import ActionsStep from './components/ActionsStep';
import AddSubscriptionModal from './components/AddSubscriptionModal';
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  Plus,
  ExternalLink,
  Heart,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

// Currency symbol helper
const currencySymbol = (code: string) => {
  const map: Record<string, string> = { USD: '$', NGN: '₦', EUR: '€', GBP: '£' };
  return map[code] || code + ' ';
};
const fmt = (amount: number, currency: string = 'USD') =>
  `${currencySymbol(currency)}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// --- Types ---
interface Report {
  merchant_count: number;
  upcoming_renewals_30d: any[];
  spend_by_currency: Record<string, number>;
  total_monthly_spend: number;
  merchants: any[];
  overlaps: any[];
}
function App() {
  const [step, setStep] = useState(1);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [markedForCancel, setMarkedForCancel] = useState<Set<string>>(new Set());
  const [healthScores, setHealthScores] = useState<any[]>([]);

  // Silently obtain auth token on startup so all API calls work
  useEffect(() => {
    if (!localStorage.getItem('subtrack_token')) {
      fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: 'subtrack' }),
      })
        .then(r => r.json())
        .then(d => { if (d.token) localStorage.setItem('subtrack_token', d.token); })
        .catch(() => {});
    }
  }, []);

  const fetchReport = () => {
    setLoading(true);
    apiFetch('/api/report')
      .then(res => res.json())
      .then(data => {
        if (!data.error) {
          setReport(data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch report", err);
        setLoading(false);
      });
  };

  const fetchHealthScores = () => {
    apiFetch('/api/health-score')
      .then(res => res.json())
      .then(data => setHealthScores(data.subscriptions || []))
      .catch(err => console.error('Failed to fetch health scores', err));
  };

  const toggleCancelMark = (merchant: string) => {
    const newMarked = new Set(markedForCancel);
    const shouldMark = !newMarked.has(merchant);
    if (shouldMark) newMarked.add(merchant);
    else newMarked.delete(merchant);
    setMarkedForCancel(newMarked);
    apiFetch('/api/cancellation/mark', {
      method: 'POST',
      body: JSON.stringify({ merchant, mark: shouldMark }),
    }).catch(console.error);
  };

  // If we directly jump to Step 3 and don't have a report, try fetching
  useEffect(() => {
    if (step === 3 && !report) {
      fetchReport();
    }
    if (step === 3) {
      fetchHealthScores();
    }
  }, [step]);

  // --- Render Steps ---
  if (step === 1) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
        <header className="p-6 flex items-center justify-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-yellow-500 flex items-center justify-center font-bold text-slate-900 shadow-md text-lg">S</div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">SubTrack</h1>
            <p className="text-xs text-gray-500 font-medium">Subscription intelligence</p>
          </div>
        </header>

        {/* Wizard Progress Bar */}
        <div className="max-w-xl mx-auto w-full px-4 mb-2">
          <div className="flex items-center justify-between bg-white p-1 rounded-xl border border-gray-200 shadow-sm">
            {['1 · Connect', '2 · Scanning', '3 · Results', '4 · Actions'].map((label, i) => (
              <button key={i} onClick={() => setStep(i + 1)} className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold cursor-pointer transition-colors ${step === i + 1 ? 'bg-slate-900 text-yellow-500 shadow-md' : step > i + 1 ? 'text-slate-900 hover:bg-gray-100' : 'text-gray-400 hover:bg-gray-100'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <ConnectStep onConnect={() => setStep(2)} />
      </div>
    );
  }

  if (step === 2) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
        <header className="p-6 flex items-center justify-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-yellow-500 flex items-center justify-center font-bold text-slate-900 shadow-md text-lg">S</div>
          <div><h1 className="text-xl font-bold text-slate-900 tracking-tight">SubTrack</h1></div>
        </header>
        <div className="max-w-xl mx-auto w-full px-4 mb-2">
          <div className="flex items-center justify-between bg-white p-1 rounded-xl border border-gray-200 shadow-sm">
            {['1 · Connect', '2 · Scanning', '3 · Results', '4 · Actions'].map((label, i) => (
              <div key={i} className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold ${step === i + 1 ? 'bg-slate-900 text-yellow-500 shadow-md' : step > i + 1 ? 'text-slate-900' : 'text-gray-400'}`}>
                {label}
              </div>
            ))}
          </div>
        </div>

        <ScanningStep onComplete={() => setStep(3)} onCancel={() => setStep(1)} />
      </div>
    );
  }

  if (step === 4) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
        <header className="p-6 flex items-center justify-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-yellow-500 flex items-center justify-center font-bold text-slate-900 shadow-md text-lg">S</div>
          <div><h1 className="text-xl font-bold text-slate-900 tracking-tight">SubTrack</h1></div>
        </header>
        <div className="max-w-xl mx-auto w-full px-4 mb-2">
          <div className="flex items-center justify-between bg-white p-1 rounded-xl border border-gray-200 shadow-sm">
            {['1 · Connect', '2 · Scanning', '3 · Results', '4 · Actions'].map((label, i) => (
              <div key={i} className={`flex-1 text-center py-2 rounded-lg text-xs font-semibold ${step === i + 1 ? 'bg-slate-900 text-yellow-500 shadow-md' : step > i + 1 ? 'text-slate-900' : 'text-gray-400'}`}>
                {label}
              </div>
            ))}
          </div>
        </div>

        <ActionsStep report={report} goBack={() => setStep(3)} />
      </div>
    );
  }

  // --- Step 3: Default Dashboard UI ---


  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 text-slate-900 font-semibold">
        <div className="flex flex-col items-center">
          <div className="w-8 h-8 rounded-lg bg-yellow-500 flex items-center justify-center font-bold text-slate-900 mb-4 animate-bounce">
            S
          </div>
          Loading Dashboard...
        </div>
      </div>
    );
  }

  // Derived mock data if report is empty or for charts
  const merchantList = report?.merchants || [];
  const activeCount = report?.merchant_count || 0;
  const renewals = report?.upcoming_renewals_30d || [];
  const overlapsCount = report?.overlaps?.length || 0;
  const spendByCurrency = report?.spend_by_currency || {};

  // Group monthly cost by category for a meaningful chart
  const categorySpend: Record<string, number> = {};
  if (report?.merchants) {
    report.merchants.forEach(m => {
      const cat = m.category || 'Other';
      categorySpend[cat] = (categorySpend[cat] || 0) + m.monthly_cost;
    });
  }
  const chartData = Object.entries(categorySpend).map(([name, spend]) => ({
    name: name.length > 10 ? name.substring(0, 10) + '...' : name,
    spend: Number(spend.toFixed(2))
  })).sort((a, b) => b.spend - a.spend); // Highest spend first

  return (
    <div className="flex flex-col h-screen bg-gray-50 font-sans text-slate-800">
      {/* Header with Navigation - Top Bar instead of Sidebar */}
      <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center space-x-4">
          {/* Logo mini version */}
          <div className="w-8 h-8 rounded-lg bg-yellow-500 flex items-center justify-center font-bold text-slate-900 shadow-sm text-sm mr-2">S</div>
          <div className="flex items-center text-gray-900 font-bold text-lg tracking-tight mr-6">
            SubTrack
          </div>

          {/* Render Navigation state up here */}
          <div className="hidden sm:flex items-center space-x-1 bg-gray-50 border border-gray-200 rounded-lg p-1">
            {['Connect', 'Scan', 'Results', 'Actions'].map((label, i) => (
              <button
                key={i}
                onClick={() => setStep(i + 1)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${step === i + 1 ? 'bg-slate-900 text-yellow-500 shadow-sm' : 'text-gray-500 hover:text-slate-900 hover:bg-white'}`}
              >
                {i + 1}. {label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end space-x-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-1.5 border border-gray-200 text-gray-700 font-semibold text-sm rounded-lg hover:bg-gray-50 transition-colors flex items-center shadow-sm"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Add
          </button>
          <button
            onClick={() => setStep(4)}
            className="px-4 py-1.5 bg-slate-900 text-white font-semibold text-sm rounded-lg hover:bg-slate-800 transition-colors flex items-center shadow-sm"
          >
            Take Action &rarr;
          </button>
        </div>
      </header>

      {/* Add Subscription Modal */}
      {showAddModal && (
        <AddSubscriptionModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => { fetchReport(); fetchHealthScores(); }}
        />
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto p-4">
        <div className="max-w-7xl mx-auto space-y-4">

          {/* Top Stats Row (Shrunk) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Stat Card 1 */}
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="text-xs font-semibold text-gray-500 tracking-wide uppercase mb-0.5">Total Monthly Spend</p>
                  <div>
                    {Object.entries(spendByCurrency).map(([cur, amount]) => (
                      <h3 key={cur} className="text-2xl font-bold text-slate-900 tracking-tight">
                        {fmt(amount as number, cur)}<span className="text-gray-400 text-xs font-normal ml-1">/mo</span>
                      </h3>
                    ))}
                    {Object.keys(spendByCurrency).length === 0 && (
                      <h3 className="text-2xl font-bold text-slate-900 tracking-tight">$0.00</h3>
                    )}
                  </div>
                </div>
                <div className="p-1.5 bg-slate-50 text-slate-600 rounded-md flex items-center">
                  <Activity className="w-3.5 h-3.5 mr-1" />
                  <span className="text-[10px] font-semibold">Est.</span>
                </div>
              </div>
            </div>

            {/* Stat Card 2 */}
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-yellow-50 rounded-full translate-x-1/2 -translate-y-1/2 blur-2xl"></div>
              <div className="relative">
                <div className="flex justify-between items-start mb-1">
                  <div>
                    <p className="text-xs font-semibold text-gray-500 tracking-wide uppercase mb-0.5">Active Subscriptions</p>
                    <h3 className="text-2xl font-bold text-slate-900 tracking-tight">{activeCount}</h3>
                  </div>
                </div>
                <div className="mt-2 flex items-center text-xs font-medium text-emerald-600">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> {renewals.length} renewals upcoming
                </div>
              </div>
            </div>

            {/* Stat Card 3 (Actionable) */}
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 shadow-md text-white flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-1.5 text-yellow-500 mb-1">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-[10px] font-bold tracking-wider uppercase">Optimization</span>
                </div>
                <h3 className="text-sm font-bold leading-tight mb-1">{overlapsCount > 0 ? `${overlapsCount} Potential Savings Found` : 'No Savings Found'}</h3>
                <p className="text-slate-400 text-xs">
                  {overlapsCount > 0 ? `We detected overlapping subscriptions.` : `Subscriptions look optimized.`}
                </p>
              </div>
              <button
                className={`mt-2 w-full font-semibold py-1.5 rounded-lg text-xs transition-colors ${overlapsCount > 0 ? 'bg-yellow-500 hover:bg-yellow-400 text-slate-900' : 'bg-slate-800 text-slate-400 cursor-not-allowed'}`}
                disabled={overlapsCount === 0}
              >
                Review Duplicates
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Chart Section */}
            <div className="md:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Spending Trend</h3>
                <select className="bg-gray-50 border border-gray-200 text-gray-600 text-xs rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-yellow-500/50">
                  <option>Last 6 Months</option>
                </select>
              </div>
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData.length > 0 ? chartData : [{ name: 'No Data', spend: 0 }]} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#EAB308" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#EAB308" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 10 }} dy={5} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6B7280', fontSize: 10 }} tickFormatter={(value) => `$${value}`} dx={-5} />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', padding: '4px 8px' }}
                      itemStyle={{ color: '#0F172A', fontWeight: 600, fontSize: '12px' }}
                      formatter={(value) => [`$${value}`, 'Spend']}
                      labelStyle={{ fontSize: '11px', color: '#6B7280' }}
                    />
                    <Area type="monotone" dataKey="spend" stroke="#0F172A" strokeWidth={2} fillOpacity={1} fill="url(#colorSpend)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent Activity / Renewals */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">Upcoming Renewals</h3>
                <button className="text-yellow-600 text-[10px] uppercase tracking-wider font-bold hover:text-yellow-700">View All</button>
              </div>
              <div className="flex-1 space-y-3">
                {renewals.slice(0, 4).map((item: any, i: number) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${item.days_until < 4 ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-600 border border-slate-200'}`}>
                        {item.merchant.charAt(0)}
                      </div>
                      <div>
                        <p className={`text-xs font-semibold ${item.days_until < 4 ? 'text-red-600' : 'text-slate-900'}`}>{item.merchant}</p>
                        <p className="text-[10px] text-gray-500">in {item.days_until} days</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-slate-900">{fmt(item.amount, item.currency)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Subscriptions Table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <h3 className="text-base font-bold text-slate-900 tracking-tight">Active Subscriptions</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-white border-b border-gray-100 text-xs font-semibold text-gray-500 tracking-wide uppercase">
                  <tr>
                    <th className="px-4 py-2 w-8"></th>
                    <th className="px-4 py-2">Service</th>
                    <th className="px-4 py-2">Category</th>
                    <th className="px-4 py-2">Cost</th>
                    <th className="px-4 py-2">Health</th>
                    <th className="px-4 py-2">Next Billing</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {merchantList.map((sub: any, idx: number) => {
                    const hs = healthScores.find((h: any) => h.merchant === sub.merchant);
                    const isMarked = markedForCancel.has(sub.merchant);
                    return (
                      <tr key={idx} className={`transition-colors group ${isMarked ? 'bg-red-50/50' : 'hover:bg-slate-50'}`}>
                        {/* Cancellation checkbox */}
                        <td className="px-4 py-2.5">
                          <input
                            type="checkbox"
                            checked={isMarked}
                            onChange={() => toggleCancelMark(sub.merchant)}
                            className="w-4 h-4 rounded border-gray-300 text-red-500 focus:ring-red-500/30 cursor-pointer"
                            title={isMarked ? 'Unmark for cancellation' : 'Mark for cancellation'}
                          />
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center space-x-3">
                            <span className={`font-semibold text-sm ${isMarked ? 'text-red-600 line-through' : 'text-slate-900'}`}>{sub.merchant}</span>
                            {sub.source === 'manual' && <span className="text-[10px] bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded font-semibold">MANUAL</span>}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-gray-500 text-xs">{sub.category || 'Subscription'}</td>
                        <td className="px-4 py-2.5 font-bold text-slate-900 text-sm">{fmt(sub.monthly_cost, sub.currency)}<span className="text-gray-400 font-normal text-xs">/mo</span></td>
                        {/* Health score */}
                        <td className="px-4 py-2.5">
                          {hs ? (
                            <div className="flex items-center space-x-1" title={hs.tips?.join('\n') || 'No issues'}>
                              {hs.score >= 75 ? <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> :
                                hs.score >= 50 ? <ShieldQuestion className="w-3.5 h-3.5 text-yellow-500" /> :
                                  <ShieldAlert className="w-3.5 h-3.5 text-red-500" />}
                              <span className={`text-xs font-semibold ${hs.score >= 75 ? 'text-emerald-600' :
                                hs.score >= 50 ? 'text-yellow-600' :
                                  'text-red-600'
                                }`}>{hs.score}</span>
                            </div>
                          ) : (
                            <span className="text-gray-300 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-gray-500 text-xs">{sub.next_renewal || '-'}</td>
                        {/* Cancel link */}
                        <td className="px-4 py-2.5">
                          {isMarked && (
                            <a
                              href={`/api/cancellation`}
                              onClick={(e) => {
                                e.preventDefault();
                                apiFetch('/api/cancellation')
                                  .then(r => r.json())
                                  .then(data => {
                                    const s = data.subscriptions?.find((x: any) => x.merchant === sub.merchant);
                                    if (s?.cancel_url) window.open(s.cancel_url, '_blank');
                                  });
                              }}
                              className="text-red-500 hover:text-red-700 transition-colors"
                              title="Open cancellation page"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* Cancel summary bar */}
            {markedForCancel.size > 0 && (
              <div className="px-4 py-3 bg-red-50 border-t border-red-100 flex items-center justify-between">
                <div className="text-sm">
                  <span className="font-semibold text-red-600">{markedForCancel.size} subscription{markedForCancel.size !== 1 ? 's' : ''} marked</span>
                  <span className="text-red-400 ml-2">
                    Save {fmt(
                      merchantList.filter((m: any) => markedForCancel.has(m.merchant)).reduce((sum: number, m: any) => sum + m.monthly_cost, 0),
                      'USD'
                    )}/mo
                  </span>
                </div>
                <button
                  onClick={() => setStep(4)}
                  className="px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded-lg hover:bg-red-700 transition-colors"
                >
                  Cancel These →
                </button>
              </div>
            )}
          </div>

          {/* Health Score Summary */}
          {healthScores.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Heart className="w-4 h-4 text-red-500" />
                  <h3 className="text-base font-bold text-slate-900 tracking-tight">Subscription Health</h3>
                </div>
                <div className="flex items-center space-x-3 text-[10px] font-semibold">
                  <span className="flex items-center space-x-1"><ShieldCheck className="w-3 h-3 text-emerald-500" /><span className="text-emerald-600">75+ Healthy</span></span>
                  <span className="flex items-center space-x-1"><ShieldQuestion className="w-3 h-3 text-yellow-500" /><span className="text-yellow-600">50+ Fair</span></span>
                  <span className="flex items-center space-x-1"><ShieldAlert className="w-3 h-3 text-red-500" /><span className="text-red-600">&lt;50 Review</span></span>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {healthScores.map((hs: any, i: number) => (
                  <div key={i} className={`flex items-center justify-between p-2.5 rounded-lg border ${hs.score >= 75 ? 'border-emerald-200 bg-emerald-50/50' :
                    hs.score >= 50 ? 'border-yellow-200 bg-yellow-50/50' :
                      'border-red-200 bg-red-50/50'
                    }`}>
                    <div className="flex items-center space-x-2 min-w-0">
                      {hs.score >= 75 ? <ShieldCheck className="w-4 h-4 text-emerald-500 flex-shrink-0" /> :
                        hs.score >= 50 ? <ShieldQuestion className="w-4 h-4 text-yellow-500 flex-shrink-0" /> :
                          <ShieldAlert className="w-4 h-4 text-red-500 flex-shrink-0" />}
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-900 truncate">{hs.merchant}</p>
                        {hs.tips?.length > 0 && (
                          <p className="text-[10px] text-gray-500 truncate">{hs.tips[0]}</p>
                        )}
                      </div>
                    </div>
                    <span className={`text-sm font-bold flex-shrink-0 ml-2 ${hs.score >= 75 ? 'text-emerald-600' :
                      hs.score >= 50 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>{hs.score}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default App;
