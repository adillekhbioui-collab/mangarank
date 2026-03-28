import React from "react";

export default function Privacy() {
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
        Privacy Policy
      </h1>

      <p style={{ marginBottom: '24px' }}>
        Last updated: {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
      </p>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          1. Introduction
        </h2>
        <p style={{ marginBottom: '16px' }}>
          Welcome to ManhwaRank. We respect your privacy and are committed to protecting it through our compliance with this policy. This Privacy Policy explains our practices regarding the collection, use, and disclosure of information when you use our website.
        </p>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          2. Information We Collect
        </h2>
        <p style={{ marginBottom: '16px' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Authentication Data:</strong> If you choose to log in via Google OAuth, we receive your email address, basic profile information (like your name and avatar), and a unique identifier from Google via our authentication provider (Supabase). We do not have access to your Google password.
        </p>
        <p style={{ marginBottom: '16px' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Usage Data:</strong> We use privacy-friendly, cookie-less analytics via Umami to collect anonymous usage data. This includes page views, search queries, and general interactions (like adding to a watchlist). This data helps us improve the platform and contains no personally identifiable information (PII).
        </p>
        <p style={{ marginBottom: '16px' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Watchlist Data:</strong> If you use the site anonymously, your watchlist is stored locally on your device (in localStorage). If you log in, your watchlist is synced to our database securely so you can access it across devices.
        </p>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          3. How We Use Your Information
        </h2>
        <ul style={{ paddingLeft: '24px', listStyleType: 'disc', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <li>To provide and maintain the ManhwaRank service.</li>
          <li>To sync your personal watchlist across devices (for logged-in users).</li>
          <li>To analyze aggregated, anonymous usage trends to improve the user experience.</li>
          <li>To prevent abuse, spam, and technical issues.</li>
        </ul>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          4. Third-Party Services
        </h2>
        <p style={{ marginBottom: '16px' }}>
          We use <strong style={{ color: 'var(--text-primary)' }}>Supabase</strong> for secure database storage and authentication. Supabase complies with strict data security standards. We also proxy images from external sources (like MangaDex, AniList, and Kitsu) strictly to optimize bandwidth; we do not share your reading habits with these external providers.
        </p>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          5. Data Security
        </h2>
        <p style={{ marginBottom: '16px' }}>
          We take reasonable measures to protect your information from unauthorized access, loss, or misuse. Our database employs Row Level Security (RLS) to ensure that your authenticated watchlist data is only accessible by you.
        </p>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          6. Your Choices
        </h2>
        <p style={{ marginBottom: '16px' }}>
          You can use ManhwaRank entirely anonymously without providing any personal data. If you have logged in and wish to have your account and watchlist data permanently deleted from our servers, please contact us at the email provided below.
        </p>
      </section>

      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>
          7. Contact Us
        </h2>
        <p style={{ marginBottom: '16px' }}>
          If you have any questions or concerns regarding this Privacy Policy, please contact us at: <a href="mailto:hello@manhwarank.com" style={{ color: 'var(--accent-primary)', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.textDecoration = 'underline'} onMouseOut={(e) => e.target.style.textDecoration = 'none'}>hello@manhwarank.com</a>.
        </p>
      </section>
    </div>
  );
}
