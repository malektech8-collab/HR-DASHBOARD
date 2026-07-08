import React, { useState } from 'react';
import { SidebarNavigation } from './SidebarNavigation';
import { TopBar } from './TopBar';

interface AppLayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onPageChange: (page: string) => void;
  reportMonth: string;
  lastRefreshAt: string;
  refreshStatus: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  currentPage,
  onPageChange,
  reportMonth,
  lastRefreshAt,
  refreshStatus
}) => {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground flex transition-theme">
      {/* Left Sidebar — fixed on desktop, off-canvas drawer on mobile */}
      <SidebarNavigation
        currentPage={currentPage}
        onPageChange={onPageChange}
        isOpen={isMobileNavOpen}
        onClose={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen w-full">
        {/* Fixed TopBar */}
        <TopBar
          reportMonth={reportMonth}
          lastRefreshAt={lastRefreshAt}
          refreshStatus={refreshStatus}
          onMenuClick={() => setIsMobileNavOpen(true)}
        />

        {/* Page Content body */}
        <main className="flex-1 mt-16 p-4 sm:p-6 lg:p-8 overflow-y-auto min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};
