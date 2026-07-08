import React from 'react';

export const TableContainer: React.FC<React.HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }> = ({ children, className = '', ...props }) => (
  <div className={`bg-card border border-border rounded-xl shadow-lg flex flex-col overflow-hidden text-foreground ${className}`} {...props}>
    {children}
  </div>
);

export const TableWrapper: React.FC<React.HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }> = ({ children, className = '', ...props }) => (
  <div className={`flex-1 overflow-x-auto ${className}`} {...props}>
    <table className="w-full text-left border-collapse" role="table">
      {children}
    </table>
  </div>
);

export const TableHeader: React.FC<React.HTMLAttributes<HTMLTableSectionElement> & { children: React.ReactNode }> = ({ children, className = '', ...props }) => (
  <thead className={`border-b border-border bg-muted/60 ${className}`} role="rowgroup" {...props}>
    {children}
  </thead>
);

export const TableRow: React.FC<React.HTMLAttributes<HTMLTableRowElement> & { children: React.ReactNode; onClick?: () => void }> = ({ children, className = '', onClick, ...props }) => (
  <tr 
    className={`border-b border-border/50 hover:bg-muted/40 transition-colors ${onClick ? 'cursor-pointer' : ''} ${className}`}
    role="row"
    onClick={onClick}
    {...props}
  >
    {children}
  </tr>
);

export const TableHeadCell: React.FC<React.ThHTMLAttributes<HTMLTableHeaderCellElement> & { children: React.ReactNode; onClick?: (event: any) => void; ariaSort?: React.AriaAttributes['aria-sort'] }> = ({ children, className = '', onClick, ariaSort, ...props }) => (
  <th 
    className={`p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground select-none ${onClick ? 'cursor-pointer hover:bg-muted/60' : ''} ${className}`}
    role="columnheader"
    onClick={onClick}
    aria-sort={ariaSort}
    {...props}
  >
    {children}
  </th>
);

export const TableCell: React.FC<React.TdHTMLAttributes<HTMLTableCellElement> & { children?: React.ReactNode }> = ({ children, className = '', ...props }) => (
  <td className={`p-4 text-sm align-middle ${className}`} role="cell" {...props}>
    {children}
  </td>
);
