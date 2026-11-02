import React, { useState, useMemo } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  FileSpreadsheet,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { Button } from "./Button";
import { Badge } from "./Badge";

export interface DataTableProps {
  columns: string[];
  rows: Record<string, any>[];
  totalRowCount?: number;
  executionTimeMs?: number;
  title?: string;
  exportFilenamePrefix?: string;
  enableExport?: boolean;
  enableSearch?: boolean;
  enablePagination?: boolean;
  defaultPageSize?: number;
  maxHeight?: string;
}

export function DataTable({
  columns,
  rows,
  totalRowCount,
  executionTimeMs,
  title,
  exportFilenamePrefix = "query_data",
  enableExport = true,
  enableSearch = true,
  enablePagination = true,
  defaultPageSize = 25,
  maxHeight = "450px",
}: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState<number>(defaultPageSize);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Filtered rows based on search
  const filteredRows = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter((row) =>
      columns.some((col) => {
        const val = row[col];
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(term);
      })
    );
  }, [rows, columns, searchTerm]);

  // Sorted rows
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;
    return [...filteredRows].sort((a, b) => {
      const valA = a[sortColumn];
      const valB = b[sortColumn];

      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === "number" && typeof valB === "number") {
        return sortDirection === "asc" ? valA - valB : valB - valA;
      }

      const strA = String(valA);
      const strB = String(valB);
      return sortDirection === "asc" ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });
  }, [filteredRows, sortColumn, sortDirection]);

  // Paginated rows
  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize));
  const paginatedRows = useMemo(() => {
    if (!enablePagination) return sortedRows;
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, currentPage, pageSize, enablePagination]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortColumn(null);
      }
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
    setCurrentPage(1);
  };

  const exportCsv = () => {
    if (!columns.length || !rows.length) return;
    const headers = columns.join(",");
    const rowLines = sortedRows.map((row) =>
      columns
        .map((col) => {
          const val = row[col];
          if (val === null || val === undefined) return "";
          const str = String(val).replace(/"/g, '""');
          return str.includes(",") || str.includes('"') || str.includes("\n") ? `"${str}"` : str;
        })
        .join(",")
    );
    const content = "data:text/csv;charset=utf-8," + encodeURIComponent([headers, ...rowLines].join("\n"));
    const link = document.createElement("a");
    link.href = content;
    link.download = `${exportFilenamePrefix}_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportJson = () => {
    if (!rows.length) return;
    const content =
      "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sortedRows, null, 2));
    const link = document.createElement("a");
    link.href = content;
    link.download = `${exportFilenamePrefix}_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="rounded-xl border border-border bg-card/80 overflow-hidden space-y-3 p-4">
      {/* Table Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          {title && <span className="font-semibold text-foreground">{title}</span>}
          <Badge variant="mono" size="xs">
            {rows.length.toLocaleString()} {rows.length === 1 ? "row" : "rows"}
            {totalRowCount && totalRowCount > rows.length && ` (of ${totalRowCount.toLocaleString()})`}
          </Badge>
          {executionTimeMs !== undefined && (
            <span className="text-[11px] font-mono text-muted-foreground">
              {executionTimeMs.toFixed(1)}ms
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
          {enableSearch && (
            <div className="relative flex-1 sm:w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                placeholder="Search records..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-8 pr-2.5 py-1 text-xs bg-background/60 border border-border rounded-lg text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/70"
              />
            </div>
          )}

          {enableExport && rows.length > 0 && (
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <Button
                variant="outline"
                size="xs"
                onClick={exportCsv}
                icon={<FileSpreadsheet className="w-3.5 h-3.5 text-success" />}
                title="Export filtered records as CSV"
              >
                CSV
              </Button>
              <Button
                variant="outline"
                size="xs"
                onClick={exportJson}
                icon={<Download className="w-3.5 h-3.5 text-primary" />}
                title="Export filtered records as JSON"
              >
                JSON
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main Table Scroll Container */}
      {rows.length === 0 ? (
        <div className="p-8 text-center text-xs text-muted-foreground border border-border/50 rounded-lg bg-background/30">
          No records to display.
        </div>
      ) : (
        <div
          className="overflow-x-auto overflow-y-auto border border-border/70 rounded-lg bg-background/40"
          style={{ maxHeight }}
        >
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-card/90 border-b border-border sticky top-0 z-10 backdrop-blur">
              <tr>
                {columns.map((col) => {
                  const isSorted = sortColumn === col;
                  return (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className="p-2.5 font-mono font-semibold text-muted-foreground hover:text-foreground cursor-pointer transition-colors select-none whitespace-nowrap"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>{col}</span>
                        {isSorted ? (
                          sortDirection === "asc" ? (
                            <ArrowUp className="w-3 h-3 text-primary" />
                          ) : (
                            <ArrowDown className="w-3 h-3 text-primary" />
                          )
                        ) : (
                          <ArrowUpDown className="w-3 h-3 opacity-30 hover:opacity-100" />
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {paginatedRows.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="p-6 text-center text-muted-foreground italic">
                    No records match search "{searchTerm}".
                  </td>
                </tr>
              ) : (
                paginatedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-muted/30 transition-colors">
                    {columns.map((col) => {
                      const val = row[col];
                      return (
                        <td key={col} className="p-2.5 font-mono text-foreground/90 whitespace-nowrap">
                          {val !== null && val !== undefined ? (
                            String(val)
                          ) : (
                            <span className="text-muted-foreground/60 italic text-[11px]">NULL</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer */}
      {enablePagination && totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs pt-1 border-t border-border/40 text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>
              Showing {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, sortedRows.length)} of {sortedRows.length}
            </span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-background/80 border border-border rounded px-1.5 py-0.5 text-xs text-foreground focus:outline-none focus:border-primary"
            >
              <option value={10}>10 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              title="First Page"
            >
              <ChevronsLeft className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </Button>
            <span className="px-2 font-mono text-[11px]">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages}
              title="Last Page"
            >
              <ChevronsRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

