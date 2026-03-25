import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient.js';

const AuthContext = createContext({
    user: null,
    session: null,
    loading: true,
    signInWithGoogle: async () => { },
    signOut: async () => { },
});

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Get initial session
        supabase.auth.getSession().then(({ data: { session: s } }) => {
            setSession(s);
            setUser(s?.user ?? null);
            setLoading(false);
        });

        // Listen for auth changes (login, logout, token refresh)
        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, s) => {
            setSession(s);
            setUser(s?.user ?? null);
            setLoading(false);
        });

        return () => subscription.unsubscribe();
    }, []);

    async function signInWithGoogle() {
        const { error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin,
            },
        });
        if (error) {
            console.error('[Auth] Google sign-in error:', error.message);
        }
    }

    async function signOut() {
        const { error } = await supabase.auth.signOut();
        if (error) {
            console.error('[Auth] Sign-out error:', error.message);
        }
    }

    return (
        <AuthContext.Provider
            value={{ user, session, loading, signInWithGoogle, signOut }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return ctx;
}
