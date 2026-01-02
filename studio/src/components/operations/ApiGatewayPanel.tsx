import React, { useState } from 'react';
import { Box, Typography, Paper, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { TrendingUp as TrendingUpIcon, TrendingDown as TrendingDownIcon } from '@mui/icons-material';

export const ApiGatewayPanel: React.FC = () => {
  const [timeframe, setTimeframe] = useState<'5m' | '1h' | '24h'>('5m');

  // Mock data - replace with actual API calls
  const requestData = [
    { time: '10:00', requests: 120, errors: 2 },
    { time: '10:05', requests: 145, errors: 1 },
    { time: '10:10', requests: 132, errors: 3 },
    { time: '10:15', requests: 158, errors: 0 },
    { time: '10:20', requests: 142, errors: 1 },
    { time: '10:25', requests: 167, errors: 2 },
  ];

  const topEndpoints = [
    { path: '/api/v1/conversation', requests: 1247, avgLatency: 45, errorRate: 0.2 },
    { path: '/api/v1/memory-album', requests: 856, avgLatency: 32, errorRate: 0.1 },
    { path: '/api/v1/kg/nodes', requests: 634, avgLatency: 78, errorRate: 0.3 },
    { path: '/api/v1/auth/session', requests: 423, avgLatency: 12, errorRate: 0.0 },
    { path: '/api/v1/scheduler/jobs', requests: 312, avgLatency: 56, errorRate: 0.5 },
  ];

  const totalRequests = requestData.reduce((sum, d) => sum + d.requests, 0);
  const totalErrors = requestData.reduce((sum, d) => sum + d.errors, 0);
  const errorRate = ((totalErrors / totalRequests) * 100).toFixed(2);

  return (
    <Paper
      sx={{
        p: 3,
        borderRadius: '20px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'divider',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.1em',
            color: 'text.secondary',
          }}
        >
          API Gateway
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {(['5m', '1h', '24h'] as const).map((tf) => (
            <Chip
              key={tf}
              label={tf}
              size="small"
              onClick={() => setTimeframe(tf)}
              sx={{
                bgcolor: timeframe === tf ? 'rgba(184, 161, 234, 0.15)' : 'rgba(255,255,255,0.05)',
                color: timeframe === tf ? '#B8A1EA' : 'text.secondary',
                fontWeight: timeframe === tf ? 700 : 500,
                fontSize: '0.7rem',
                cursor: 'pointer',
                '&:hover': {
                  bgcolor: 'rgba(184, 161, 234, 0.1)',
                },
              }}
            />
          ))}
        </Box>
      </Box>

      {/* KPIs */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Requests/sec
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
              {(totalRequests / 6).toFixed(0)}
            </Typography>
            <TrendingUpIcon sx={{ fontSize: 16, color: '#10B981' }} />
          </Box>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Error Rate
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: errorRate === '0.00' ? '#10B981' : '#F59E0B' }}>
              {errorRate}%
            </Typography>
            {errorRate === '0.00' ? (
              <TrendingDownIcon sx={{ fontSize: 16, color: '#10B981' }} />
            ) : (
              <TrendingUpIcon sx={{ fontSize: 16, color: '#F59E0B' }} />
            )}
          </Box>
        </Box>
      </Box>

      {/* Request Chart - Placeholder for D3 implementation */}
      <Box sx={{ 
        mb: 3, 
        height: 180, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '12px',
        border: '1px solid rgba(255, 255, 255, 0.08)'
      }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          Request Chart - D3 Implementation Coming Soon
        </Typography>
      </Box>

      {/* Top Endpoints Table */}
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
        TOP ENDPOINTS
      </Typography>
      <TableContainer sx={{ flex: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: 'text.secondary', fontSize: '0.65rem', fontWeight: 600, borderColor: 'rgba(255,255,255,0.08)' }}>
                PATH
              </TableCell>
              <TableCell align="right" sx={{ color: 'text.secondary', fontSize: '0.65rem', fontWeight: 600, borderColor: 'rgba(255,255,255,0.08)' }}>
                REQUESTS
              </TableCell>
              <TableCell align="right" sx={{ color: 'text.secondary', fontSize: '0.65rem', fontWeight: 600, borderColor: 'rgba(255,255,255,0.08)' }}>
                LATENCY
              </TableCell>
              <TableCell align="right" sx={{ color: 'text.secondary', fontSize: '0.65rem', fontWeight: 600, borderColor: 'rgba(255,255,255,0.08)' }}>
                ERROR %
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {topEndpoints.map((endpoint) => (
              <TableRow
                key={endpoint.path}
                sx={{
                  '&:hover': { bgcolor: 'rgba(184, 161, 234, 0.05)' },
                  cursor: 'pointer',
                }}
              >
                <TableCell sx={{ fontSize: '0.75rem', borderColor: 'rgba(255,255,255,0.08)', fontFamily: 'monospace' }}>
                  {endpoint.path}
                </TableCell>
                <TableCell align="right" sx={{ fontSize: '0.75rem', borderColor: 'rgba(255,255,255,0.08)', fontWeight: 600 }}>
                  {endpoint.requests.toLocaleString()}
                </TableCell>
                <TableCell align="right" sx={{ fontSize: '0.75rem', borderColor: 'rgba(255,255,255,0.08)' }}>
                  {endpoint.avgLatency}ms
                </TableCell>
                <TableCell align="right" sx={{ fontSize: '0.75rem', borderColor: 'rgba(255,255,255,0.08)' }}>
                  <Chip
                    label={`${endpoint.errorRate}%`}
                    size="small"
                    sx={{
                      bgcolor: endpoint.errorRate === 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                      color: endpoint.errorRate === 0 ? '#10B981' : '#F59E0B',
                      fontSize: '0.65rem',
                      height: 18,
                      fontWeight: 600,
                    }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};
