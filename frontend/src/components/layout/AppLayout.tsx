import React from 'react';
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
  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Fixed Left Sidebar */}
      <SidebarNavigation currentPage={currentPage} onPageChange={onPageChange} />

      {/* Main Content Area */}
      <div className="flex-1 pl-64 flex flex-col min-h-screen">
        {/* Fixed TopBar */}
        <TopBar 
          reportMonth={reportMonth} 
          lastRefreshAt={lastRefreshAt} 
          refreshStatus={refreshStatus} 
        />

        {/* Page Content body */}
        <main className="flex-1 mt-16 p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
