import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme, type ThemeMode } from '../../context/ThemeContext';

const OPTIONS: { mode: ThemeMode; label: string; icon: React.ElementType }[] = [
  { mode: 'light', label: 'Light theme', icon: Sun },
  { mode: 'dark', label: 'Dark theme', icon: Moon },
  { mode: 'system', label: 'Match system theme', icon: Monitor },
];

export const ThemeToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { mode, setMode } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Color scheme"
      className={`inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-muted border border-border ${className}`}
    >
      {OPTIONS.map(({ mode: optionMode, label, icon: Icon }) => {
        const isActive = mode === optionMode;
        return (
          <button
            key={optionMode}
            type="button"
            role="radio"
            aria-checked={isActive}
            title={label}
            aria-label={label}
            onClick={() => setMode(optionMode)}
            className={`p-1.5 rounded-md transition-colors ${
              isActive
                ? 'bg-card text-primary shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Icon className="w-4 h-4" />
          </button>
        );
      })}
    </div>
  );
};
