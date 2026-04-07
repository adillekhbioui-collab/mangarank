import { useState } from 'react';
import AdminDashboard from '../components/admin/AdminDashboard.jsx';

const STORAGE_KEY = 'admin-auth-password';

export default function AdminPage() {
    const [adminPassword, setAdminPassword] = useState(() => sessionStorage.getItem(STORAGE_KEY) || '');
    const [isValidating, setIsValidating] = useState(false);
    const [input, setInput] = useState('');
    const [error, setError] = useState('');

    const handleEnter = async () => {
        const trimmed = input.trim();
        if (!trimmed) {
            setError('Password is required.');
            return;
        }

        setIsValidating(true);
        setError('');

        try {
            const res = await fetch(
                `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/admin/stats`,
                { headers: { 'X-Admin-Password': trimmed } }
            );

            if (res.ok) {
                sessionStorage.setItem(STORAGE_KEY, trimmed);
                setAdminPassword(trimmed);
                setInput('');
            } else if (res.status === 401) {
                setError('Incorrect password.');
            } else if (res.status === 503) {
                setError('Admin endpoints are not configured on the server.');
            } else {
                setError(`Server error (${res.status}). Try again.`);
            }
        } catch {
            setError('Cannot reach the server. Is the backend running?');
        } finally {
            setIsValidating(false);
        }
    };

    const handleLogout = () => {
        sessionStorage.removeItem(STORAGE_KEY);
        setAdminPassword('');
        setInput('');
        setError('');
    };

    if (adminPassword) {
        return <AdminDashboard adminPassword={adminPassword} onLogout={handleLogout} />;
    }

    return (
        <div className="min-h-screen bg-background text-text-primary flex items-center justify-center px-4">
            <div className="w-full max-w-md bg-elevated border border-border px-6 py-7 sm:px-8 sm:py-8">
                <div className="font-mono uppercase tracking-[0.18em] text-xs text-accent-red">Admin Access</div>
                <div className="mt-2 text-sm text-text-secondary">Enter the backend admin password.</div>
                <input
                    type="password"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === 'Enter' && !isValidating) handleEnter();
                    }}
                    className="mt-4 w-full bg-surface border border-border px-3 py-2 text-sm text-text-primary placeholder:text-text-ghost outline-none focus:border-accent-red"
                    placeholder="Admin password"
                    disabled={isValidating}
                />
                {error ? <div className="mt-3 text-sm text-accent-red">{error}</div> : null}
                <button
                    className="mt-5 w-full border border-accent-red bg-accent-red px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={handleEnter}
                    disabled={isValidating}
                >
                    {isValidating ? 'Verifying...' : 'Enter Control Room'}
                </button>
            </div>
        </div>
    );
}
