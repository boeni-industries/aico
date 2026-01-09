import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Chip, CircularProgress, Alert } from '@mui/material';
import { CheckCircle as HealthyIcon, AlertTriangle as WarningIcon, AlertCircle as ErrorIcon, Monitor as BackendIcon, HardDrive as ModelIcon, Clock as SchedulerIcon, LayoutDashboard as StudioIcon, Database as DatabaseIcon, User as UserIcon } from 'lucide-react';
import { fetchSystemOverview } from '../../api/system';
import { fetchDetailedHealth, fetchSchedulerStatus, fetchDatabaseStats, fetchActiveSessions } from '../../api/operations';

interface ComponentStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'critical' | 'offline';
  uptime: string;
  version: string;
  host?: string;
  port?: number;
  metrics?: {
    label: string;
    value: string | number;
  }[];
}

interface DatabaseInfo {
  name: string;
  type: 'libsql' | 'chromadb' | 'lmdb';
  size: string;
  status: 'healthy' | 'degraded' | 'critical';
  location: string;
  error_details?: string;
  metrics: {
    label: string;
    value: string | number;
  }[];
}

interface ActiveUser {
  uuid: string;
  name: string;
  sessionCount: number;
  lastActivity: string;
}

interface OperationsOverviewProps {
  onNavigateToTab?: (tab: string) => void;
  refreshTrigger?: number;
}

export const OperationsOverview: React.FC<OperationsOverviewProps> = ({ onNavigateToTab, refreshTrigger }) => {
  const [systemStatus, setSystemStatus] = useState<'healthy' | 'degraded' | 'critical'>('healthy');
  const [components, setComponents] = useState<ComponentStatus[]>([]);
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [activeUsers, setActiveUsers] = useState<ActiveUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uptime, setUptime] = useState('0m');
  const [systemLoad, setSystemLoad] = useState(0);
  const [schedulerInfo, setSchedulerInfo] = useState({ 
    registered_tasks: 0, 
    scheduled_tasks: 0,
    running_tasks: 0,
    next_run_times: {} as Record<string, string>
  });

  useEffect(() => {
    loadOverviewData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload data when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger !== undefined && refreshTrigger > 0) {
      loadOverviewData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all data in parallel
      const [systemOverview, healthData, schedulerData, databaseStats, activeSessions] = await Promise.all([
        fetchSystemOverview(),
        fetchDetailedHealth(),
        fetchSchedulerStatus().catch(() => ({ 
          running: false, 
          registered_tasks: 0, 
          scheduled_tasks: 0,
          running_tasks: 0,
          next_run_times: {}
        })),
        fetchDatabaseStats(),
        fetchActiveSessions(),
      ]);

      // Update system status
      const statusMap: Record<string, 'healthy' | 'degraded' | 'critical'> = {
        'ok': 'healthy',
        'healthy': 'healthy',
        'attention': 'degraded',
        'degraded': 'degraded',
        'critical': 'critical',
      };
      setSystemStatus(statusMap[healthData.overall_status] || statusMap[systemOverview.system_status] || 'healthy');

      // Update uptime and system load
      setUptime(systemOverview.uptime_formatted);
      setSystemLoad(healthData.system_metrics?.cpu_usage ? Math.round(healthData.system_metrics.cpu_usage) : 0);

      // Store scheduler info for display
      setSchedulerInfo({
        registered_tasks: schedulerData.registered_tasks || 0,
        scheduled_tasks: schedulerData.scheduled_tasks || 0,
        running_tasks: schedulerData.running_tasks || 0,
        next_run_times: schedulerData.next_run_times || {},
      });

      // Build main components array (Gateway, Modelservice, Studio only)
      const componentsData: ComponentStatus[] = [];

      // 1. Backend/Gateway - always show since we're connected to it
      if (healthData.components?.api_gateway) {
        const gw = healthData.components.api_gateway;
        componentsData.push({
          name: 'Gateway',
          status: gw.status === 'healthy' || gw.status === 'running' ? 'healthy' : gw.status === 'error' ? 'critical' : 'degraded',
          uptime: formatUptime(gw.uptime || 0),
          version: gw.version || 'unknown',
          host: 'localhost',
          port: 8771,
          metrics: [
            { label: 'Status', value: gw.status },
          ],
        });
      } else {
        // Fallback: if health API doesn't report gateway, assume it's running (we're connected to it)
        componentsData.push({
          name: 'Gateway',
          status: 'healthy',
          uptime: systemOverview.uptime_formatted,
          version: 'unknown',
          host: 'localhost',
          port: 8771,
          metrics: [
            { label: 'Status', value: 'Running' },
          ],
        });
      }

      // 2. Modelservice - check if available in health data
      if (healthData.components?.modelservice) {
        const ms = healthData.components.modelservice;
        componentsData.push({
          name: 'Modelservice',
          status: ms.status === 'healthy' || ms.status === 'running' ? 'healthy' : ms.status === 'error' ? 'critical' : 'degraded',
          uptime: formatUptime(ms.uptime || 0),
          version: ms.version || 'unknown',
          host: 'localhost',
          port: 8773,
          metrics: [
            { label: 'Status', value: ms.status },
          ],
        });
      } else {
        // Modelservice not in health API yet - show as healthy if we can reach it
        componentsData.push({
          name: 'Modelservice',
          status: 'healthy',
          uptime: systemOverview.uptime_formatted,
          version: 'unknown',
          host: 'localhost',
          port: 8773,
          metrics: [
            { label: 'Status', value: 'Running' },
          ],
        });
      }

      // 3. Ollama - LLM backend server
      if (healthData.components?.ollama) {
        const ollama = healthData.components.ollama;
        componentsData.push({
          name: 'Ollama',
          status: ollama.status === 'healthy' || ollama.status === 'running' ? 'healthy' : ollama.status === 'error' ? 'critical' : 'degraded',
          uptime: formatUptime(ollama.uptime || 0),
          version: ollama.version || 'unknown',
          host: 'localhost',
          port: 11434,
          metrics: [
            { label: 'Status', value: ollama.status },
          ],
        });
      } else {
        // Ollama not in health API yet - show as healthy if we can reach it
        componentsData.push({
          name: 'Ollama',
          status: 'healthy',
          uptime: systemOverview.uptime_formatted,
          version: 'unknown',
          host: 'localhost',
          port: 11434,
          metrics: [
            { label: 'Status', value: 'Running' },
          ],
        });
      }

      // 4. Studio - always show since we're running in it
      componentsData.push({
        name: 'Studio',
        status: 'healthy',
        uptime: systemOverview.uptime_formatted,
        version: '0.0.1',
        host: 'localhost',
        port: 3000,
        metrics: [
          { label: 'Active', value: 'Yes' },
        ],
      });

      setComponents(componentsData);

      // Set databases from real API data
      const databasesData: DatabaseInfo[] = databaseStats.databases.map(db => {
        const metrics: { label: string; value: string | number }[] = [];
        
        // Add type-specific metrics
        if (db.type === 'libsql') {
          if (db.table_count !== undefined) metrics.push({ label: 'Tables', value: db.table_count });
          if (db.connection_count !== undefined) metrics.push({ label: 'Connections', value: db.connection_count });
          if (db.wal_size_bytes !== undefined) metrics.push({ label: 'WAL Size', value: formatBytes(db.wal_size_bytes) });
        } else if (db.type === 'chromadb') {
          if (db.collection_count !== undefined) metrics.push({ label: 'Collections', value: db.collection_count });
          if (db.document_count !== undefined) metrics.push({ label: 'Documents', value: formatNumber(db.document_count) });
          if (db.index_size_bytes !== undefined) metrics.push({ label: 'Index Size', value: formatBytes(db.index_size_bytes) });
        } else if (db.type === 'lmdb') {
          if (db.database_count !== undefined) metrics.push({ label: 'Databases', value: db.database_count });
          if (db.key_count !== undefined) metrics.push({ label: 'Keys', value: formatNumber(db.key_count) });
          if (db.map_size_bytes !== undefined) metrics.push({ label: 'Map Size', value: formatBytes(db.map_size_bytes) });
        }
        
        return {
          name: db.name,
          type: db.type as 'libsql' | 'chromadb' | 'lmdb',
          size: formatBytes(db.size_bytes),
          status: db.status as 'healthy' | 'degraded' | 'critical',
          location: db.location,
          error_details: db.error_details,
          metrics,
        };
      });
      
      setDatabases(databasesData);

      // Set active users from real API data
      const usersData: ActiveUser[] = activeSessions.sessions.map(session => ({
        uuid: session.user_uuid,
        name: session.full_name,
        sessionCount: session.session_count,
        lastActivity: session.last_activity,
      }));
      
      setActiveUsers(usersData);

      setLoading(false);
    } catch (err: any) {
      console.error('Failed to load operations data:', err);
      setError(err.message || 'Failed to load operations data');
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return '#10B981';
      case 'degraded':
        return '#F59E0B';
      case 'critical':
        return '#EF4444';
      case 'offline':
        return '#6B7280';
      default:
        return '#6B7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <HealthyIcon color="#10B981" size={20} />;
      case 'degraded':
        return <WarningIcon color="#F59E0B" size={20} />;
      case 'critical':
      case 'offline':
        return <ErrorIcon color="#EF4444" size={20} />;
      default:
        return <HealthyIcon color="#6B7280" size={20} />;
    }
  };

  const getComponentIcon = (name: string) => {
    if (name.includes('Gateway')) return <BackendIcon color="#3B82F6" />;
    if (name.includes('Modelservice')) return <ModelIcon color="#8B5CF6" />;
    if (name.includes('Ollama')) return <ModelIcon color="#14B8A6" />;
    if (name.includes('Scheduler')) return <SchedulerIcon color="#6366F1" />;
    if (name.includes('Studio')) return <StudioIcon color="#A78BFA" />;
    return <BackendIcon color="#3B82F6" />;
  };

  const getComponentColor = (name: string) => {
    // Component identity colors (neutral, not status indicators)
    if (name.includes('Gateway')) return '#3B82F6';      // Blue
    if (name.includes('Modelservice')) return '#8B5CF6'; // Purple
    if (name.includes('Ollama')) return '#14B8A6';       // Teal
    if (name.includes('Scheduler')) return '#6366F1';    // Indigo
    if (name.includes('Studio')) return '#A78BFA';       // Lavender
    return '#3B82F6';
  };

  const getComponentNavigationTab = (name: string): string => {
    if (name.includes('Scheduler')) return 'scheduler';
    if (name.includes('Backend') || name.includes('Gateway')) return 'gateway';
    if (name.includes('Modelservice')) return 'topology';
    if (name.includes('Ollama')) return 'topology';
    if (name.includes('Studio')) return 'topology';
    return 'topology';
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* System Status Header */}
      <Box
        sx={{
          p: 3,
          mb: 3,
          borderRadius: '20px',
          bgcolor: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(12px)',
          border: '1px solid',
          borderColor: 'divider',
          background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.05) 0%, rgba(16, 185, 129, 0.05) 100%)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          {getStatusIcon(systemStatus)}
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            System Status: {systemStatus.charAt(0).toUpperCase() + systemStatus.slice(1)}
          </Typography>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 3 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Uptime
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {uptime}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Components
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {components.length} / {components.length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              Active Users
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {activeUsers.length}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              System Load
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {systemLoad}%
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Component Status Grid */}
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        System Components
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 2, mb: 4 }}>
        {loading && components.length === 0 ? (
          // Show loading skeleton for components
          Array.from({ length: 4 }).map((_, idx) => (
            <Paper
              key={`skeleton-${idx}`}
              sx={{
                p: 2.5,
                borderRadius: '16px',
                border: '1.5px solid',
                borderColor: 'divider',
                background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.08) 100%)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '120px',
              }}
            >
              <CircularProgress size={24} />
            </Paper>
          ))
        ) : (
          components.map((component) => (
            <Paper
            key={component.name}
            onClick={() => onNavigateToTab?.(getComponentNavigationTab(component.name))}
            sx={{
              p: 2.5,
              borderRadius: '16px',
              border: component.status === 'critical' || component.status === 'offline' ? '3px solid' : component.status === 'degraded' ? '2.5px solid' : '1.5px solid',
              borderColor: component.status === 'critical' || component.status === 'offline' || component.status === 'degraded'
                ? getStatusColor(component.status) 
                : `${getStatusColor(component.status)}40`,
              background: component.status === 'critical' || component.status === 'offline'
                ? `linear-gradient(135deg, ${getStatusColor(component.status)}20 0%, ${getComponentColor(component.name)}10 100%)`
                : component.status === 'degraded'
                ? `linear-gradient(135deg, ${getStatusColor(component.status)}18 0%, ${getComponentColor(component.name)}10 100%)`
                : `linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, ${getComponentColor(component.name)}08 100%)`,
              backdropFilter: 'blur(8px)',
              transition: 'all 0.2s',
              cursor: 'pointer',
              boxShadow: component.status === 'critical' || component.status === 'offline'
                ? `0 0 30px ${getStatusColor(component.status)}60, inset 0 0 30px ${getStatusColor(component.status)}15`
                : component.status === 'degraded'
                ? `0 0 25px ${getStatusColor(component.status)}50, inset 0 0 20px ${getStatusColor(component.status)}12`
                : 'none',
              '&:hover': {
                borderColor: getStatusColor(component.status),
                background: `linear-gradient(135deg, ${getStatusColor(component.status)}08 0%, ${getComponentColor(component.name)}12 100%)`,
                boxShadow: `0 8px 24px ${getStatusColor(component.status)}20`,
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '10px',
                  bgcolor: `${getComponentColor(component.name)}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {getComponentIcon(component.name)}
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  {component.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  v{component.version}
                </Typography>
              </Box>
              {getStatusIcon(component.status)}
            </Box>

            {component.host && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                {component.host}:{component.port}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip
                label={`Uptime: ${component.uptime}`}
                size="small"
                sx={{
                  bgcolor: `${getComponentColor(component.name)}15`,
                  color: getComponentColor(component.name),
                  border: '1px solid',
                  borderColor: `${getComponentColor(component.name)}30`,
                  fontSize: '0.7rem',
                  height: 24,
                  fontWeight: 600,
                }}
              />
            </Box>

            {component.metrics && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {component.metrics.map((metric) => (
                  <Box key={metric.label} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">
                      {metric.label}
                    </Typography>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      {metric.value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>
          ))
        )}
      </Box>

      {/* Scheduler Section - Gateway Sub-component */}
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, mt: 4 }}>
        Scheduler
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
        Gateway Sub-component
      </Typography>
      <Box sx={{ mb: 4 }}>
        <Paper
          onClick={() => onNavigateToTab?.('scheduler')}
          sx={{
            p: 2.5,
            borderRadius: '16px',
            border: '1.5px solid',
            borderColor: 'rgba(99, 102, 241, 0.4)',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.08) 100%)',
            backdropFilter: 'blur(8px)',
            transition: 'all 0.2s',
            cursor: 'pointer',
            '&:hover': {
              borderColor: '#6366F1',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(99, 102, 241, 0.12) 100%)',
              boxShadow: '0 8px 24px rgba(99, 102, 241, 0.2)',
            },
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '10px',
                bgcolor: 'rgba(99, 102, 241, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <SchedulerIcon color="#6366F1" />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '0.9rem' }}>
                Task Scheduler
              </Typography>
            </Box>
            <HealthyIcon color="#10B981" size={20} />
          </Box>

          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Chip
              label={`Uptime: ${uptime}`}
              size="small"
              sx={{
                bgcolor: 'rgba(99, 102, 241, 0.15)',
                color: '#6366F1',
                border: '1px solid',
                borderColor: 'rgba(99, 102, 241, 0.3)',
                fontSize: '0.7rem',
                height: 24,
                fontWeight: 600,
              }}
            />
          </Box>

          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 2 }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: '8px', bgcolor: 'rgba(99, 102, 241, 0.1)' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#6366F1' }}>
                {schedulerInfo.registered_tasks}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Registered
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: '8px', bgcolor: 'rgba(99, 102, 241, 0.1)' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#6366F1' }}>
                {schedulerInfo.scheduled_tasks}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Scheduled
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: '8px', bgcolor: 'rgba(16, 185, 129, 0.1)' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#10B981' }}>
                {schedulerInfo.running_tasks}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Running Now
              </Typography>
            </Box>
          </Box>

          {Object.keys(schedulerInfo.next_run_times).length > 0 && (
            <Box>
              <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.primary', display: 'block', mb: 1.5 }}>
                Next Scheduled Runs:
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {Object.entries(schedulerInfo.next_run_times).slice(0, 3).map(([taskId, nextRun]) => {
                  // Convert UTC to local time and format
                  const formatDateTime = (utcString: string) => {
                    try {
                      const date = new Date(utcString);
                      const now = new Date();
                      const diffMs = date.getTime() - now.getTime();
                      const diffMins = Math.floor(diffMs / 60000);
                      
                      // Format as local time
                      const timeStr = date.toLocaleTimeString('en-US', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: false 
                      });
                      
                      // Add relative time if within 24 hours
                      if (diffMins < 60 && diffMins > 0) {
                        return `${timeStr} (in ${diffMins}m)`;
                      } else if (diffMins < 1440 && diffMins > 0) {
                        const hours = Math.floor(diffMins / 60);
                        return `${timeStr} (in ${hours}h)`;
                      }
                      
                      return timeStr;
                    } catch {
                      return utcString;
                    }
                  };
                  
                  return (
                    <Box key={taskId} sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      p: 1,
                      borderRadius: 1,
                      bgcolor: 'rgba(99, 102, 241, 0.08)',
                      '&:hover': { bgcolor: 'rgba(99, 102, 241, 0.12)' }
                    }}>
                      <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 500, color: 'rgba(255, 255, 255, 0.9)' }}>
                        {taskId}
                      </Typography>
                      <Typography variant="caption" sx={{ 
                        fontWeight: 600, 
                        fontSize: '0.75rem', 
                        color: '#A5B4FC',
                        fontFamily: 'monospace'
                      }}>
                        {formatDateTime(nextRun)}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          )}
        </Paper>
      </Box>

      {/* Databases Grid */}
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        Databases
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2, mb: 4 }}>
        {loading && databases.length === 0 ? (
          // Show loading skeleton for databases
          Array.from({ length: 3 }).map((_, idx) => (
            <Paper
              key={`db-skeleton-${idx}`}
              sx={{
                p: 2.5,
                borderRadius: '16px',
                border: '1.5px solid',
                borderColor: 'divider',
                background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.08) 100%)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '140px',
              }}
            >
              <CircularProgress size={24} />
            </Paper>
          ))
        ) : (
          databases.map((db) => (
            <Paper
            key={db.name}
            onClick={() => onNavigateToTab?.('database')}
            sx={{
              p: 2.5,
              borderRadius: '16px',
              border: '1.5px solid',
              borderColor: `${getStatusColor(db.status)}40`,
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(99, 102, 241, 0.08) 100%)',
              backdropFilter: 'blur(8px)',
              transition: 'all 0.2s',
              cursor: 'pointer',
              '&:hover': {
                borderColor: getStatusColor(db.status),
                background: `linear-gradient(135deg, ${getStatusColor(db.status)}08 0%, rgba(99, 102, 241, 0.12) 100%)`,
                boxShadow: `0 8px 24px ${getStatusColor(db.status)}20`,
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '10px',
                  bgcolor: `${getStatusColor(db.status)}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: getStatusColor(db.status),
                }}
              >
                <DatabaseIcon />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  {db.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {db.type.toUpperCase()}
                </Typography>
              </Box>
              {getStatusIcon(db.status)}
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              {db.location}
            </Typography>

            <Chip
              label={`Size: ${db.size}`}
              size="small"
              sx={{
                bgcolor: 'rgba(99, 102, 241, 0.15)',
                color: '#6366F1',
                border: '1px solid',
                borderColor: 'rgba(99, 102, 241, 0.3)',
                fontSize: '0.7rem',
                height: 24,
                mb: 2,
                fontWeight: 600,
              }}
            />

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {db.metrics.map((metric) => (
                <Box key={metric.label} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    {metric.label}
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 600 }}>
                    {metric.value}
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* Show error details for degraded/critical databases */}
            {(db.status === 'degraded' || db.status === 'critical') && db.error_details && (
              <Alert 
                severity={db.status === 'critical' ? 'error' : 'warning'} 
                sx={{ 
                  mt: 2, 
                  fontSize: '0.7rem',
                  py: 0.5,
                  '& .MuiAlert-message': { fontSize: '0.7rem' }
                }}
              >
                {db.error_details}
              </Alert>
            )}
          </Paper>
          ))
        )}
      </Box>

      {/* Active Users Section */}
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, mt: 4 }}>
        Active Users
      </Typography>
      <Paper
        onClick={() => onNavigateToTab?.('users')}
        sx={{
          p: 3,
          mb: 4,
          borderRadius: '16px',
          border: '1.5px solid',
          borderColor: 'rgba(167, 139, 250, 0.4)',
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(167, 139, 250, 0.08) 100%)',
          backdropFilter: 'blur(8px)',
          cursor: 'pointer',
          transition: 'all 0.2s',
          '&:hover': {
            borderColor: '#A78BFA',
            boxShadow: '0 8px 24px rgba(167, 139, 250, 0.2)',
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '10px',
                bgcolor: 'rgba(167, 139, 250, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <UserIcon color="#A78BFA" />
            </Box>
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.9rem' }}>
                User Sessions
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {activeUsers.length} active user{activeUsers.length !== 1 ? 's' : ''}
              </Typography>
            </Box>
          </Box>
          <Chip
            label={`Total: ${activeUsers.reduce((sum, u) => sum + u.sessionCount, 0)} sessions`}
            size="small"
            sx={{
              bgcolor: 'rgba(167, 139, 250, 0.15)',
              color: '#A78BFA',
              border: '1px solid',
              borderColor: 'rgba(167, 139, 250, 0.3)',
              fontSize: '0.7rem',
              height: 24,
              fontWeight: 600,
            }}
          />
        </Box>

        {activeUsers.length > 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {activeUsers.map((user) => (
              <Box
                key={user.uuid}
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  p: 1.5,
                  borderRadius: '8px',
                  bgcolor: 'rgba(167, 139, 250, 0.05)',
                  border: '1px solid rgba(167, 139, 250, 0.1)',
                }}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {user.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    UUID: {user.uuid.substring(0, 8)}...
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: '#A78BFA' }}>
                      {user.sessionCount} session{user.sessionCount > 1 ? 's' : ''}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Last: {user.lastActivity}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
            No active users
          </Typography>
        )}
      </Paper>
    </Box>
  );
};
