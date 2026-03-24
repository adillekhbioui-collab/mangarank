import { useState } from 'react';
import AdminDashboard from '../components/admin/AdminDashboard.jsx';

const STORAGE_KEY = 'admin-auth-password';

export default function AdminPage() {
    const [adminPassword, setAdminPassword] = useState(() => sessionStorage.getItem(STORAGE_KEY) || '');
    const [input, setInput] = useState('');
    const [error, setError] = useState('');

    const handleEnter = () => {
        const trimmed = input.trim();
        if (!trimmed) {
            setError('Password is required.');
            return;
        }

        sessionStorage.setItem(STORAGE_KEY, trimmed);
        setAdminPassword(trimmed);
        setInput('');
        setError('');
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
                        if (event.key === 'Enter') handleEnter();
                    }}
                    className="admin-gate-input"
                    placeholder="Admin password"
                />
                {error ? <div className="admin-gate-error">{error}</div> : null}
                <button className="admin-gate-btn" onClick={handleEnter}>Enter Control Room</button>
            </div>
        </div>
    );
}
