import { useState } from 'react';
import { Download, Bell, Send, CheckCircle2 } from 'lucide-react';

export default function ActionsStep({ report, goBack }: { report: any, goBack: () => void }) {
    const [tgSaved, setTgSaved] = useState(false);
    const [waSaved, setWaSaved] = useState(false);

    const handleDownload = () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2));
        const dt = document.createElement('a');
        dt.setAttribute("href", dataStr);
        dt.setAttribute("download", "subscription_audit.json");
        dt.click();
    };

    return (
        <div className="max-w-4xl mx-auto p-8 space-y-8">

            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Export & Notifications</h2>
                <button onClick={goBack} className="text-sm font-semibold text-gray-500 hover:text-slate-900">
                    &larr; Back to Dashboard
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Export Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 flex flex-col items-start justify-between">
                    <div>
                        <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-700 mb-4">
                            <Download className="w-5 h-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 mb-2">Audit Report</h3>
                        <p className="text-sm text-gray-500 leading-relaxed mb-6">
                            Download the complete JSON audit file containing all your parsed subscriptions,
                            detected overlaps, and calculated costs.
                        </p>
                    </div>
                    <button
                        onClick={handleDownload}
                        className="px-5 py-2.5 bg-white border-2 border-slate-200 hover:border-slate-900 text-slate-900 font-semibold rounded-xl transition-all w-full text-center"
                    >
                        Download report.json
                    </button>
                </div>

                {/* Telegram Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 flex flex-col items-start justify-between">
                    <div>
                        <div className="w-10 h-10 bg-blue-50 text-blue-500 rounded-xl flex items-center justify-center mb-4">
                            <Send className="w-5 h-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 mb-2">Telegram Alerts</h3>
                        <p className="text-sm text-gray-500 leading-relaxed mb-6">
                            Get push notifications directly to Telegram 3 days before any subscription renews.
                        </p>
                    </div>

                    <div className="w-full space-y-3">
                        <input type="text" placeholder="Bot Token" className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 outline-none" />
                        <input type="text" placeholder="Chat ID" className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 outline-none" />
                        <button
                            onClick={() => setTgSaved(true)}
                            className={`w-full py-2.5 font-semibold rounded-xl transition-all flex justify-center items-center ${tgSaved ? 'bg-emerald-500 text-white' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                        >
                            {tgSaved ? <><CheckCircle2 className="w-4 h-4 mr-2" /> Saved</> : 'Save Telegram Config'}
                        </button>
                    </div>
                </div>

                {/* WhatsApp Card */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 flex flex-col items-start justify-between">
                    <div>
                        <div className="w-10 h-10 bg-emerald-50 text-emerald-500 rounded-xl flex items-center justify-center mb-4">
                            <Bell className="w-5 h-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 mb-2">WhatsApp Alerts</h3>
                        <p className="text-sm text-gray-500 leading-relaxed mb-6">
                            Open WhatsApp to send yourself a summary of your active subscriptions and renewals.
                        </p>
                    </div>

                    <div className="w-full space-y-3">
                        <input type="text" placeholder="+1234567890" className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 outline-none" />
                        <button
                            onClick={() => setWaSaved(true)}
                            className={`w-full py-2.5 font-semibold rounded-xl transition-all flex justify-center items-center ${waSaved ? 'bg-emerald-500 text-white' : 'bg-[#25D366] text-white hover:bg-[#1ebd5a]'}`}
                        >
                            Open WhatsApp
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
