import { useState, useEffect } from 'react';

export default function ScanningStep({ onComplete, onCancel }: { onComplete: () => void, onCancel: () => void }) {
    const [progress, setProgress] = useState({ current: 0, total: 100, status: 'Scanning your inbox...' });
    const [logs, setLogs] = useState<string[]>([]);

    useEffect(() => {
        // Poll the backend for parsing progress
        const interval = setInterval(async () => {
            try {
                const res = await fetch("/api/progress");
                const data = await res.json();

                if (data.status === "done") {
                    clearInterval(interval);
                    onComplete();
                } else if (data.status === "error") {
                    clearInterval(interval);
                    alert("Scan Error: " + data.message);
                    onCancel();
                } else {
                    setProgress({
                        current: data.processed,
                        total: data.total || 100,
                        status: 'Scanning your inbox...'
                    });
                    if (data.recent_log) {
                        setLogs(prev => [...prev.slice(-4), data.recent_log]);
                    }
                }
            } catch (err) {
                console.error(err);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [onComplete, onCancel]);

    const pct = Math.min(100, Math.round((progress.current / progress.total) * 100)) || 0;

    const handleCancel = async () => {
        try {
            await fetch("/api/cancel", { method: "POST" });
        } catch (e) { }
        onCancel();
    }

    return (
        <div className="max-w-xl mx-auto mt-20 text-center">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-10">

                {/* Animated Spinner matching syncro */}
                <div className="flex justify-center mb-6">
                    <div className="w-12 h-12 border-4 border-gray-200 border-t-yellow-500 rounded-full animate-spin"></div>
                </div>

                <h2 className="text-xl font-bold text-slate-900 mb-2">{progress.status}</h2>
                <p className="text-sm font-medium text-gray-500 mb-8">
                    {progress.current} of {progress.total} emails processed &middot; {pct}%
                </p>

                {/* Progress bar line */}
                <div className="w-full bg-gray-100 rounded-full h-2.5 mb-8 overflow-hidden">
                    <div
                        className="bg-yellow-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                        style={{ width: `${pct}%` }}
                    ></div>
                </div>

                {/* Console Box */}
                <div className="bg-slate-900 text-left rounded-xl p-4 h-32 overflow-y-auto border border-slate-800 mb-8">
                    <div className="font-mono text-xs text-emerald-400 space-y-1">
                        {logs.length === 0 ? '> Establishing secure IMAP connection...' : logs.map((l, i) => (
                            <div key={i}>{l}</div>
                        ))}
                    </div>
                </div>

                <button
                    onClick={handleCancel}
                    className="text-sm font-semibold text-slate-500 hover:text-red-500 transition-colors"
                >
                    Cancel Scan
                </button>
            </div>
        </div>
    );
}
