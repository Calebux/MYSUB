import { useState } from 'react';
import { Plus, X } from 'lucide-react';

interface Props {
    onClose: () => void;
    onAdded: () => void;
}

export default function AddSubscriptionModal({ onClose, onAdded }: Props) {
    const [merchant, setMerchant] = useState('');
    const [amount, setAmount] = useState('9.99');
    const [currency, setCurrency] = useState('USD');
    const [frequency, setFrequency] = useState('monthly');
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [error, setError] = useState('');
    const [saving, setSaving] = useState(false);

    const handleSubmit = async () => {
        if (!merchant.trim()) {
            setError('Please enter a service name.');
            return;
        }
        setSaving(true);
        setError('');
        try {
            const res = await fetch('/api/subscriptions/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    merchant: merchant.trim(),
                    amount: parseFloat(amount),
                    currency,
                    frequency,
                    date,
                }),
            });
            const data = await res.json();
            if (data.status === 'success') {
                onAdded();
                onClose();
            } else {
                setError(data.message || 'Failed to add subscription.');
            }
        } catch {
            setError('Network error. Is the API server running?');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 rounded-lg bg-yellow-500 flex items-center justify-center">
                            <Plus className="w-4 h-4 text-slate-900" />
                        </div>
                        <h2 className="text-lg font-bold text-slate-900">Add Subscription</h2>
                    </div>
                    <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                <p className="text-sm text-gray-500 mb-4">
                    Add subscriptions not found via email — gym, bank debits, Apple Pay, etc.
                </p>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm font-medium">
                        {error}
                    </div>
                )}

                {/* Form */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="col-span-2">
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Service Name</label>
                        <input
                            type="text"
                            value={merchant}
                            onChange={e => setMerchant(e.target.value)}
                            placeholder="e.g. Gym membership"
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-slate-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Amount</label>
                        <input
                            type="number"
                            value={amount}
                            onChange={e => setAmount(e.target.value)}
                            min="0.01"
                            step="0.01"
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Currency</label>
                        <select
                            value={currency}
                            onChange={e => setCurrency(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500"
                        >
                            <option value="USD">USD ($)</option>
                            <option value="NGN">NGN (₦)</option>
                            <option value="GBP">GBP (£)</option>
                            <option value="EUR">EUR (€)</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Billing Cycle</label>
                        <select
                            value={frequency}
                            onChange={e => setFrequency(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500"
                        >
                            <option value="monthly">Monthly</option>
                            <option value="yearly">Yearly</option>
                            <option value="quarterly">Quarterly</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Last Billing Date</label>
                        <input
                            type="date"
                            value={date}
                            onChange={e => setDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500"
                        />
                    </div>
                </div>

                {/* Actions */}
                <div className="flex space-x-3">
                    <button
                        onClick={handleSubmit}
                        disabled={saving}
                        className="flex-1 py-2.5 bg-slate-900 text-white font-semibold text-sm rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
                    >
                        {saving ? 'Adding...' : 'Add Subscription'}
                    </button>
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 border border-gray-200 text-gray-600 font-semibold text-sm rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
