import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
    return (
        <footer style={{
            marginTop: '64px',
            padding: '32px 16px',
            borderTop: '1px solid var(--border-color)',
            textAlign: 'center',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-data)'
        }}>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginBottom: '16px' }}>
                <Link to="/privacy" style={{ color: 'inherit', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.color = 'var(--accent-primary)'} onMouseOut={(e) => e.target.style.color = 'inherit'}>Privacy Policy</Link>
                <Link to="/terms" style={{ color: 'inherit', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.color = 'var(--accent-primary)'} onMouseOut={(e) => e.target.style.color = 'inherit'}>Terms of Service</Link>
                <a href="mailto:hello@manhwarank.com" style={{ color: 'inherit', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.color = 'var(--accent-primary)'} onMouseOut={(e) => e.target.style.color = 'inherit'}>Contact</a>
            </div>
            <p style={{ margin: '0 0 8px 0' }}>
                This site uses privacy-friendly analytics. Watchlist data is synced to your account.
            </p>
            <p style={{ margin: '0 0 16px 0', opacity: 0.6 }}>
                Data sourced from MangaDex, AniList, and Kitsu. We do not host copyrighted content.
            </p>
            <p style={{ margin: 0, opacity: 0.4 }}>
                © {new Date().getFullYear()} ManhwaRank
            </p>
        </footer>
    );
}
