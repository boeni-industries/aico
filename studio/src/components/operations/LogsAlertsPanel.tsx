import React, { useState } from 'react';
import { Box, Typography, Paper, Chip, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Error as ErrorIcon, Warning as WarningIcon, Info as InfoIcon, BugReport as DebugIcon } from '@mui/icons-material';

export const LogsAlertsPanel: React.FC = () => {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [serviceFilter, setServiceFilter] = useState<string>('all');

  // Mock data - replace with actual API calls
  const logEvents = [
    { id: 1, service: 'gateway', severity: 'error', message: 'Connection timeout to modelservice', timestamp: '2m ago' },
    { id: 2, service: 'scheduler', severity: 'warning', message: 'Queue utilization above 80%', timestamp: '5m ago' },
    { id: 3, service: 'memory', severity: 'info', message: 'Consolidation completed: 234 segments', timestamp: '8m ago' },
    { id: 4, service: 'modelservice', severity: 'error', message: 'Model loading failed: timeout', timestamp: '12m ago' },
    { id: 5, service: 'bus', severity: 'warning', message: 'Backlog detected on scheduler.jobs', timestamp: '15m ago' },
    { id: 6, service: 'gateway', severity: 'info', message: 'Health check passed', timestamp: '18m ago' },
  ];

  const severityConfig = {
    error: { icon: ErrorIcon, color: '#EF4444', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.3)' },
    warning: { icon: WarningIcon, color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)' },
    info: { icon: InfoIcon, color: '#3B82F6', bg: 'rgba(59, 130, 246, 0.12)', border: 'rgba(59, 130, 246, 0.3)' },
    debug: { icon: DebugIcon, color: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.12)', border: 'rgba(139, 92, 246, 0.3)' },
  };

  const filteredLogs = logEvents.filter(log => {
    const matchesSeverity = severityFilter === 'all' || log.severity === severityFilter;
    const matchesService = serviceFilter === 'all' || log.service === serviceFilter;
    return matchesSeverity && matchesService;
  });

  const errorCount = logEvents.filter(l => l.severity === 'error').length;
  const warningCount = logEvents.filter(l => l.severity === 'warning').length;

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
          Logs & Alerts
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            icon={<ErrorIcon sx={{ fontSize: 14 }} />}
            label={errorCount}
            size="small"
            sx={{
              bgcolor: 'rgba(239, 68, 68, 0.12)',
              color: '#EF4444',
              fontWeight: 700,
              fontSize: '0.7rem',
              height: 24,
            }}
          />
          <Chip
            icon={<WarningIcon sx={{ fontSize: 14 }} />}
            label={warningCount}
            size="small"
            sx={{
              bgcolor: 'rgba(245, 158, 11, 0.12)',
              color: '#F59E0B',
              fontWeight: 700,
              fontSize: '0.7rem',
              height: 24,
            }}
          />
        </Box>
      </Box>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>Severity</InputLabel>
          <Select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            label="Severity"
            sx={{
              fontSize: '0.75rem',
              bgcolor: 'rgba(255,255,255,0.05)',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.12)' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(184, 161, 234, 0.5)' },
            }}
          >
            <MenuItem value="all" sx={{ fontSize: '0.75rem' }}>All</MenuItem>
            <MenuItem value="error" sx={{ fontSize: '0.75rem' }}>Error</MenuItem>
            <MenuItem value="warning" sx={{ fontSize: '0.75rem' }}>Warning</MenuItem>
            <MenuItem value="info" sx={{ fontSize: '0.75rem' }}>Info</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>Service</InputLabel>
          <Select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            label="Service"
            sx={{
              fontSize: '0.75rem',
              bgcolor: 'rgba(255,255,255,0.05)',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.12)' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(184, 161, 234, 0.5)' },
            }}
          >
            <MenuItem value="all" sx={{ fontSize: '0.75rem' }}>All Services</MenuItem>
            <MenuItem value="gateway" sx={{ fontSize: '0.75rem' }}>Gateway</MenuItem>
            <MenuItem value="modelservice" sx={{ fontSize: '0.75rem' }}>Model Service</MenuItem>
            <MenuItem value="scheduler" sx={{ fontSize: '0.75rem' }}>Scheduler</MenuItem>
            <MenuItem value="memory" sx={{ fontSize: '0.75rem' }}>Memory</MenuItem>
            <MenuItem value="bus" sx={{ fontSize: '0.75rem' }}>Message Bus</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Log Events */}
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
        RECENT EVENTS ({filteredLogs.length})
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, overflow: 'auto' }}>
        {filteredLogs.map((log) => {
          const config = severityConfig[log.severity as keyof typeof severityConfig];
          const SeverityIcon = config.icon;
          return (
            <Box
              key={log.id}
              sx={{
                p: 1.5,
                borderRadius: '12px',
                bgcolor: 'rgba(255,255,255,0.03)',
                border: '1px solid',
                borderColor: config.border,
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: config.bg,
                  borderColor: config.color,
                },
                cursor: 'pointer',
              }}
            >
              <Box
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '8px',
                  bgcolor: config.bg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <SeverityIcon sx={{ fontSize: 14, color: config.color }} />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                  <Chip
                    label={log.service}
                    size="small"
                    sx={{
                      bgcolor: 'rgba(255,255,255,0.05)',
                      color: 'text.secondary',
                      fontSize: '0.6rem',
                      height: 16,
                      fontWeight: 500,
                    }}
                  />
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                    {log.timestamp}
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ fontSize: '0.75rem', display: 'block', lineHeight: 1.4 }}>
                  {log.message}
                </Typography>
              </Box>
            </Box>
          );
        })}
      </Box>

      {/* Storage Status */}
      <Box
        sx={{
          mt: 2,
          p: 1.5,
          borderRadius: '12px',
          bgcolor: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
            Log Storage
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#10B981' }}>
            2.3 GB / 10 GB
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};
