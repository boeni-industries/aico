import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Switch,
  FormControlLabel,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Play as PlayIcon,
  Copy as CopyIcon,
  Download as DownloadIcon,
  AlertTriangle as WarningIcon,
  CheckCircle as SuccessIcon,
  AlertCircle as ErrorIcon,
  Code as CodeIcon,
  Info as InfoIcon,
} from 'lucide-react';
import { executeSQLQuery, QueryRequest, QueryResult } from '../../api/operations';
import { CodeEditor } from '../common/CodeEditor';

interface SQLQueryInterfaceProps {
  databaseName: string;
}


export const SQLQueryInterface: React.FC<SQLQueryInterfaceProps> = ({ databaseName }) => {
  const [query, setQuery] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [allowDestructive, setAllowDestructive] = useState(false);
  const [showDestructiveWarning, setShowDestructiveWarning] = useState(false);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);

  const handleExecuteQuery = async (forceExecute: boolean = false) => {
    if (!query.trim()) return;

    // Check if query is potentially destructive
    const queryUpper = query.toUpperCase();
    const isDestructive = /\b(DELETE|UPDATE|INSERT|REPLACE)\b/.test(queryUpper);

    if (isDestructive && !allowDestructive && !forceExecute) {
      setPendingQuery(query);
      setShowDestructiveWarning(true);
      return;
    }

    setIsExecuting(true);
    setQueryError(null);
    setQueryResult(null);
    setPage(0);

    try {
      const request: QueryRequest = {
        query,
        limit: 1000,
        allow_destructive: allowDestructive,
      };

      const result = await executeSQLQuery(request);

      if (result.success) {
        setQueryResult(result);
      } else {
        setQueryError(result.error || 'Query execution failed');
      }
    } catch (error: any) {
      console.error('[SQL] Query execution failed:', error);
      setQueryError(error.message || 'Failed to execute query');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleConfirmDestructive = () => {
    setShowDestructiveWarning(false);
    setAllowDestructive(true);
    if (pendingQuery) {
      setQuery(pendingQuery);
      setPendingQuery(null);
      // Execute after state updates
      setTimeout(() => handleExecuteQuery(true), 100);
    }
  };

  const handleCancelDestructive = () => {
    setShowDestructiveWarning(false);
    setPendingQuery(null);
  };

  const handleCopyQuery = () => {
    navigator.clipboard.writeText(query);
  };

  const handleExportCSV = () => {
    if (!queryResult?.rows || !queryResult?.columns) return;

    const { columns, rows } = queryResult;
    const csvRows = [
      columns.join(','),
      ...rows.map((row) =>
        row
          .map((cell) => {
            let str = cell === null || cell === undefined ? '' : String(cell);
            return str.includes(',') || str.includes('\n') || str.includes('"')
              ? `"${str.replace(/"/g, '""')}"`
              : str;
          })
          .join(',')
      ),
    ];

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${databaseName}-query-results-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box>
      {/* Query Editor */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          borderRadius: '16px',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(0, 0, 0, 0.2) 100%)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <CodeIcon size={24} color="#3B82F6" />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', mb: 0.5 }}>
              SQL Query Editor
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
              Execute SQL queries on {databaseName} database
            </Typography>
          </Box>
          <FormControlLabel
            control={
              <Switch
                checked={allowDestructive}
                onChange={(e) => setAllowDestructive(e.target.checked)}
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: '#EF4444',
                  },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                    backgroundColor: '#EF4444',
                  },
                }}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <WarningIcon size={14} color={allowDestructive ? '#EF4444' : 'rgba(255,255,255,0.5)'} />
                <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                  Allow Modifications
                </Typography>
              </Box>
            }
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <CodeEditor
            value={query}
            onChange={setQuery}
            language="sql"
            height={300}
            placeholder="Enter your SQL query here..."
            schemaEndpoint="http://localhost:8771/api/v1/operations/databases/postgresql/schema"
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={isExecuting ? <CircularProgress size={20} sx={{ color: '#fff' }} /> : <PlayIcon size={18} />}
            disabled={!query.trim() || isExecuting}
            onClick={() => handleExecuteQuery()}
            sx={{
              textTransform: 'none',
              fontWeight: 600,
              px: 3,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
              },
              '&:disabled': {
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'rgba(255, 255, 255, 0.3)',
              },
            }}
          >
            {isExecuting ? 'Executing...' : 'Execute Query'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<CopyIcon size={18} />}
            disabled={!query.trim()}
            onClick={handleCopyQuery}
            sx={{
              textTransform: 'none',
              borderColor: 'rgba(59, 130, 246, 0.3)',
              color: '#3B82F6',
              '&:hover': {
                borderColor: '#3B82F6',
                bgcolor: 'rgba(59, 130, 246, 0.1)',
              },
            }}
          >
            Copy
          </Button>
        </Box>
      </Paper>

      {/* Destructive Query Warning Dialog */}
      <Dialog
        open={showDestructiveWarning}
        onClose={handleCancelDestructive}
        PaperProps={{
          sx: {
            borderRadius: '16px',
            bgcolor: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          },
        }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <WarningIcon size={24} color="#EF4444" />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Destructive Operation Detected
          </Typography>
        </DialogTitle>
        <DialogContent>
          <Alert
            severity="warning"
            icon={<WarningIcon />}
            sx={{
              mb: 2,
              bgcolor: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
            }}
          >
            This query contains potentially destructive operations (DELETE, UPDATE, INSERT, or REPLACE).
          </Alert>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Executing this query will modify data in the database. This action cannot be undone.
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#EF4444' }}>
            Are you sure you want to proceed?
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, gap: 1 }}>
          <Button
            onClick={handleCancelDestructive}
            variant="outlined"
            sx={{
              textTransform: 'none',
              borderColor: 'rgba(255, 255, 255, 0.2)',
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDestructive}
            variant="contained"
            sx={{
              textTransform: 'none',
              bgcolor: '#EF4444',
              '&:hover': {
                bgcolor: '#DC2626',
              },
            }}
          >
            Execute Anyway
          </Button>
        </DialogActions>
      </Dialog>

      {/* Query Error */}
      {queryError && (
        <Alert
          severity="error"
          icon={<ErrorIcon />}
          sx={{
            mb: 3,
            borderRadius: '12px',
            bgcolor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Query Execution Failed
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
            {queryError}
          </Typography>
        </Alert>
      )}

      {/* Query Results */}
      {queryResult && queryResult.success && (
        <Paper
          sx={{
            p: 3,
            borderRadius: '16px',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(0, 0, 0, 0.2) 100%)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <SuccessIcon size={24} color="#10B981" />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
              Query Results
            </Typography>
            <Chip
              label={`${queryResult.row_count} rows`}
              size="small"
              sx={{
                bgcolor: 'rgba(16, 185, 129, 0.2)',
                color: '#10B981',
                fontWeight: 700,
                fontSize: '0.75rem',
              }}
            />
            {(() => {
              const hasOrderBy = /\bORDER\s+BY\b/i.test(query);
              return (
                <Tooltip 
                  title={hasOrderBy 
                    ? "Results are sorted according to your ORDER BY clause" 
                    : "Results are in database order. Add ORDER BY to your query to sort."} 
                  arrow
                >
                  <Chip
                    label={hasOrderBy ? "Sorted by query" : "Database order"}
                    size="small"
                    icon={<InfoIcon size={14} />}
                    sx={{
                      bgcolor: hasOrderBy ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                      color: hasOrderBy ? '#10B981' : '#60A5FA',
                      fontSize: '0.7rem',
                      cursor: 'help',
                      '& .MuiChip-icon': {
                        color: hasOrderBy ? '#10B981' : '#60A5FA',
                      },
                    }}
                  />
                </Tooltip>
              );
            })()}
            <Box sx={{ ml: 'auto' }}>
              <Button
                size="small"
                variant="outlined"
                startIcon={<DownloadIcon size={16} />}
                onClick={handleExportCSV}
                sx={{
                  textTransform: 'none',
                  borderColor: 'rgba(16, 185, 129, 0.3)',
                  color: '#10B981',
                  '&:hover': {
                    borderColor: '#10B981',
                    bgcolor: 'rgba(16, 185, 129, 0.1)',
                  },
                }}
              >
                Export CSV
              </Button>
            </Box>
          </Box>

          <TableContainer
            sx={{
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              bgcolor: 'rgba(0, 0, 0, 0.4)',
              maxHeight: 500,
            }}
          >
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {queryResult.columns.map((col, idx) => (
                    <TableCell
                      key={idx}
                      sx={{
                        background: 'rgba(16, 185, 129, 0.50)',
                        backdropFilter: 'blur(24px) saturate(200%) brightness(1.1)',
                        WebkitBackdropFilter: 'blur(24px) saturate(200%) brightness(1.1)',
                        borderBottom: '2px solid rgba(16, 185, 129, 0.6)',
                        color: '#D1FAE5',
                        fontWeight: 700,
                        fontSize: '0.8rem',
                        whiteSpace: 'nowrap',
                        position: 'sticky',
                        top: 0,
                        zIndex: 10,
                        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 2px 16px rgba(16, 185, 129, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
                      }}
                    >
                      {col}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {queryResult.rows
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((row, rowIdx) => (
                    <TableRow
                      key={rowIdx}
                      sx={{
                        '&:hover': {
                          bgcolor: 'rgba(255, 255, 255, 0.05)',
                        },
                      }}
                    >
                      {row.map((cell, cellIdx) => {
                        let displayValue: React.ReactNode;
                        if (cell === null || cell === undefined) {
                          displayValue = (
                            <span style={{ color: 'rgba(255, 255, 255, 0.4)', fontStyle: 'italic' }}>null</span>
                          );
                        } else if (typeof cell === 'boolean') {
                          displayValue = (
                            <span style={{ color: cell ? '#10B981' : '#EF4444', fontWeight: 600 }}>
                              {String(cell)}
                            </span>
                          );
                        } else if (typeof cell === 'number') {
                          displayValue = <span style={{ color: '#60A5FA' }}>{cell}</span>;
                        } else {
                          displayValue = String(cell);
                        }

                        const cellString = cell === null || cell === undefined ? 'null' : String(cell);
                        const isLongContent = cellString.length > 50;

                        return (
                          <Tooltip 
                            key={cellIdx} 
                            title={isLongContent ? cellString : ''} 
                            arrow
                            componentsProps={{
                              tooltip: {
                                sx: {
                                  bgcolor: 'rgba(15, 23, 42, 0.98)',
                                  backdropFilter: 'blur(12px)',
                                  border: '1px solid rgba(255, 255, 255, 0.1)',
                                  borderRadius: '8px',
                                  fontSize: '0.75rem',
                                  maxWidth: '400px',
                                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
                                },
                              },
                              arrow: {
                                sx: {
                                  color: 'rgba(15, 23, 42, 0.98)',
                                  '&::before': {
                                    border: '1px solid rgba(255, 255, 255, 0.1)',
                                  },
                                },
                              },
                            }}
                          >
                            <TableCell
                              sx={{
                                color: 'rgba(255, 255, 255, 0.9)',
                                fontSize: '0.8rem',
                                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                                maxWidth: '300px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                cursor: isLongContent ? 'help' : 'default',
                              }}
                            >
                              {displayValue}
                            </TableCell>
                          </Tooltip>
                        );
                      })}
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={queryResult.rows.length}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[10, 25, 50, 100]}
            sx={{
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'rgba(255, 255, 255, 0.7)',
              '& .MuiTablePagination-select': {
                color: '#10B981',
              },
            }}
          />
        </Paper>
      )}
    </Box>
  );
};
