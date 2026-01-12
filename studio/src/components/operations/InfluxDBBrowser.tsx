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
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Play as PlayIcon,
  Copy as CopyIcon,
  Download as DownloadIcon,
  CheckCircle as SuccessIcon,
  AlertCircle as ErrorIcon,
  Clock as ClockIcon,
  TrendingUp as TrendingUpIcon,
} from 'lucide-react';
import { CodeEditor } from '../common/CodeEditor';
import { httpJson } from '../../api/http';

interface InfluxDBBrowserProps {
  color: string;
}

interface QueryResult {
  success: boolean;
  error?: string;
  columns: string[];
  rows: any[][];
  row_count: number;
}

const EXAMPLE_QUERIES = [
  {
    name: 'Recent Logs (Last 1h)',
    query: `from(bucket: "aico_telemetry")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "logs")
  |> limit(n: 100)`,
  },
  {
    name: 'API Request Metrics',
    query: `from(bucket: "aico_telemetry")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "api_request")
  |> aggregateWindow(every: 1h, fn: mean)`,
  },
  {
    name: 'Model Inference Stats',
    query: `from(bucket: "aico_telemetry")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "model_inference")
  |> group(columns: ["model_name"])
  |> count()`,
  },
  {
    name: 'System Metrics (CPU/Memory)',
    query: `from(bucket: "aico_telemetry")
  |> range(start: -6h)
  |> filter(fn: (r) => r._measurement == "system_metrics")
  |> filter(fn: (r) => r._field == "cpu_percent" or r._field == "memory_percent")`,
  },
  {
    name: 'List All Measurements',
    query: `import "influxdata/influxdb/schema"
schema.measurements(bucket: "aico_telemetry")`,
  },
];

export const InfluxDBBrowser: React.FC<InfluxDBBrowserProps> = ({ color }) => {
  const [query, setQuery] = useState(EXAMPLE_QUERIES[0].query);
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [selectedExample, setSelectedExample] = useState(0);

  const handleExecuteQuery = async () => {
    if (!query.trim()) return;

    setIsExecuting(true);
    setQueryError(null);
    setQueryResult(null);
    setPage(0);

    try {
      const result = await httpJson<QueryResult>({
        method: 'POST',
        path: 'http://localhost:8771/api/v1/operations/databases/influxdb/query',
        body: { query },
      });

      if (result.success) {
        setQueryResult(result);
      } else {
        setQueryError(result.error || 'Query execution failed');
      }
    } catch (error: any) {
      console.error('[InfluxDB] Query execution failed:', error);
      setQueryError(error.message || 'Failed to execute query');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCopyQuery = () => {
    navigator.clipboard.writeText(query);
  };

  const handleExampleChange = (index: number) => {
    setSelectedExample(index);
    setQuery(EXAMPLE_QUERIES[index].query);
    setQueryResult(null);
    setQueryError(null);
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
    link.download = `influxdb-query-results-${new Date().toISOString().slice(0, 10)}.csv`;
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

  const paginatedRows = queryResult?.rows?.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  ) || [];

  return (
    <Box>
      {/* Query Examples Selector */}
      <Box sx={{ mb: 2 }}>
        <FormControl fullWidth size="small">
          <InputLabel>Example Queries</InputLabel>
          <Select
            value={selectedExample}
            label="Example Queries"
            onChange={(e) => handleExampleChange(e.target.value as number)}
            sx={{
              bgcolor: `${color}08`,
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: `${color}30`,
              },
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: `${color}50`,
              },
            }}
          >
            {EXAMPLE_QUERIES.map((example, index) => (
              <MenuItem key={index} value={index}>
                {example.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Query Editor */}
      <Paper
        sx={{
          mb: 2,
          borderRadius: '8px',
          border: '1px solid',
          borderColor: `${color}30`,
          overflow: 'hidden',
        }}
      >
        <Box sx={{ p: 1.5, bgcolor: `${color}08`, borderBottom: '1px solid', borderColor: `${color}20` }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color }}>
            Flux Query Editor
          </Typography>
          <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', fontSize: '0.65rem', mt: 0.5 }}>
            Execute Flux queries on "aico_telemetry" database
          </Typography>
        </Box>
        <CodeEditor
          value={query}
          onChange={setQuery}
          language="flux"
          placeholder="Enter your Flux query here..."
          height="150px"
        />
      </Paper>

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={isExecuting ? <CircularProgress size={16} /> : <PlayIcon size={16} />}
          onClick={handleExecuteQuery}
          disabled={isExecuting || !query.trim()}
          sx={{
            bgcolor: color,
            '&:hover': { bgcolor: `${color}dd` },
            textTransform: 'none',
            fontWeight: 600,
          }}
        >
          Execute Query
        </Button>
        <Button
          variant="outlined"
          startIcon={<CopyIcon size={16} />}
          onClick={handleCopyQuery}
          sx={{
            borderColor: `${color}50`,
            color,
            '&:hover': { borderColor: color, bgcolor: `${color}10` },
            textTransform: 'none',
          }}
        >
          Copy
        </Button>
        {queryResult && (
          <Button
            variant="outlined"
            startIcon={<DownloadIcon size={16} />}
            onClick={handleExportCSV}
            sx={{
              borderColor: `${color}50`,
              color,
              '&:hover': { borderColor: color, bgcolor: `${color}10` },
              textTransform: 'none',
            }}
          >
            Export CSV
          </Button>
        )}
      </Box>

      {/* Query Results */}
      {queryError && (
        <Alert
          severity="error"
          icon={<ErrorIcon size={18} />}
          sx={{
            mb: 2,
            borderRadius: '8px',
            bgcolor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Query Execution Failed
          </Typography>
          <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
            {queryError}
          </Typography>
        </Alert>
      )}

      {queryResult && (
        <Paper
          sx={{
            borderRadius: '8px',
            border: '1px solid',
            borderColor: `${color}30`,
            overflow: 'hidden',
          }}
        >
          {/* Results Header */}
          <Box
            sx={{
              p: 1.5,
              bgcolor: `${color}08`,
              borderBottom: '1px solid',
              borderColor: `${color}20`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SuccessIcon size={16} color={color} />
              <Typography variant="caption" sx={{ fontWeight: 600, color }}>
                Query Results
              </Typography>
              <Chip
                label={`${queryResult.row_count} rows`}
                size="small"
                sx={{
                  bgcolor: `${color}20`,
                  color,
                  fontSize: '0.65rem',
                  height: 20,
                  fontWeight: 600,
                }}
              />
            </Box>
            {queryResult.row_count === 0 && (
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
                No data found for the specified time range
              </Typography>
            )}
          </Box>

          {/* Results Table */}
          {queryResult.row_count > 0 && (
            <>
              <TableContainer sx={{ maxHeight: 400 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      {queryResult.columns.map((column) => (
                        <TableCell
                          key={column}
                          sx={{
                            bgcolor: `${color}10`,
                            fontWeight: 600,
                            fontSize: '0.7rem',
                            borderBottom: '2px solid',
                            borderColor: `${color}30`,
                            color,
                          }}
                        >
                          {column}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {paginatedRows.map((row, rowIndex) => (
                      <TableRow
                        key={rowIndex}
                        sx={{
                          '&:hover': { bgcolor: `${color}05` },
                          '&:nth-of-type(even)': { bgcolor: `${color}03` },
                        }}
                      >
                        {row.map((cell, cellIndex) => (
                          <TableCell
                            key={cellIndex}
                            sx={{
                              fontSize: '0.7rem',
                              fontFamily: 'monospace',
                              maxWidth: 300,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {cell === null || cell === undefined ? (
                              <Typography
                                variant="caption"
                                sx={{ color: 'text.disabled', fontStyle: 'italic' }}
                              >
                                null
                              </Typography>
                            ) : (
                              String(cell)
                            )}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={queryResult.row_count}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                rowsPerPageOptions={[10, 25, 50, 100]}
                sx={{
                  borderTop: '1px solid',
                  borderColor: `${color}20`,
                  bgcolor: `${color}05`,
                }}
              />
            </>
          )}
        </Paper>
      )}
    </Box>
  );
};
