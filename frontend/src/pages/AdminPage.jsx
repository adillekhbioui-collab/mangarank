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
        <div className="admin-gate-shell">
            <div className="admin-gate-card">
                <div className="admin-gate-title">Admin Access</div>
                <div className="admin-gate-subtitle">Enter the backend admin password.</div>
                <input
                    type="password"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === 'Enter' && !isValidating) handleEnter();
                    }}
                    className="admin-gate-input"
                    placeholder="Admin password"
                    disabled={isValidating}
                />
                {error ? <div className="admin-gate-error">{error}</div> : null}
                <button className="admin-gate-btn" onClick={handleEnter} disabled={isValidating}>
                    {isValidating ? 'Verifying...' : 'Enter Control Room'}
                </button>
            </div>
        </div>
    );
}
