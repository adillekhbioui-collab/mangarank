import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '70vh',
            padding: '24px',
            textAlign: 'center',
            fontFamily: 'var(--font-data)'
        }}>
            <h1 style={{ fontSize: '6rem', margin: '0 0 16px 0', color: 'var(--text-primary)', fontFamily: 'var(--font-serif)' }}>
                404
            </h1>
            <p style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', marginBottom: '32px', maxWidth: '400px' }}>
                Oops! We couldn't find the page you were looking for. It might have been moved or deleted.
            </p>
            <Link
                to="/"
                style={{
                    padding: '12px 24px',
                    backgroundColor: 'var(--accent-primary)',
                    color: '#1c1822',
                    fontWeight: 'bold',
                    textDecoration: 'none',
                    borderRadius: '4px',
                    transition: 'opacity 0.2s',
                    display: 'inline-block'
                }}
            >
                RETURN HOME
            </Link>
        </div>
    );
}
