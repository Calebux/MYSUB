import { useState, useEffect } from 'react';
import { Download, Bell, Send, CheckCircle2 } from 'lucide-react';
import { apiFetch } from '../api';

export default function ActionsStep({ report, goBack }: { report: any, goBack: () => void }) {
    const [tgToken, setTgToken] = useState('');
    const [tgChatId, setTgChatId] = useState('');
    const [tgSaved, setTgSaved] = useState(false);
    const [tgSaving, setTgSaving] = useState(false);
    const [tgError, setTgError] = useState('');
    const [tgTesting, setTgTesting] = useState(false);
    const [tgTestMsg, setTgTestMsg] = useState('');

    // Load existing config on mount
    useEffect(() => {
        apiFetch('/api/alerts/config')
            .then(r => r.json())
            .then(data => {
                if (data.telegram_chat_id) setTgChatId(data.telegram_chat_id);
                if (data.telegram_configured) setTgSaved(true);
            })
            .catch(() => {});
    }, []);

    const handleSaveTelegram = async () => {
        if (!tgToken.trim() || !tgChatId.trim()) {
            setTgError('Please enter both Bot Token and Chat ID.');
            return;
        }
        setTgSaving(true);
        setTgError('');
        try {
            const res = await apiFetch('/api/alerts/config', {
                method: 'POST',
                body: JSON.stringify({
                    telegram_token: tgToken.trim(),
                    telegram_chat_id: tgChatId.trim(),
                }),
            });
            const data = await res.json();
            if (data.status === 'success') {
                setTgSaved(true);
            } else {
                setTgError(data.message || 'Failed to save.');
            }
        } catch {
            setTgError('Network error.');
        } finally {
            setTgSaving(false);
        }
    };

    const handleTestTelegram = async () => {
        setTgTesting(true);
        setTgTestMsg('');
        try {
            const res = await apiFetch('/api/alerts/test', { method: 'POST' });
            const data = await res.json();
            setTgTestMsg(data.status === 'success' ? '✓ Test message sent!' : '✗ ' + (data.message || 'Failed'));
        } catch {
            setTgTestMsg('✗ Network error.');
        } finally {
            setTgTesting(false);
        }
    };

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
                    <div className="w-full">
                        <div className="w-10 h-10 bg-blue-50 text-blue-500 rounded-xl flex items-center justify-center mb-4">
                            <Send className="w-5 h-5" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 mb-2">Telegram Alerts</h3>
                        <p className="text-sm text-gray-500 leading-relaxed mb-4">
                            Get notified on Telegram 3 days before any subscription renews.
                        </p>

                        {tgError && (
                            <p className="text-red-500 text-xs mb-3">{tgError}</p>
                        )}
                        {tgTestMsg && (
                            <p className={`text-xs mb-3 font-semibold ${tgTestMsg.startsWith('✓') ? 'text-emerald-600' : 'text-red-500'}`}>{tgTestMsg}</p>
                        )}

                        <div className="w-full space-y-3">
                            <input
                                type="text"
                                placeholder="Bot Token"
                                value={tgToken}
                                onChange={e => { setTgToken(e.target.value); setTgSaved(false); }}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 outline-none"
                            />
                            <input
                                type="text"
                                placeholder="Chat ID"
                                value={tgChatId}
                                onChange={e => { setTgChatId(e.target.value); setTgSaved(false); }}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500 outline-none"
                            />
                            <button
                                onClick={handleSaveTelegram}
                                disabled={tgSaving}
                                className={`w-full py-2.5 font-semibold rounded-xl transition-all flex justify-center items-center ${tgSaved ? 'bg-emerald-500 text-white' : 'bg-slate-900 text-white hover:bg-slate-800'} disabled:opacity-50`}
                            >
                                {tgSaved ? <><CheckCircle2 className="w-4 h-4 mr-2" /> Saved</> : tgSaving ? 'Saving...' : 'Save Telegram Config'}
                            </button>
                            {tgSaved && (
                                <button
                                    onClick={handleTestTelegram}
                                    disabled={tgTesting}
                                    className="w-full py-2 border border-blue-200 text-blue-600 text-sm font-semibold rounded-xl hover:bg-blue-50 transition-all disabled:opacity-50"
                                >
                                    {tgTesting ? 'Sending...' : 'Send Test Message'}
                                </button>
                            )}
                        </div>
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
                        <button className="w-full py-2.5 font-semibold rounded-xl transition-all flex justify-center items-center bg-[#25D366] text-white hover:bg-[#1ebd5a]">
                            Open WhatsApp
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
