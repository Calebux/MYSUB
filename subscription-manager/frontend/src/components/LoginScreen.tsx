import { useState } from 'react';
import { Lock } from 'lucide-react';

interface Props {
    onAuth: (token: string) => void;
}

export default function LoginScreen({ onAuth }: Props) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!password.trim()) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password }),
            });
            const data = await res.json();
            if (data.status === 'success') {
                localStorage.setItem('subtrack_token', data.token);
                onAuth(data.token);
            } else {
                setError(data.message || 'Wrong password.');
            }
        } catch {
            setError('Cannot reach server.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center font-sans p-4">
            <div className="w-full max-w-sm">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="w-14 h-14 rounded-2xl bg-yellow-500 flex items-center justify-center font-bold text-slate-900 shadow-lg text-2xl mx-auto mb-3">S</div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">SubTrack</h1>
                    <p className="text-sm text-gray-500 mt-1">Subscription intelligence</p>
                </div>

                {/* Login card */}
                <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
                    <div className="flex items-center space-x-2 mb-4">
                        <Lock className="w-4 h-4 text-gray-400" />
                        <h2 className="text-sm font-semibold text-gray-600">Enter access password</h2>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm font-medium">
                            {error}
                        </div>
                    )}

                    <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="Password"
                        autoFocus
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-slate-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500 mb-4"
                    />

                    <button
                        type="submit"
                        disabled={loading || !password.trim()}
                        className="w-full py-3 bg-slate-900 text-white font-semibold text-sm rounded-xl hover:bg-slate-800 transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p className="text-center text-xs text-gray-400 mt-6">
                    Ask the host for the access password
                </p>
            </div>
        </div>
    );
}
