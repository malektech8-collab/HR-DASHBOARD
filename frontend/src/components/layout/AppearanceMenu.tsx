import React, { useEffect, useRef, useState } from 'react';
import { Settings, Image, Trash2, Upload } from 'lucide-react';
import { ThemeToggle } from '../ui/ThemeToggle';
import { useBranding } from '../../context/BrandingContext';

export const AppearanceMenu: React.FC = () => {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { logoUrl, setLogo, clearLogo, error } = useBranding();

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Appearance settings"
        title="Appearance settings"
        className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
      >
        <Settings className="w-4 h-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-72 rounded-xl border border-border bg-card shadow-lg p-4 z-20 transition-theme"
        >
          <div className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Color scheme
            </p>
            <ThemeToggle />
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Company logo
            </p>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg border border-border bg-muted flex items-center justify-center overflow-hidden shrink-0">
                {logoUrl ? (
                  <img src={logoUrl} alt="Company logo preview" className="w-full h-full object-contain" />
                ) : (
                  <Image className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary-hover"
                >
                  <Upload className="w-3.5 h-3.5" />
                  Upload logo
                </button>
                {logoUrl && (
                  <button
                    type="button"
                    onClick={clearLogo}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-critical"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Remove logo
                  </button>
                )}
              </div>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void setLogo(file);
                e.target.value = '';
              }}
            />
            {error && <p className="mt-2 text-[11px] text-critical">{error}</p>}
            <p className="mt-2 text-[11px] text-muted-foreground">PNG, JPG, SVG or WebP, up to 1MB.</p>
          </div>
        </div>
      )}
    </div>
  );
};
