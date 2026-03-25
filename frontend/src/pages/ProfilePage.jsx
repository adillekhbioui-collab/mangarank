import { useMemo } from 'react';
import { motion } from 'motion/react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWatchlist } from '../hooks/useWatchlist';

const STATUS_LABELS = {
    want_to_read: 'Want to Read',
    reading: 'Reading',
    completed: 'Completed',
    dropped: 'Dropped',
};

const STATUS_COLORS = {
    want_to_read: 'var(--watchlist-want)',
    reading: 'var(--watchlist-reading)',
    completed: 'var(--watchlist-done)',
    dropped: 'var(--watchlist-drop)',
};

export default function ProfilePage() {
    const { user, isAuthLoading } = useAuth();
    const { watchlist, grouped, totalCount } = useWatchlist();

    const joinDate = useMemo(() => {
        if (!user?.created_at) return 'Unknown';
        return new Date(user.created_at).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }, [user]);

    const handleExportCSV = () => {
        const headers = ['Title', 'Status', 'Date Added'];
        const rows = Object.values(watchlist).map(entry => {
            // Escape quotes and commas in titles
            const safeTitle = `"${entry.title.replace(/"/g, '""')}"`;
            return [
                safeTitle,
                STATUS_LABELS[entry.status],
                new Date(entry.added_at).toLocaleDateString()
            ].join(',');
        });

        const csvContent = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'manhwarank_watchlist.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (isAuthLoading) {
        return (
            <div className="admin-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
                <div className="admin-loading" style={{ color: 'var(--text-primary)' }}>Loading Profile...</div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/" replace />;
    }

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px 20px', minHeight: '100vh' }}>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="profile-header"
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '24px',
                    background: 'var(--bg-secondary)',
                    padding: '32px',
                    borderRadius: '16px',
                    border: '1px solid var(--border)',
                    marginBottom: '32px'
                }}
            >
                <img
                    src={user.user_metadata?.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.email)}`}
                    alt="Avatar"
                    style={{ width: '96px', height: '96px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--border)' }}
                />
                <div>
                    <h1 style={{ fontSize: '28px', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
                        {user.user_metadata?.full_name || user.email.split('@')[0]}
                    </h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '15px' }}>
                        Member since {joinDate}
                    </p>
                </div>
            </motion.div>

            <h2 style={{ fontSize: '22px', fontWeight: '700', marginBottom: '20px', color: 'var(--text-primary)' }}>Watchlist Overview</h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 }}
                    style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)' }}
                >
                    <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: '600' }}>Total Saved</div>
                    <div style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>{totalCount}</div>
                </motion.div>

                {Object.keys(STATUS_LABELS).map((statusKey, index) => {
                    const count = grouped[statusKey]?.length || 0;
                    return (
                        <motion.div
                            key={statusKey}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.1 + (index * 0.05) }}
                            style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)', borderTop: `4px solid ${STATUS_COLORS[statusKey]}` }}
                        >
                            <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: '600' }}>
                                {STATUS_LABELS[statusKey]}
                            </div>
                            <div style={{ fontSize: '32px', fontWeight: '800', color: 'var(--text-primary)' }}>{count}</div>
                        </motion.div>
                    );
                })}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    onClick={handleExportCSV}
                    style={{
                        background: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border)',
                        padding: '12px 24px',
                        borderRadius: '8px',
                        cursor: totalCount === 0 ? 'not-allowed' : 'pointer',
                        opacity: totalCount === 0 ? 0.5 : 1,
                        fontWeight: '600',
                        fontSize: '15px',
                        transition: 'background 0.2s ease'
                    }}
                    disabled={totalCount === 0}
                >
                    ⬇️ Export List as CSV
                </button>
            </div>
        </div>
    );
}
