import React from "react";

export default function Terms() {
    return (
        <div style={{
            maxWidth: '800px',
            margin: '0 auto',
            padding: '64px 24px',
            color: 'var(--text-secondary)',
            fontSize: '1rem',
            lineHeight: '1.6',
            fontFamily: 'var(--font-data)'
        }}>
            <h1 style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '32px', fontFamily: 'var(--font-serif)' }}>
                Terms of Service
            </h1>

            <p style={{ marginBottom: '24px' }}>
                Last updated: {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
            </p>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    1. Agreement to Terms
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    By accessing or using ManhwaRank, you agree to be bound by these Terms of Service. If you disagree with any part of these terms, you may not access or use our service.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    2. Nature of the Service
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    ManhwaRank is an aggregator platform that compiles rankings, metadata, and publicly available information regarding manhwa, manhua, and manga from various third-party sources (including MangaDex, AniList, and Kitsu).
                </p>
                <p style={{ marginBottom: '16px' }}>
                    <strong style={{ color: 'var(--text-primary)' }}>ManhwaRank does NOT host, upload, or own any of the copyrighted images, artwork, or text descriptions displayed.</strong> All cover images are proxied dynamically on-the-fly from the original source servers purely for bandwidth optimization and performance. All rights to the intellectual property belong to their respective creators, publishers, and platforms.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    3. Fair Use & Copyright
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    The aggregation of metadata and the proxying of low-resolution cover thumbnails are provided under the premise of Fair Use for the purpose of commentary, search, and cataloging. If you are a copyright holder and believe that your work is being presented in a way that constitutes copyright infringement, please contact the original source platforms (MangaDex, AniList, Kitsu) where the content is permanently hosted.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    4. User Conduct
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    When using our platform (including our API endpoints), you agree not to:
                </p>
                <ul style={{ paddingLeft: '24px', listStyleType: 'disc', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <li>Automate mass-scraping or send unreasonably high volumes of requests that trigger our automated rate limits.</li>
                    <li>Attempt to bypass security measures or access administrative endpoints without authorization.</li>
                    <li>Use the service for any illegal or unauthorized purpose.</li>
                </ul>
                <p style={{ marginBottom: '16px' }}>
                    We reserve the right to temporarily or permanently block IP addresses or user accounts that violate these terms or degrade the service for other users.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    5. Disclaimer of Warranties
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    ManhwaRank is provided on an "AS IS" and "AS AVAILABLE" basis. We do not warrant that the service will be uninterrupted, secure, or error-free. We rely on third-party APIs for data; therefore, we make no guarantees regarding the accuracy, completeness, or reliability of any rankings, scores, or metadata shown.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    6. Changes to Terms
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    We reserve the right, at our sole discretion, to modify or replace these Terms at any time. By continuing to access or use our service after those revisions become effective, you agree to be bound by the revised terms.
                </p>
            </section>

            <section style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
                    7. Contact Information
                </h2>
                <p style={{ marginBottom: '16px' }}>
                    Questions about the Terms of Service should be sent to us at: <a href="mailto:hello@manhwarank.com" style={{ color: 'var(--accent-primary)', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.textDecoration = 'underline'} onMouseOut={(e) => e.target.style.textDecoration = 'none'}>hello@manhwarank.com</a>.
                </p>
            </section>
        </div>
    );
}
