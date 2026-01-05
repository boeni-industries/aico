import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  IconButton,
  Collapse,
  LinearProgress,
  Tooltip,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Bug,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  Search,
  Filter,
  Download,
  RefreshCw,
  FileText,
  TrendingUp,
  TrendingDown,
  Activity,
  Database,
  Clock,
  Zap,
  Copy,
  Check,
} from 'lucide-react';
import { getLogEvents, getLogKPIs, getLogHistogram, LogEvent as ApiLogEvent, LogKPIs as ApiLogKPIs, HistogramDataPoint as ApiHistogramDataPoint } from '../../api/logs';

interface LogEvent {
  id: string;
  timestamp: string;
  severity: 'error' | 'warning' | 'info' | 'debug';
  service: string;
  message: string;
  details?: string;
  stackTrace?: string;
  metadata?: Record<string, any>;
}

interface LogKPIs {
  errorRate: number;
  errorRateTrend: number;
  logVolume: number;
  logVolumeTrend: number;
  errorDistribution: { error: number; warning: number; info: number; debug: number };
  serviceHealth: number;
  mttd: number;
  storageUsage: number;
  storageTotal: number;
  topErrorSource: string;
  errorVelocity: number;
  logLatency: number;
}

interface LogsEventsProps {
  refreshTrigger?: number;
}

// Copy Button Component
const CopyButton: React.FC<{ event: any; config: any }> = ({ event, config }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async (e: React.MouseEvent) => {
    e.stopPropagation();
    
    // Format the log entry for copying
    const logData = {
      timestamp: event.timestamp,
      level: event.severity,
      service: event.service,
      message: event.message,
      ...(event.metadata && { metadata: event.metadata }),
      ...(event.details && { details: event.details }),
      ...(event.stackTrace && { stackTrace: event.stackTrace }),
    };
    
    const formatted = JSON.stringify(logData, null, 2);
    
    try {
      await navigator.clipboard.writeText(formatted);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <Tooltip title={copied ? "Copied!" : "Copy log entry"}>
      <IconButton
        size="small"
        onClick={copyToClipboard}
        sx={{
          color: copied ? config.color : 'text.secondary',
          opacity: 0,
          transition: 'opacity 0.2s',
          p: 0.5,
          '.MuiBox-root:hover &': {
            opacity: 1,
          },
        }}
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </IconButton>
    </Tooltip>
  );
};

export const LogsEvents: React.FC<LogsEventsProps> = ({ refreshTrigger = 0 }) => {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [isUserInteracting, setIsUserInteracting] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string[]>(['error', 'warning', 'info', 'debug']);
  const [serviceFilter, setServiceFilter] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState<'5m' | '1h' | '24h' | '7d'>('1h');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [kpis, setKpis] = useState<ApiLogKPIs | null>(null);
  const [logEvents, setLogEvents] = useState<ApiLogEvent[]>([]);
  const [histogramData, setHistogramData] = useState<ApiHistogramDataPoint[]>([]);
  
  // Caching and pre-fetching (cache key includes filters)
  const cacheRef = useRef<Map<string, ApiLogEvent[]>>(new Map());
  const prefetchRef = useRef<Set<number>>(new Set());
  const autoRefreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastFetchTimeRef = useRef<number>(Date.now());

  // Pre-fetch adjacent pages for instant pagination
  const prefetchPage = useCallback(async (pageNum: number) => {
    // Use "ALL" when all 4 levels selected to distinguish from filtered state
    const filterKey = severityFilter.length === 4 ? 'ALL' : severityFilter.join(',');
    const cacheKey = `${pageNum}-${filterKey}-${searchQuery}`;
    if (prefetchRef.current.has(pageNum) || cacheRef.current.has(cacheKey)) return;
    
    prefetchRef.current.add(pageNum);
    try {
      const offset = (pageNum - 1) * pageSize;
      const eventsData = await getLogEvents({
        limit: pageSize,
        offset: offset,
        level: severityFilter.length === 4 ? undefined : severityFilter.map(s => s.toUpperCase()).join(','),
        search: searchQuery || undefined,
      });
      cacheRef.current.set(cacheKey, eventsData.logs || []);
    } catch (error) {
      console.error(`Failed to prefetch page ${pageNum}:`, error);
    } finally {
      prefetchRef.current.delete(pageNum);
    }
  }, [pageSize, severityFilter, searchQuery]);

  // Load data from API with intelligent caching
  const loadData = useCallback(async (forceRefresh = false) => {
    // Build cache key including filters to avoid stale data
    const filterKey = severityFilter.length === 4 ? 'ALL' : severityFilter.join(',');
    const cacheKey = `${page}-${filterKey}-${searchQuery}`;
    
    // Check cache first for instant loading
    if (!forceRefresh && cacheRef.current.has(cacheKey)) {
      setLogEvents(cacheRef.current.get(cacheKey)!);
      
      // Pre-fetch adjacent pages in background
      setTimeout(() => {
        prefetchPage(page + 1);
        if (page > 1) prefetchPage(page - 1);
      }, 100);
      return;
    }

    setLoading(true);
    try {
      // Fetch KPIs and histogram only on initial load or force refresh
      if (forceRefresh || !kpis) {
        const [kpisData, histData] = await Promise.all([
          getLogKPIs(),
          getLogHistogram(24)
        ]);
        setKpis(kpisData);
        setHistogramData(histData);
      }

      // Fetch log events - admin API uses limit/offset instead of page/page_size
      const offset = (page - 1) * pageSize;
      const eventsData = await getLogEvents({
        limit: pageSize,
        offset: offset,
        level: severityFilter.length === 4 ? undefined : severityFilter.map(s => s.toUpperCase()).join(','),
        search: searchQuery || undefined,
      });
      
      // Admin API returns { logs, total, has_more }
      const logs = eventsData.logs || [];
      setLogEvents(logs);
      setTotalCount(eventsData.total || 0);
      
      // Cache the result with filter key
      const filterKey = severityFilter.length === 4 ? 'ALL' : severityFilter.join(',');
      const cacheKey = `${page}-${filterKey}-${searchQuery}`;
      cacheRef.current.set(cacheKey, logs);
      
      // Limit cache size to 10 pages (500 entries)
      if (cacheRef.current.size > 10) {
        const oldestKey = Array.from(cacheRef.current.keys())[0];
        cacheRef.current.delete(oldestKey);
      }
      
      // Pre-fetch adjacent pages in background
      setTimeout(() => {
        prefetchPage(page + 1);
        if (page > 1) prefetchPage(page - 1);
      }, 100);
      
      lastFetchTimeRef.current = Date.now();
    } catch (error) {
      console.error('Failed to load log data:', error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, severityFilter, searchQuery, kpis, prefetchPage]);

  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);

  // Smart auto-refresh: only refresh KPIs and new logs, not entire page
  useEffect(() => {
    const startAutoRefresh = () => {
      autoRefreshTimerRef.current = setInterval(async () => {
        // Skip refresh if user is interacting
        if (page === 1 && !isUserInteracting) {
          try {
            // Fetch only KPIs and check for new logs without disrupting UI
            const [kpisData, eventsData] = await Promise.all([
              getLogKPIs(),
              getLogEvents({ limit: pageSize, offset: 0, level: severityFilter.length === 4 ? undefined : severityFilter.map(s => s.toUpperCase()).join(','), search: searchQuery || undefined })
            ]);
            
            setKpis(kpisData);
            
            // Only update if there are new logs (compare first log ID)
            const currentFirstId = logEvents[0]?.id;
            const newFirstId = eventsData.logs?.[0]?.id;
            if (newFirstId && newFirstId !== currentFirstId) {
              setLogEvents(eventsData.logs || []);
              setTotalCount(eventsData.total || 0);
              const filterKey = severityFilter.length === 4 ? 'ALL' : severityFilter.join(',');
              const cacheKey = `1-${filterKey}-${searchQuery}`;
              cacheRef.current.set(cacheKey, eventsData.logs || []);
            }
          } catch (error) {
            console.error('Auto-refresh failed:', error);
          }
        }
      }, 10000); // Refresh every 10 seconds (less disruptive)
    };

    startAutoRefresh();

    return () => {
      if (autoRefreshTimerRef.current) {
        clearInterval(autoRefreshTimerRef.current);
      };
    }
  }, [page, pageSize, severityFilter, searchQuery, logEvents, isUserInteracting, expandedRows]);

  // Clear cache and reset to page 1 when filters change
  useEffect(() => {
    cacheRef.current.clear();
    prefetchRef.current.clear();
    setPage(1);
  }, [severityFilter, searchQuery]);

  // Format number with commas
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  // Format percentage with 2 decimals
  const formatPercent = (num: number): string => {
    return num.toFixed(2);
  };

  // Format bytes to human readable
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Default KPIs while loading
  const defaultKpis: ApiLogKPIs = {
    error_rate: 0,
    error_rate_trend: 0,
    log_volume: 0,
    log_volume_trend: 0,
    error_distribution: { error: 0, warning: 0, info: 0, debug: 0 },
    service_health: 100,
    mttd: 0,
    storage_usage: 0,
    storage_total: 10,
    top_error_source: 'none',
    error_velocity: 0,
    log_latency: 0,
  };

  // Map KPIs to display format with correct property names
  const displayKpis = useMemo(() => {
    if (!kpis) return defaultKpis;
    return {
      error_rate: kpis.error_rate,
      error_rate_trend: kpis.error_rate_trend,
      log_volume: kpis.log_volume,
      log_volume_trend: kpis.log_volume_trend,
      error_distribution: kpis.error_distribution,
      service_health: kpis.service_health,
      mttd: kpis.mttd,
      storage_usage: kpis.storage_usage,
      storage_total: kpis.storage_total,
      top_error_source: kpis.top_error_source,
      error_velocity: kpis.error_velocity,
      log_latency: kpis.log_latency,
    };
  }, [kpis]);

  // Calculate max value for histogram scaling with logarithmic scale
  const maxHistogramValue = useMemo(() => {
    if (histogramData.length === 0) return 100;
    const maxValue = Math.max(...histogramData.map(h => h.error + h.warning + h.info + h.debug), 1);
    // Use log scale for better visualization of small values
    return Math.log10(maxValue + 1);
  }, [histogramData]);

  // Map API events to display format
  const displayEvents = useMemo(() => {
    return logEvents.map(event => ({
      ...event,
      severity: event.level,
      service: event.subsystem || event.module,
      details: event.extra_data?.details,
      stackTrace: event.extra_data?.stack_trace,
      metadata: event.extra_data,
      hasExpandableContent: !!(event.extra_data && Object.keys(event.extra_data).length > 0),
    }));
  }, [logEvents]);

  const toggleRow = (id: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const severityConfig = {
    error: { icon: AlertCircle, color: '#EF4444', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.3)' },
    warning: { icon: AlertTriangle, color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)' },
    info: { icon: Info, color: '#3B82F6', bg: 'rgba(59, 130, 246, 0.12)', border: 'rgba(59, 130, 246, 0.3)' },
    debug: { icon: Bug, color: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.12)', border: 'rgba(139, 92, 246, 0.3)' },
  };

  // Format timestamp for display - fixed width format
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${day}.${month}.${year} - ${hours}:${minutes}`;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI Cards Row - 3 columns to match Scheduler & Jobs layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
        {/* Error Rate */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 32, height: 32, borderRadius: '10px', bgcolor: 'rgba(239, 68, 68, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertCircle size={16} color="#EF4444" />
              </Box>
              <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Error Rate
              </Typography>
              <Tooltip title={
                <Box sx={{ p: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>Error Rate</Typography>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>Percentage of log entries at ERROR level</Typography>
                  <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.7)' }}>Lower is better. Trend shows change vs last hour.</Typography>
                </Box>
              } arrow placement="top">
                <Box component="span" sx={{ display: 'inline-flex', cursor: 'help' }}>
                  <HelpCircle size={14} color="rgba(255,255,255,0.4)" />
                </Box>
              </Tooltip>
            </Box>
            {displayKpis.error_rate_trend < 0 ? (
              <TrendingDown size={16} color="#10B981" />
            ) : (
              <TrendingUp size={16} color="#EF4444" />
            )}
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary', mt: 1 }}>
            {formatPercent(displayKpis.error_rate)}%
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.5, display: 'block' }}>
            {displayKpis.error_rate_trend > 0 ? '+' : ''}{displayKpis.error_rate_trend}% vs last hour
          </Typography>
        </Paper>

        {/* Log Volume */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 32, height: 32, borderRadius: '10px', bgcolor: 'rgba(59, 130, 246, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Activity size={16} color="#3B82F6" />
              </Box>
              <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Volume
              </Typography>
              <Tooltip title={
                <Box sx={{ p: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>Log Volume</Typography>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>Total number of log entries in the system</Typography>
                  <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.7)' }}>Tracks system activity level. Trend shows growth rate.</Typography>
                </Box>
              } arrow placement="top">
                <Box component="span" sx={{ display: 'inline-flex', cursor: 'help' }}>
                  <HelpCircle size={14} color="rgba(255,255,255,0.4)" />
                </Box>
              </Tooltip>
            </Box>
            <TrendingUp size={16} color="#3B82F6" />
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary', mt: 1 }}>
            {formatNumber(displayKpis.log_volume)}
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.5, display: 'block' }}>
            +{displayKpis.log_volume_trend}% vs last hour
          </Typography>
        </Paper>

        {/* Service Health */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 32, height: 32, borderRadius: '10px', bgcolor: 'rgba(16, 185, 129, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Zap size={16} color="#10B981" />
              </Box>
              <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Health
              </Typography>
              <Tooltip title={
                <Box sx={{ p: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>Service Health</Typography>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>Percentage of services operating without errors</Typography>
                  <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255,255,255,0.7)' }}>100% means all services are error-free. Based on recent log patterns.</Typography>
                </Box>
              } arrow placement="top">
                <Box component="span" sx={{ display: 'inline-flex', cursor: 'help' }}>
                  <HelpCircle size={14} color="rgba(255,255,255,0.4)" />
                </Box>
              </Tooltip>
            </Box>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary', mt: 1 }}>
            {formatPercent(displayKpis.service_health)}%
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.5, display: 'block' }}>
            Error-free services
          </Typography>
        </Paper>

      </Box>

      {/* Timeline Histogram */}
      <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em', color: 'text.secondary' }}>
            Event Timeline (24h)
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 12, height: 12, borderRadius: '3px', bgcolor: '#EF4444' }} />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>Error</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 12, height: 12, borderRadius: '3px', bgcolor: '#F59E0B' }} />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>Warning</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 12, height: 12, borderRadius: '3px', bgcolor: '#3B82F6' }} />
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>Info</Typography>
            </Box>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 0.5, height: 120 }}>
          {histogramData.length > 0 ? histogramData.map((data, idx) => {
            if (!data) return null;
            const total = (data.error || 0) + (data.warning || 0) + (data.info || 0) + (data.debug || 0);
            // Use logarithmic scale for better visualization
            const logTotal = Math.log10(total + 1);
            const height = maxHistogramValue > 0 ? (logTotal / maxHistogramValue) * 100 : 0;
            // Ensure minimum height for visibility
            const minHeight = total > 0 ? 2 : 0;
            const actualHeight = Math.max(height, minHeight);
            const errorHeight = total > 0 ? ((data.error || 0) / total) * actualHeight : 0;
            const warningHeight = total > 0 ? ((data.warning || 0) / total) * actualHeight : 0;
            const infoHeight = total > 0 ? ((data.info || 0) / total) * actualHeight : 0;
            
            return (
              <Tooltip
                key={idx}
                title={
                  <Box>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
                      {data.hour.toString().padStart(2, '0')}:00
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#EF4444' }}>
                        Errors: {data.error}
                      </Typography>
                      <br />
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#F59E0B' }}>
                        Warnings: {data.warning}
                      </Typography>
                      <br />
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#3B82F6' }}>
                        Info: {data.info}
                      </Typography>
                    </Box>
                  </Box>
                }
                arrow
              >
                <Box
                  sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'flex-end',
                    height: '100%',
                    cursor: 'pointer',
                    '&:hover': {
                      opacity: 0.8,
                    },
                  }}
                >
                  <Box
                    sx={{
                      width: '100%',
                      height: `${height}%`,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'flex-end',
                      borderRadius: '4px 4px 0 0',
                      overflow: 'hidden',
                    }}
                  >
                    <Box sx={{ height: `${errorHeight}%`, bgcolor: '#EF4444' }} />
                    <Box sx={{ height: `${warningHeight}%`, bgcolor: '#F59E0B' }} />
                    <Box sx={{ height: `${infoHeight}%`, bgcolor: '#3B82F6' }} />
                  </Box>
                </Box>
              </Tooltip>
            );
          }) : (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
              <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                No data available
              </Typography>
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, px: 0.5 }}>
          <Typography variant="caption" sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
            {histogramData.length > 0 && histogramData[0] ? histogramData[0].hour.toString().padStart(2, '0') + ':00' : '00:00'}
          </Typography>
          <Typography variant="caption" sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
            Now
          </Typography>
        </Box>
      </Paper>

      {/* Event List */}
      <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em', color: 'text.secondary' }}>
            Event Log
          </Typography>
        </Box>

        {/* Search and Filters */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
          <TextField
            size="small"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={16} color="rgba(255,255,255,0.5)" />
                </InputAdornment>
              ),
            }}
            sx={{
              flex: 1,
              minWidth: 200,
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(255,255,255,0.03)',
                fontSize: '0.8rem',
                '& fieldset': { borderColor: 'rgba(255,255,255,0.12)' },
                '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.5)' },
              },
            }}
          />
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {(['error', 'warning', 'info', 'debug'] as const).map((severity) => {
              const config = severityConfig[severity];
              const SeverityIcon = config.icon;
              const isActive = severityFilter.includes(severity);
              return (
                <Chip
                  key={severity}
                  icon={<SeverityIcon size={14} />}
                  label={severity}
                  size="small"
                  onClick={() => {
                    setSeverityFilter(prev => {
                      // Prevent deselecting the last level (must have at least 1)
                      if (isActive && prev.length === 1) return prev;
                      return isActive ? prev.filter(s => s !== severity) : [...prev, severity];
                    });
                  }}
                  sx={{
                    bgcolor: isActive ? config.bg : 'rgba(255,255,255,0.05)',
                    color: isActive ? config.color : 'text.secondary',
                    border: `1px solid ${isActive ? config.border : 'rgba(255,255,255,0.12)'}`,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      bgcolor: config.bg,
                      borderColor: config.color,
                    },
                  }}
                />
              );
            })}
          </Box>
        </Box>

        {/* Event Table */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {displayEvents.map((event) => {
            const severityKey = event.severity.toLowerCase() as 'error' | 'warning' | 'info' | 'debug';
            const config = severityConfig[severityKey];
            const SeverityIcon = config.icon;
            const isExpanded = expandedRows.has(event.id);

            return (
              <Box
                key={event.id}
                onMouseEnter={() => setIsUserInteracting(true)}
                onMouseLeave={() => setIsUserInteracting(false)}
                sx={{
                  borderRadius: '12px',
                  bgcolor: 'rgba(255,255,255,0.05)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid',
                  borderColor: isExpanded ? config.color : 'rgba(255,255,255,0.15)',
                  overflow: 'hidden',
                  transition: 'all 0.2s',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.08)',
                    borderColor: config.border,
                    boxShadow: '0 6px 12px rgba(0,0,0,0.15)',
                  },
                }}
              >
                {/* Main Row - Ultra Compact */}
                <Box
                  onClick={() => toggleRow(event.id)}
                  sx={{
                    p: 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    cursor: 'pointer',
                  }}
                >
                  {/* Expand Icon */}
                  <IconButton size="small" sx={{ color: 'text.secondary', p: 0, width: 20, height: 20 }}>
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </IconButton>

                  {/* Severity Icon */}
                  <Box
                    sx={{
                      width: 24,
                      height: 24,
                      borderRadius: '6px',
                      bgcolor: config.bg,
                      border: `1px solid ${config.border}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <SeverityIcon size={14} color={config.color} />
                  </Box>

                  {/* Timestamp - Fixed Width */}
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', fontFamily: 'monospace', minWidth: 135, flexShrink: 0 }}>
                    {formatTimestamp(event.timestamp)}
                  </Typography>

                  {/* Metadata Indicator - Fixed Width Column */}
                  <Box sx={{ width: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {event.hasExpandableContent && (
                      <FileText size={12} color={config.color} style={{ opacity: 0.5 }} />
                    )}
                  </Box>

                  {/* Service Badge - Fixed Width */}
                  <Chip
                    label={event.service}
                    size="small"
                    sx={{
                      bgcolor: 'rgba(184, 161, 234, 0.12)',
                      color: '#B8A1EA',
                      border: '1px solid rgba(184, 161, 234, 0.3)',
                      fontSize: '0.6rem',
                      fontWeight: 600,
                      height: 18,
                      minWidth: 100,
                      maxWidth: 100,
                      textTransform: 'capitalize',
                      flexShrink: 0,
                      '& .MuiChip-label': { px: 0.75, py: 0, overflow: 'hidden', textOverflow: 'ellipsis' },
                    }}
                  />

                  {/* Message - Truncated */}
                  <Typography
                    variant="body2"
                    sx={{
                      flex: 1,
                      maxWidth: '600px',
                      fontSize: '0.7rem',
                      lineHeight: 1.3,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      color: 'rgba(255,255,255,0.9)',
                    }}
                  >
                    {event.message.length > 120 ? `${event.message.substring(0, 120)}...` : event.message}
                  </Typography>

                  {/* Copy Button - Appears on Hover */}
                  <CopyButton event={event} config={config} />
                </Box>

                {/* Expanded Details */}
                <Collapse in={isExpanded}>
                  <Box
                    sx={{
                      p: 2,
                      pt: 0,
                      borderTop: '1px solid rgba(255,255,255,0.08)',
                      bgcolor: 'rgba(0,0,0,0.2)',
                    }}
                  >
                    {/* Full Message */}
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5, display: 'block' }}>
                        Full Message
                      </Typography>
                      <Typography variant="body2" sx={{ fontSize: '0.75rem', lineHeight: 1.6, color: 'rgba(255,255,255,0.9)', wordBreak: 'break-word' }}>
                        {event.message}
                      </Typography>
                    </Box>

                    {/* Details */}
                    {event.details && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5, display: 'block' }}>
                          Details
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', lineHeight: 1.6, color: 'rgba(255,255,255,0.9)' }}>
                          {event.details}
                        </Typography>
                      </Box>
                    )}

                    {/* Metadata */}
                    {event.metadata && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5, display: 'block' }}>
                          Metadata
                        </Typography>
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: '8px',
                            bgcolor: 'rgba(0,0,0,0.3)',
                            border: '1px solid rgba(255,255,255,0.08)',
                            fontFamily: 'monospace',
                            fontSize: '0.7rem',
                          }}
                        >
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <Box key={key} sx={{ display: 'flex', gap: 1, mb: 0.5 }}>
                              <Typography component="span" sx={{ color: '#8B5CF6', fontWeight: 600 }}>
                                {key}:
                              </Typography>
                              <Typography component="span" sx={{ color: '#10B981' }}>
                                {JSON.stringify(value)}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    )}

                    {/* Stack Trace */}
                    {event.stackTrace && (
                      <Box>
                        <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.05em', mb: 0.5, display: 'block' }}>
                          Stack Trace
                        </Typography>
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: '8px',
                            bgcolor: 'rgba(0,0,0,0.3)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            fontFamily: 'monospace',
                            fontSize: '0.7rem',
                            color: '#EF4444',
                            maxHeight: 200,
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {event.stackTrace}
                        </Box>
                      </Box>
                    )}
                  </Box>
                </Collapse>
              </Box>
            );
          })}
        </Box>

        {/* Pagination Footer */}
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
            Showing {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, totalCount)} of {totalCount.toLocaleString()} events
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Box component="span">
              <IconButton 
                size="small" 
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                sx={{ color: 'text.secondary', '&:disabled': { opacity: 0.3 } }}
              >
                <ChevronRight size={16} style={{ transform: 'rotate(180deg)' }} />
              </IconButton>
            </Box>
            <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', minWidth: 80, textAlign: 'center' }}>
              Page {page} of {Math.ceil(totalCount / pageSize).toLocaleString()}
            </Typography>
            <Box component="span">
              <IconButton 
                size="small"
                disabled={page >= Math.ceil(totalCount / pageSize)}
                onClick={() => setPage(p => p + 1)}
                sx={{ color: 'text.secondary', '&:disabled': { opacity: 0.3 } }}
              >
                <ChevronRight size={16} />
              </IconButton>
            </Box>
          </Box>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
            Auto-refresh: 5s
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};
