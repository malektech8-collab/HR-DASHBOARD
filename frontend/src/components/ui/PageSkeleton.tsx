import React from 'react';

export const PageSkeleton: React.FC = () => {
  return (
    <div className="p-6 space-y-6 text-foreground animate-pulse" aria-busy="true" aria-label="Loading page data...">
      {/* Top Title Bar Skeleton */}
      <div className="h-8 bg-muted rounded-lg w-1/4 mb-6"></div>
      
      {/* KPI Cards Row Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-5 h-[140px] flex flex-col justify-between">
            <div className="h-3 bg-muted rounded w-1/2"></div>
            <div className="h-6 bg-muted rounded w-3/4 mt-2"></div>
            <div className="h-3 bg-muted rounded w-2/3 mt-2"></div>
          </div>
        ))}
      </div>
      
      {/* Visual Analytics Grid Row Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <div className="bg-card border border-border rounded-xl p-5 h-[300px]">
          <div className="h-4 bg-muted rounded w-1/3 mb-4"></div>
          <div className="h-full bg-muted/30 rounded-lg"></div>
        </div>
        <div className="bg-card border border-border rounded-xl p-5 h-[300px]">
          <div className="h-4 bg-muted rounded w-1/3 mb-4"></div>
          <div className="h-full bg-muted/30 rounded-lg"></div>
        </div>
      </div>
    </div>
  );
};
