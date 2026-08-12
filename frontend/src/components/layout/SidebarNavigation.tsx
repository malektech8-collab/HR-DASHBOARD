import React from 'react';
import {
  UploadCloud,
  LayoutDashboard,
  Users,
  CreditCard,
  Clock,
  AlertTriangle,
  Building2,
  ShieldCheck,
  Scale,
  UserPlus,
  Star,
  LayoutGrid,
  X
} from 'lucide-react';
import { useBranding } from '../../context/BrandingContext';

interface SidebarProps {
  currentPage: string;
  onPageChange: (page: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const SidebarNavigation: React.FC<SidebarProps> = ({ currentPage, onPageChange, isOpen, onClose }) => {
  const { logoUrl } = useBranding();

  const menuItems: { id: string; label: string; icon: any; isPlaceholder?: boolean }[] = [
    { id: 'command-center', label: 'Command Center', icon: LayoutGrid },
    { id: 'executive', label: 'Executive Summary', icon: LayoutDashboard },
    { id: 'workforce', label: 'Workforce', icon: Users },
    { id: 'payroll', label: 'Payroll & Cost', icon: CreditCard },
    { id: 'attendance', label: 'Attendance', icon: Clock },
    { id: 'compliance', label: 'Saudization & Compliance', icon: ShieldCheck },
    { id: 'er', label: 'Employee Relations', icon: Scale },
    { id: 'recruitment', label: 'Recruitment & Hiring', icon: UserPlus },
    { id: 'talent', label: 'Talent & Succession', icon: Star },
    { id: 'data-quality', label: 'Data Quality', icon: AlertTriangle },
    { id: 'onboarding', label: 'Data Onboarding', icon: UploadCloud },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`w-64 bg-card border-r border-border flex flex-col h-screen fixed left-0 top-0 text-foreground z-30 transition-theme transition-transform duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-border gap-2 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {logoUrl ? (
              <img src={logoUrl} alt="Company logo" className="w-7 h-7 object-contain shrink-0 rounded" />
            ) : (
              <Building2 className="w-6 h-6 text-primary shrink-0" />
            )}
            <span className="font-bold text-lg tracking-wide uppercase truncate">HR Analytics</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation menu"
            className="lg:hidden p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onPageChange(item.id);
                  onClose();
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group ${
                  isActive
                    ? 'bg-primary text-primary-foreground font-semibold shadow-md'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                <Icon className={`w-4 h-4 transition-colors ${
                  isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-foreground'
                }`} />
                <span className="flex-1 text-left">{item.label}</span>
                {item.isPlaceholder && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border group-hover:bg-card">
                    Soon
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-border text-center shrink-0">
          <p className="text-xs text-muted-foreground">Version 1.0.0 "Genesis"</p>
        </div>
      </aside>
    </>
  );
};
