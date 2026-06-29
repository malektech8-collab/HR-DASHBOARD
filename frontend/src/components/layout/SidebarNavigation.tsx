import React from 'react';
import { 
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
  LayoutGrid
} from 'lucide-react';

interface SidebarProps {
  currentPage: string;
  onPageChange: (page: string) => void;
}

export const SidebarNavigation: React.FC<SidebarProps> = ({ currentPage, onPageChange }) => {
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
  ];

  return (
    <aside className="w-64 bg-card border-r border-border flex flex-col h-screen fixed left-0 top-0 text-foreground">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-border gap-2">
        <Building2 className="w-6 h-6 text-primary" />
        <span className="font-bold text-lg tracking-wide uppercase">HR Analytics</span>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
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
      <div className="p-4 border-t border-border bg-slate-950/20 text-center">
        <p className="text-xs text-muted-foreground">Version 1.0.0 (Milestone 2H)</p>
      </div>
    </aside>
  );
};

