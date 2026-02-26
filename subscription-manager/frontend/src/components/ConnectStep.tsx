import { useState } from 'react';
import { Mail, KeyRound, AlertCircle, ArrowRight } from 'lucide-react';
import { apiFetch } from '../api';

export default function ConnectStep({ onConnect }: { onConnect: () => void }) {
    const [email, setEmail] = useState('');
    const [appPassword, setAppPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email || !appPassword) {
            setError("Please provide both email and App Password.");
            return;
        }
        setLoading(true);
        try {
            const res = await apiFetch("/api/connect", {
                method: "POST",
                body: JSON.stringify({ email, password: appPassword })
            });
            const data = await res.json();
            if (data.status === "success") {
                onConnect();
            } else {
                setError(data.message || "Failed to connect.");
                setLoading(false);
            }
        } catch (err) {
            console.error(err);
            setError("Failed to reach server. Is the backend running?");
            setLoading(false);
        }
    };

    return (
        <div className="max-w-xl mx-auto mt-16">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Connect your inbox</h2>
                <p className="text-gray-500 text-sm mb-6">
                    We need read-only access to scan for subscription receipts.
                    Your credentials are only stored locally.
                </p>

                {error && (
                    <div className="mb-6 bg-red-50 text-red-700 p-4 rounded-xl text-sm font-medium border border-red-100 flex items-start">
                        <AlertCircle className="w-5 h-5 mr-2 shrink-0" />
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Gmail Address</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500 transition-all text-slate-900"
                                placeholder="you@gmail.com"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Google App Password</label>
                        <div className="relative">
                            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="password"
                                value={appPassword}
                                onChange={(e) => setAppPassword(e.target.value)}
                                className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500 transition-all text-slate-900"
                                placeholder="xxxx xxxx xxxx xxxx"
                            />
                        </div>
                        <p className="mt-2 text-xs text-gray-500">
                            You must use a 16-character App Password, not your regular Google password.
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full mt-6 bg-yellow-500 hover:bg-yellow-400 text-slate-900 font-bold py-3 rounded-xl transition-all shadow-sm flex items-center justify-center disabled:opacity-50"
                    >
                        {loading ? 'Connecting...' : 'Connect & Continue'}
                        {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
                    </button>
                </form>
            </div>

            <div className="mt-6 bg-slate-50 border border-slate-200 rounded-xl p-6 text-sm text-slate-600">
                <h3 className="font-bold text-slate-800 mb-2">How to get an App Password:</h3>
                <ol className="list-decimal pl-5 space-y-2">
                    <li>Go to your <a href="https://myaccount.google.com/security" target="_blank" className="text-yellow-600 font-semibold hover:underline">Google Security settings</a></li>
                    <li>Ensure <strong>2-Step Verification</strong> is enabled.</li>
                    <li>Search for <strong>App Passwords</strong> and create a new one.</li>
                    <li>Copy the 16-character code and paste it above.</li>
                </ol>
            </div>
        </div>
    );
}
