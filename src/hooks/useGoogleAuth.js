import { useState, useEffect, useCallback } from 'react';
import { GOOGLE_CONFIG } from '../config';

const SESSION_KEY = 'r2i2_user';

export default function useGoogleAuth() {
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!GOOGLE_CONFIG.clientId || GOOGLE_CONFIG.clientId.startsWith('YOUR_')) {
      setReady(true);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = () => {
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CONFIG.clientId,
        callback: handleCredentialResponse,
        auto_select: false,
      });
      setReady(true);
    };
    document.head.appendChild(script);

    return () => {
      if (script.parentNode) script.parentNode.removeChild(script);
    };
  }, []);

  function handleCredentialResponse(response) {
    try {
      // Decode JWT payload (base64url)
      const payload = JSON.parse(
        atob(response.credential.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
      );
      const userData = {
        email: payload.email,
        name: payload.name,
        picture: payload.picture,
        token: response.credential,
      };
      setUser(userData);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(userData));
    } catch {
      // Decode failed
    }
  }

  const signIn = useCallback(() => {
    if (!GOOGLE_CONFIG.clientId || GOOGLE_CONFIG.clientId.startsWith('YOUR_')) {
      // Demo mode: use a placeholder user for testing
      const demo = { email: 'demo@example.com', name: 'Demo User', picture: null, token: null };
      setUser(demo);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(demo));
      return;
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt();
    }
  }, []);

  const signOut = useCallback(() => {
    setUser(null);
    sessionStorage.removeItem(SESSION_KEY);
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }
  }, []);

  return { user, signIn, signOut, ready };
}
