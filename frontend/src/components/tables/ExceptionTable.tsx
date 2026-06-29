import React, { useMemo, useState } from 'react';
import { 
  useReactTable, 
  getCoreRowModel, 
  getPaginationRowModel, 
  getSortedRowModel, 
  getFilteredRowModel,
  flexRender
} from '@tanstack/react-table';
import type { ColumnDef, SortingState } from '@tanstack/react-table';
import type { DQExceptionItem } from '../../lib/types';
import { ChevronDown, ChevronUp, ChevronsUpDown, AlertTriangle, AlertCircle, Search } from 'lucide-react';

interface ExceptionTableProps {
  data: DQExceptionItem[];
}

export const ExceptionTable: React.FC<ExceptionTableProps> = ({ data }) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columns = useMemo<ColumnDef<DQExceptionItem>[]>(() => [
    {
      accessorKey: 'employee_id',
      header: 'Employee ID',
      cell: info => <span className="font-mono text-xs text-muted-foreground">{info.getValue() as string || 'N/A'}</span>,
    },
    {
      accessorKey: 'employee_name',
      header: 'Employee Name',
      cell: info => <span className="font-semibold text-foreground">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'issue_type',
      header: 'Issue Type',
      cell: info => <span className="text-sm font-medium">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: info => <span className="text-xs text-muted-foreground block max-w-md whitespace-normal">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'severity',
      header: 'Severity',
      cell: info => {
        const severity = info.getValue() as string;
        const isCritical = severity.toLowerCase() === 'critical';
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
              {severity}
            </span>
          </div>
        );
      }
    },
    {
      accessorKey: 'recommended_action',
      header: 'Action Required',
      cell: info => (
        <span className="text-xs text-primary bg-primary/5 border border-primary/20 px-2 py-1 rounded block max-w-[240px] whitespace-normal font-medium">
          {info.getValue() as string}
        </span>
      ),
    }
  ], []);

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    initialState: {
      pagination: {
        pageSize: 5
      }
    }
  });

  return (
    <div className="bg-card border border-border rounded-xl shadow-lg flex flex-col overflow-hidden text-foreground">
      {/* Table Header Filter Row */}
      <div className="p-4 border-b border-border flex items-center justify-between gap-4 bg-slate-950/20">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={globalFilter ?? ''}
            onChange={e => setGlobalFilter(e.target.value)}
            placeholder="Search exceptions..."
            className="w-full bg-background border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:border-primary text-foreground placeholder-muted-foreground"
          />
        </div>
        <div className="text-xs text-muted-foreground font-semibold">
          Total Exceptions: <span className="text-foreground bg-muted border border-border px-2 py-0.5 rounded">{data.length}</span>
        </div>
      </div>

      {/* Main Table view */}
      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id} className="border-b border-border bg-slate-950/30">
                {headerGroup.headers.map(header => (
                  <th 
                    key={header.id} 
                    className="p-4 text-xs font-bold uppercase tracking-wider text-muted-foreground select-none cursor-pointer hover:bg-slate-950/40"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1.5">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        {
                          asc: <ChevronUp className="w-3.5 h-3.5 text-primary" />,
                          desc: <ChevronDown className="w-3.5 h-3.5 text-primary" />,
                        }[header.column.getIsSorted() as string] ?? <ChevronsUpDown className="w-3.5 h-3.5 text-muted-foreground/50" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-border/50">
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-slate-900/30 transition-colors">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="p-4 text-sm align-middle">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="p-8 text-center text-sm text-muted-foreground">
                  No exceptions found. Data quality is healthy!
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls Footer */}
      {table.getPageCount() > 1 && (
        <div className="p-4 border-t border-border flex items-center justify-between gap-4 bg-slate-950/20 text-xs">
          <div className="flex items-center gap-1 text-muted-foreground">
            <span>Page</span>
            <span className="font-semibold text-foreground">{table.getState().pagination.pageIndex + 1}</span>
            <span>of</span>
            <span className="font-semibold text-foreground">{table.getPageCount()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground transition-all disabled:opacity-40 disabled:hover:bg-card"
            >
              Previous
            </button>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="px-3 py-1.5 rounded border border-border bg-card hover:bg-muted text-foreground transition-all disabled:opacity-40 disabled:hover:bg-card"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
