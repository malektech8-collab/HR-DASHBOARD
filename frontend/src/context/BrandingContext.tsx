import React, { createContext, useContext, useMemo, useState, useCallback } from 'react';

const STORAGE_KEY = 'hr-dashboard-logo';
const MAX_LOGO_BYTES = 1024 * 1024; // 1MB — keeps localStorage usage safe

interface BrandingContextValue {
  logoUrl: string | null;
  setLogo: (file: File) => Promise<void>;
  clearLogo: () => void;
  error: string | null;
}

const BrandingContext = createContext<BrandingContextValue | undefined>(undefined);

function readStoredLogo(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export const BrandingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [logoUrl, setLogoUrl] = useState<string | null>(readStoredLogo);
  const [error, setError] = useState<string | null>(null);

  const setLogo = useCallback(async (file: File) => {
    setError(null);

    if (!file.type.startsWith('image/')) {
      setError('Please choose an image file (PNG, JPG, SVG, or WebP).');
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      setError('Logo must be smaller than 1MB.');
      return;
    }

    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });

    window.localStorage.setItem(STORAGE_KEY, dataUrl);
    setLogoUrl(dataUrl);
  }, []);

  const clearLogo = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setLogoUrl(null);
    setError(null);
  }, []);

  const value = useMemo(() => ({ logoUrl, setLogo, clearLogo, error }), [logoUrl, setLogo, clearLogo, error]);

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
};

export function useBranding(): BrandingContextValue {
  const ctx = useContext(BrandingContext);
  if (!ctx) throw new Error('useBranding must be used within a BrandingProvider');
  return ctx;
}
