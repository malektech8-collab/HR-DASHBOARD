import React, { useMemo, useState } from 'react';
import type { DQExceptionItem } from '../../lib/types';
import { AlertTriangle, AlertCircle, Search, ArrowUp, ArrowDown, ChevronsUpDown } from 'lucide-react';
import { VirtualTable } from '../ui/VirtualTable';
import type { VirtualTableColumn } from '../ui/VirtualTable';

interface ExceptionTableProps {
  data: DQExceptionItem[];
}

type SortField = keyof DQExceptionItem | '';
type SortOrder = 'asc' | 'desc';

export const ExceptionTable: React.FC<ExceptionTableProps> = ({ data }) => {
  const [globalFilter, setGlobalFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Filter logic
  const filteredData = useMemo(() => {
    if (!globalFilter) return data;
    const term = globalFilter.toLowerCase();
    return data.filter(item => 
      String(item.employee_id || '').toLowerCase().includes(term) ||
      String(item.employee_name || '').toLowerCase().includes(term) ||
      String(item.issue_type || '').toLowerCase().includes(term) ||
      String(item.description || '').toLowerCase().includes(term) ||
      String(item.severity || '').toLowerCase().includes(term) ||
      String(item.recommended_action || '').toLowerCase().includes(term)
    );
  }, [data, globalFilter]);

  // Sort logic
  const sortedData = useMemo(() => {
    if (!sortField) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = String(a[sortField] || '');
      const bVal = String(b[sortField] || '');
      return sortOrder === 'asc' 
        ? aVal.localeCompare(bVal, undefined, { numeric: true, sensitivity: 'base' })
        : bVal.localeCompare(aVal, undefined, { numeric: true, sensitivity: 'base' });
    });
  }, [filteredData, sortField, sortOrder]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) return <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground/50" />;
    return sortOrder === 'asc' 
      ? <ArrowUp className="w-3.5 h-3.5 text-primary" /> 
      : <ArrowDown className="w-3.5 h-3.5 text-primary" />;
  };

  const columns = useMemo<VirtualTableColumn<DQExceptionItem>[]>(() => [
    {
      header: 'Employee ID',
      accessorKey: 'employee_id',
      cell: (item) => <span className="font-mono text-xs text-muted-foreground">{item.employee_id || 'N/A'}</span>,
    },
    {
      header: 'Employee Name',
      accessorKey: 'employee_name',
      cell: (item) => <span className="font-semibold text-foreground">{item.employee_name}</span>,
    },
    {
      header: 'Issue Type',
      accessorKey: 'issue_type',
      cell: (item) => <span className="text-sm font-medium">{item.issue_type}</span>,
    },
    {
      header: 'Description',
      accessorKey: 'description',
      cell: (item) => <span className="text-xs text-muted-foreground block max-w-md whitespace-normal">{item.description}</span>,
    },
    {
      header: 'Severity',
      accessorKey: 'severity',
      cell: (item) => {
        const isCritical = item.severity.toLowerCase() === 'critical';
        return (
          <div className="flex items-center gap-1.5">
            {isCritical ? (
              <AlertTriangle className="w-3.5 h-3.5 text-critical" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-warning" />
            )}
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              isCritical 
                ? 'bg-critical/10 text-critical border border-critical/20' 
                : 'bg-warning/10 text-warning border border-warning/20'
            }`}>
              {item.severity}
            </span>
          </div>
        );
      }
    },
    {
      header: 'Action Required',
      accessorKey: 'recommended_action',
      cell: (item) => (
        <span className="text-xs text-primary bg-primary/5 border border-primary/20 px-2 py-1 rounded block max-w-[240px] whitespace-normal font-medium">
          {item.recommended_action}
        </span>
      ),
    }
  ], []);

  // Map columns to include custom sorting header renderers
  const columnsWithSorting = useMemo(() => {
    return columns.map(col => ({
      ...col,
      header: (
        <div 
          className="flex items-center gap-1.5 cursor-pointer hover:text-foreground transition-colors"
          onClick={() => handleSort(col.accessorKey as SortField)}
          role="button"
          tabIndex={0}
          aria-label={`Sort by ${col.header}`}
        >
          <span>{col.header}</span>
          {renderSortIcon(col.accessorKey as SortField)}
        </div>
      )
    })) as any;
  }, [columns, sortField, sortOrder]);

  return (
    <div className="flex flex-col text-foreground">
      {/* Table Header Filter Row */}
      <div className="p-4 border border-b-0 border-border rounded-t-xl flex items-center justify-between gap-4 bg-slate-950/20">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={globalFilter}
            onChange={e => setGlobalFilter(e.target.value)}
            placeholder="Search exceptions..."
            className="w-full bg-background border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-primary text-foreground placeholder-muted-foreground"
          />
        </div>
        <div className="text-xs text-muted-foreground font-semibold">
          Total Exceptions: <span className="text-foreground bg-muted border border-border px-2 py-0.5 rounded">{sortedData.length}</span>
        </div>
      </div>

      {/* Main Virtualized Table view */}
      <VirtualTable
        data={sortedData}
        columns={columnsWithSorting}
        rowHeight={56}
        viewportHeight={380}
      />
    </div>
  );
};
