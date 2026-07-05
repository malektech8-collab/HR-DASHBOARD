import React, { useState, useRef, useMemo } from 'react';
import { TableContainer, TableWrapper, TableHeader, TableRow, TableHeadCell, TableCell } from './Table';

export interface VirtualTableColumn<T> {
  header: string;
  cell: (item: T, index: number) => React.ReactNode;
  accessorKey: keyof T | string;
  className?: string;
}

interface VirtualTableProps<T> {
  data: T[];
  columns: VirtualTableColumn<T>[];
  rowHeight?: number;
  viewportHeight?: number;
  overscan?: number;
  onRowClick?: (item: T) => void;
}

export function VirtualTable<T>({
  data,
  columns,
  rowHeight = 52,
  viewportHeight = 400,
  overscan = 5,
  onRowClick
}: VirtualTableProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  };

  const totalRows = data.length;

  // Viewport Slicing Calculations
  const { startIndex, endIndex, topSpacing, bottomSpacing } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const end = Math.min(totalRows - 1, Math.floor((scrollTop + viewportHeight) / rowHeight) + overscan);
    
    const top = start * rowHeight;
    const bottom = Math.max(0, (totalRows - end - 1) * rowHeight);

    return {
      startIndex: start,
      endIndex: end,
      topSpacing: top,
      bottomSpacing: bottom
    };
  }, [scrollTop, viewportHeight, rowHeight, totalRows, overscan]);

  // Sliced Visible Data
  const visibleData = useMemo(() => {
    return data.slice(startIndex, endIndex + 1);
  }, [data, startIndex, endIndex]);

  return (
    <TableContainer className="relative">
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        style={{ height: viewportHeight, overflowY: 'auto' }}
        className="w-full"
      >
        <TableWrapper>
          <TableHeader className="sticky top-0 z-10 bg-[#0f172a] border-b border-border">
            <TableRow>
              {columns.map((col, idx) => (
                <TableHeadCell key={idx} className={col.className}>
                  {col.header}
                </TableHeadCell>
              ))}
            </TableRow>
          </TableHeader>
          
          <tbody className="divide-y divide-border/50" role="rowgroup">
            {/* Top Virtual Spacer */}
            {topSpacing > 0 && (
              <tr style={{ height: topSpacing }} aria-hidden="true">
                <td colSpan={columns.length} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}
            
            {/* Render Row Elements */}
            {visibleData.length > 0 ? (
              visibleData.map((item, idx) => {
                const globalIndex = startIndex + idx;
                return (
                  <TableRow 
                    key={globalIndex} 
                    onClick={onRowClick ? () => onRowClick(item) : undefined}
                  >
                    {columns.map((col, colIdx) => (
                      <TableCell key={colIdx} className={col.className}>
                        {col.cell(item, globalIndex)}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                  No records found.
                </TableCell>
              </TableRow>
            )}
            
            {/* Bottom Virtual Spacer */}
            {bottomSpacing > 0 && (
              <tr style={{ height: bottomSpacing }} aria-hidden="true">
                <td colSpan={columns.length} style={{ padding: 0, border: 'none' }} />
              </tr>
            )}
          </tbody>
        </TableWrapper>
      </div>
    </TableContainer>
  );
}
