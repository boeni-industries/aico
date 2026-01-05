import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TablePagination,
} from '@mui/material';
import { Play as PlayArrowIcon, CheckCircle as CheckCircleIcon, AlertCircle as ErrorIcon, Hourglass as HourglassEmptyIcon, Pause as PauseIcon, X as CancelIcon, Search as SearchIcon, RefreshCw as RefreshIcon, Download as DownloadIcon, Copy as ContentCopyIcon } from 'lucide-react';
import {
  fetchSchedulerStatus,
  fetchTasks,
  fetchTaskExecutions,
  fetchExecutionsInRange,
  fetchExpectedRunsToday,
  triggerTask,
  type Task,
  type TaskExecution,
  type SchedulerStatus,
} from '../../api/scheduler';
import { useToast } from '../common/Toast';
import { TaskDetailDrawer } from './TaskDetailDrawer';
import { JobDetailDrawer } from './JobDetailDrawer';

interface SchedulerJobsProps {
  refreshTrigger?: number;
}

// Memoized table row component to prevent unnecessary re-renders
const ExecutionRow = React.memo<{
  execution: TaskExecution & { task_id?: string };
  onExecutionClick: (execution: TaskExecution) => void;
  onUserInteraction: () => void;
  onCopyUuid: (uuid: string, e: React.MouseEvent) => void;
}>(({ execution, onExecutionClick, onUserInteraction, onCopyUuid }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />;
      case 'failed':
        return <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />;
      case 'running':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#60A5FA' }} />;
      case 'pending':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#9CA3AF' }} />;
      case 'cancelled':
        return <CancelIcon sx={{ fontSize: 16, color: '#9CA3AF' }} />;
      default:
        return <PauseIcon sx={{ fontSize: 16, color: '#9CA3AF' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10B981';
      case 'failed': return '#EF4444';
      case 'running': return '#60A5FA';
      case 'pending': return '#9CA3AF';
      case 'cancelled': return '#9CA3AF';
      default: return '#9CA3AF';
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatLocalTime = (utcTimeString: string) => {
    // Backend sends UTC time, convert to local
    const date = new Date(utcTimeString + (utcTimeString.includes('Z') ? '' : 'Z'));
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  return (
    <TableRow
      hover
      onClick={() => onExecutionClick(execution)}
      onMouseEnter={onUserInteraction}
      sx={{
        cursor: 'pointer',
        '&:hover': {
          bgcolor: 'rgba(96, 165, 250, 0.05)',
        },
      }}
    >
      <TableCell sx={{ whiteSpace: 'nowrap' }}>
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.85rem', mb: 0.5 }}>
            {execution.task_id || 'Unknown Task'}
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace', fontSize: '0.7rem' }}>
              {execution.execution_id}
            </Typography>
            <IconButton
              size="small"
              onClick={(e) => onCopyUuid(execution.execution_id, e)}
              sx={{ 
                padding: '2px',
                '&:hover': { bgcolor: 'rgba(96, 165, 250, 0.1)' }
              }}
            >
              <ContentCopyIcon sx={{ fontSize: 12 }} />
            </IconButton>
          </Box>
        </Box>
      </TableCell>
      <TableCell sx={{ whiteSpace: 'nowrap' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {getStatusIcon(execution.status)}
          <Chip
            label={execution.status}
            size="small"
            sx={{
              fontSize: '0.7rem',
              height: '20px',
              bgcolor: `${getStatusColor(execution.status)}20`,
              color: getStatusColor(execution.status),
              fontWeight: 500,
              textTransform: 'capitalize',
            }}
          />
        </Box>
      </TableCell>
      <TableCell sx={{ whiteSpace: 'nowrap' }}>
        <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
          {formatLocalTime(execution.started_at)}
        </Typography>
      </TableCell>
      <TableCell sx={{ whiteSpace: 'nowrap' }}>
        <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
          {formatDuration(execution.duration_seconds)}
        </Typography>
      </TableCell>
      <TableCell sx={{ whiteSpace: 'nowrap' }}>
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); onExecutionClick(execution); }}>
          <PlayArrowIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </TableCell>
    </TableRow>
  );
}, (prevProps, nextProps) => {
  // Custom comparison: only re-render if execution data actually changed
  return prevProps.execution.execution_id === nextProps.execution.execution_id &&
         prevProps.execution.status === nextProps.execution.status &&
         prevProps.execution.started_at === nextProps.execution.started_at;
});

ExecutionRow.displayName = 'ExecutionRow';

export const SchedulerJobs: React.FC<SchedulerJobsProps> = ({ refreshTrigger }) => {
  const { showToast } = useToast();
  
  // State
  const [loading, setLoading] = useState(true);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [expectedRunsToday, setExpectedRunsToday] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<'today' | 'last7days'>('today');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  // Drawer state
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<TaskExecution | null>(null);
  const [taskDrawerOpen, setTaskDrawerOpen] = useState(false);
  const [jobDrawerOpen, setJobDrawerOpen] = useState(false);
  const [isUserInteracting, setIsUserInteracting] = useState(false);
  const [hasPendingUpdate, setHasPendingUpdate] = useState(false);
  const interactionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingDataRef = useRef<{
    status: SchedulerStatus;
    tasks: Task[];
    executions: TaskExecution[];
  } | null>(null);

  // Load data
  const loadData = useCallback(async (isBackgroundRefresh = false) => {
    try {
      if (!isBackgroundRefresh) {
        setLoading(true);
      }

      // Calculate time range for last 7 days
      const now = new Date();
      const sevenDaysAgo = new Date(now);
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      
      const [statusData, tasksData, expectedRunsData, executionsData] = await Promise.all([
        fetchSchedulerStatus(),
        fetchTasks(),
        fetchExpectedRunsToday().catch(() => ({ total_expected_runs: 0, task_run_counts: {}, calculated_at: '', period_start: '', period_end: '' })),
        fetchExecutionsInRange(sevenDaysAgo.toISOString(), now.toISOString()).catch(() => ({ executions: [], total_count: 0, start_time: '', end_time: '' })),
      ]);

      const allExecutions = executionsData.executions;
      
      // Sort by started_at descending
      allExecutions.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());

      // If user is interacting, store data for later
      if (isBackgroundRefresh && isUserInteracting) {
        pendingDataRef.current = {
          status: statusData,
          tasks: tasksData.tasks,
          executions: allExecutions,
        };
        setHasPendingUpdate(true);
      } else {
        // Apply updates immediately
        setSchedulerStatus(statusData);
        setTasks(tasksData.tasks);
        setExecutions(allExecutions);
        setExpectedRunsToday(expectedRunsData.total_expected_runs);
        setHasPendingUpdate(false);
        pendingDataRef.current = null;
      }
    } catch (error) {
      console.error('Failed to load scheduler data:', error);
      if (!isBackgroundRefresh) {
        showToast('Failed to load scheduler data', 'error');
      }
    } finally {
      if (!isBackgroundRefresh) {
        setLoading(false);
      }
    }
  }, [showToast, isUserInteracting]);

  // Apply pending updates when user stops interacting (minimal updates only)
  useEffect(() => {
    if (!isUserInteracting && pendingDataRef.current) {
      const pending = pendingDataRef.current;
      
      // Only update status and tasks (non-intrusive)
      setSchedulerStatus(pending.status);
      setTasks(pending.tasks);
      
      // For executions: only add truly new items (by checking both ID and timestamp)
      setExecutions(prev => {
        if (!pending.executions || pending.executions.length === 0) {
          return prev;
        }
        
        const existingMap = new Map(prev.map(e => [e.execution_id, e.started_at]));
        const newItems = pending.executions.filter(e => {
          const existing = existingMap.get(e.execution_id);
          return !existing; // Only truly new executions
        });
        
        // Only update if there are actually new items
        if (newItems.length === 0) {
          return prev; // No change = no re-render
        }
        
        // Prepend new items and limit total
        return [...newItems, ...prev].slice(0, 500);
      });
      
      setHasPendingUpdate(false);
      pendingDataRef.current = null;
    }
  }, [isUserInteracting]);

  // Track user interaction
  const handleUserInteraction = useCallback(() => {
    setIsUserInteracting(true);
    
    if (interactionTimeoutRef.current) {
      clearTimeout(interactionTimeoutRef.current);
    }
    
    interactionTimeoutRef.current = setTimeout(() => {
      setIsUserInteracting(false);
    }, 3000);
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (interactionTimeoutRef.current) {
        clearTimeout(interactionTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      loadData(true); // Background refresh - updates are queued if user is interacting
    }
  }, [refreshTrigger, loadData]);

  // Handle task trigger
  const handleTriggerTask = async (taskId: string) => {
    try {
      const response = await triggerTask(taskId);
      if (response.success) {
        showToast(`Task ${taskId} triggered successfully`, 'success');
        loadData(false);
      } else {
        showToast(response.message || 'Failed to trigger task', 'error');
      }
    } catch (error) {
      console.error('Failed to trigger task:', error);
      showToast('Failed to trigger task', 'error');
    }
  };


  // Handle execution click
  const handleExecutionClick = useCallback((execution: TaskExecution) => {
    setSelectedExecution(execution);
    setJobDrawerOpen(true);
  }, []);

  const handleCopyUuid = useCallback((uuid: string, event: React.MouseEvent) => {
    event.stopPropagation();
    navigator.clipboard.writeText(uuid);
    showToast('UUID copied to clipboard', 'success');
  }, [showToast]);

  // Calculate KPIs - all based on today's data for consistency
  const now = React.useMemo(() => new Date(), []);
  const todayStart = React.useMemo(() => new Date(now.getFullYear(), now.getMonth(), now.getDate()), [now]);
  const last24Hours = React.useMemo(() => new Date(now.getTime() - 24 * 60 * 60 * 1000), [now]);
  
  const executionsToday = executions.filter(e => {
    const startDate = new Date(e.started_at);
    return startDate >= todayStart;
  });
  
  const executionsLast24h = executions.filter(e => {
    const startDate = new Date(e.started_at);
    return startDate >= last24Hours;
  });

  // Helper to check if a job was skipped (check both status and result flag)
  const isJobSkipped = useCallback((exec: TaskExecution): boolean => {
    // Check status first
    if (exec.status === 'skipped' || exec.status === 'deferred') {
      return true;
    }
    // Also check result.skipped flag for tasks that return skipped=true
    if (exec.result && typeof exec.result === 'object' && exec.result.skipped === true) {
      return true;
    }
    return false;
  }, []);
  
  // Categorize jobs correctly:
  // - EXECUTED: Jobs that actually ran and finished (completed or failed, but NOT skipped)
  // - SKIPPED/DEFERRED: Jobs that were intentionally not executed
  // - RUNNING: Jobs currently executing
  // - PENDING/CANCELLED: Other states
  
  // Get jobs that were skipped/deferred (not executed)
  const skippedJobsToday = executionsToday.filter(e => isJobSkipped(e));
  
  // Get jobs that actually executed (completed or failed, excluding skipped)
  const executedJobsToday = executionsToday.filter(e => 
    (e.status === 'completed' || e.status === 'failed') && !isJobSkipped(e)
  );
  
  // Calculate metrics based on EXECUTED jobs only
  const totalExecutionsToday = executionsToday.length; // Total executions today (including skipped)
  const jobsToday = executedJobsToday.length; // Actually executed (completed or failed)
  const successfulJobsToday = executedJobsToday.filter(e => e.status === 'completed').length;
  const failedJobsToday = executedJobsToday.filter(e => e.status === 'failed').length;
  const successRateToday = jobsToday > 0 
    ? Math.round((successfulJobsToday / jobsToday) * 100) 
    : 0;
  const runningJobs = executions.filter(e => e.status === 'running').length;
  
  // Calculate hourly active jobs for last 24 hours (for histogram)
  // Only count jobs that were actually running (status='running') at some point during the hour
  const activeJobsHistogram = React.useMemo(() => {
    const histogram: number[] = new Array(24).fill(0);
    const hourMs = 60 * 60 * 1000;
    
    // For each hour bucket, count how many jobs were running at the END of that hour
    for (let i = 0; i < 24; i++) {
      const bucketEnd = now.getTime() - (24 - i - 1) * hourMs;
      
      // Count jobs that were running at this point in time
      executionsLast24h.forEach(exec => {
        const startTime = new Date(exec.started_at).getTime();
        const endTime = exec.completed_at ? new Date(exec.completed_at).getTime() : now.getTime();
        
        // Job was running at bucketEnd if it started before and ended after (or is still running)
        if (startTime <= bucketEnd && endTime >= bucketEnd) {
          histogram[i]++;
        }
      });
    }
    
    return histogram;
  }, [executionsLast24h, now]);  // eslint-disable-line react-hooks/exhaustive-deps
  
  // Calculate complete job accounting over time (last 7 days)
  const jobAccountingOverTime = React.useMemo(() => {
    const days = 7;
    const dailyStats: {
      date: string;
      scheduled: number;
      completed: number;
      failed: number;
      skipped: number;
      successRate: number;
    }[] = [];
    
    for (let i = days - 1; i >= 0; i--) {
      const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
      const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);
      
      // Get all executions for this day (scheduled = all that started)
      const dayExecutions = executions.filter(e => {
        const startDate = new Date(e.started_at);
        return startDate >= dayStart && startDate < dayEnd;
      });
      
      // Categorize by status
      const completed = dayExecutions.filter(e => e.status === 'completed' && !isJobSkipped(e)).length;
      const failed = dayExecutions.filter(e => e.status === 'failed' && !isJobSkipped(e)).length;
      const skipped = dayExecutions.filter(e => isJobSkipped(e)).length;
      const scheduled = dayExecutions.length; // Total scheduled = all that attempted to run
      const executed = completed + failed;
      
      const successRate = executed > 0 ? Math.round((completed / executed) * 100) : 0;
      
      dailyStats.push({
        date: dayStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        scheduled,
        completed,
        failed,
        skipped,
        successRate
      });
    }
    
    return dailyStats;
  }, [executions, isJobSkipped, now]);  // eslint-disable-line react-hooks/exhaustive-deps
  
  // Get failed jobs with details (status='failed' but NOT skipped)
  const failedJobsDetails = React.useMemo(() => {
    return executedJobsToday
      .filter(e => e.status === 'failed' && !isJobSkipped(e))
      .map(e => ({
        ...e,
        task_name: (e as any).task_id || 'Unknown Task'
      }));
  }, [executedJobsToday, isJobSkipped]);
  
  // Get skipped/deferred jobs (warnings, not errors)
  const skippedJobsDetails = React.useMemo(() => {
    return skippedJobsToday.map(e => ({
      ...e,
      task_name: (e as any).task_id || 'Unknown Task',
      skip_reason: e.result?.message || e.result?.defer_reason || 'Job was skipped'
    }));
  }, [skippedJobsToday]);

  // Filter executions (memoized to prevent recalculation on every render)
  const filteredExecutions = React.useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const sevenDaysAgo = new Date(todayStart);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    return executions.filter(execution => {
      const matchesSearch = searchQuery === '' || 
        execution.execution_id.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || execution.status === statusFilter;
      
      // Date filter: only show today by default
      const executionDate = new Date(execution.started_at + (execution.started_at.includes('Z') ? '' : 'Z'));
      const matchesDate = dateFilter === 'today' 
        ? executionDate >= todayStart
        : executionDate >= sevenDaysAgo;
      
      return matchesSearch && matchesStatus && matchesDate;
    });
  }, [executions, searchQuery, statusFilter, dateFilter]);

  // Paginate (memoized to prevent recalculation)
  const paginatedExecutions = React.useMemo(() => {
    return filteredExecutions.slice(
      page * rowsPerPage,
      page * rowsPerPage + rowsPerPage
    );
  }, [filteredExecutions, page, rowsPerPage]);

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />;
      case 'failed':
        return <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />;
      case 'running':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#60A5FA' }} />;
      case 'pending':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#9CA3AF' }} />;
      case 'skipped':
      case 'deferred':
        return <PauseIcon sx={{ fontSize: 16, color: '#F59E0B' }} />;
      case 'cancelled':
        return <CancelIcon sx={{ fontSize: 16, color: '#6B7280' }} />;
      default:
        return null;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10B981';
      case 'failed': return '#EF4444';
      case 'running': return '#60A5FA';
      case 'pending': return '#9CA3AF';
      case 'skipped':
      case 'deferred': return '#F59E0B';
      case 'cancelled': return '#6B7280';
      default: return '#6B7280';
    }
  };
  
  // Get status label
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed': return 'COMPLETED';
      case 'failed': return 'FAILED';
      case 'running': return 'RUNNING';
      case 'pending': return 'PENDING';
      case 'skipped': return 'SKIPPED';
      case 'deferred': return 'DEFERRED';
      case 'cancelled': return 'CANCELLED';
      default: return status.toUpperCase();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
        {/* Jobs Today */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Executions Today
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 1 }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
              {totalExecutionsToday}
            </Typography>
            <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', fontWeight: 500 }}>
              actual runs
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.5, display: 'block' }}>
            of {expectedRunsToday.toLocaleString()} expected
          </Typography>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, 
            mt: 1.5,
            pt: 1.5,
            borderTop: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 0.5,
              px: 1,
              py: 0.5,
              borderRadius: '6px',
              bgcolor: 'rgba(96, 165, 250, 0.1)',
              border: '1px solid rgba(96, 165, 250, 0.2)'
            }}>
              <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#60A5FA' }}>
                {jobsToday}
              </Typography>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'rgba(96, 165, 250, 0.8)' }}>
                executed
              </Typography>
            </Box>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 0.5,
              px: 1,
              py: 0.5,
              borderRadius: '6px',
              bgcolor: 'rgba(245, 158, 11, 0.1)',
              border: '1px solid rgba(245, 158, 11, 0.2)'
            }}>
              <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#F59E0B' }}>
                {skippedJobsToday.length}
              </Typography>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'rgba(245, 158, 11, 0.8)' }}>
                skipped
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* Failed Jobs Today */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Failed Today
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: failedJobsToday > 0 ? '#EF4444' : 'text.primary' }}>
            {failedJobsToday}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', mt: 0.5, display: 'block' }}>
            {jobsToday > 0 ? Math.round((failedJobsToday / jobsToday) * 100) : 0}% of executions
          </Typography>
        </Paper>

        {/* Success Rate */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Success Rate
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: successRateToday >= 90 ? '#10B981' : successRateToday >= 70 ? '#F59E0B' : '#EF4444' }}>
            {successRateToday}%
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', mt: 0.5, display: 'block' }}>
            {successfulJobsToday}/{jobsToday} completed successfully
          </Typography>
        </Paper>

        {/* Active Jobs with Histogram */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Active Jobs
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 2, mt: 1 }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#60A5FA' }}>
              {runningJobs}
            </Typography>
            {/* Mini Histogram - Last 24 hours */}
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: 0.3, height: 32, mb: 0.5 }}>
              {activeJobsHistogram.map((count, i) => {
                const maxCount = Math.max(...activeJobsHistogram, 1);
                const height = (count / maxCount) * 100;
                return (
                  <Tooltip 
                    key={i} 
                    title={`${count} active ${i === 23 ? 'now' : `${24-i}h ago`}`}
                    componentsProps={{
                      tooltip: {
                        sx: {
                          bgcolor: 'rgba(17, 24, 39, 0.95)',
                          backdropFilter: 'blur(20px)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                        },
                      },
                      arrow: {
                        sx: {
                          color: 'rgba(17, 24, 39, 0.95)',
                          '&::before': {
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                          },
                        },
                      },
                    }}
                    arrow
                  >
                    <Box
                      sx={{
                        flex: 1,
                        height: `${height}%`,
                        minHeight: count > 0 ? '2px' : '0px',
                        bgcolor: i === 23 ? '#60A5FA' : 'rgba(96, 165, 250, 0.4)',
                        borderRadius: '2px',
                        transition: 'all 0.2s',
                        '&:hover': {
                          bgcolor: '#60A5FA',
                        },
                      }}
                    />
                  </Tooltip>
                );
              })}
            </Box>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', mt: 0.5, display: 'block' }}>
            Last 24 hours
          </Typography>
        </Paper>
      </Box>

      {/* Scheduler Status */}
      {schedulerStatus && (
        <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600 }}>
              Scheduler Status
            </Typography>
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">Registered Tasks</Typography>
              <Typography variant="h6">{schedulerStatus.registered_tasks}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Scheduled Tasks</Typography>
              <Typography variant="h6">{schedulerStatus.scheduled_tasks}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Running Tasks</Typography>
              <Typography variant="h6">{schedulerStatus.running_tasks}</Typography>
            </Box>
          </Box>
        </Paper>
      )}

      {/* Job Accounting Over Time - Stacked Column Chart */}
      <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600 }}>
              Execution History (Last 7 Days)
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Daily runs by status • {tasks.length} active tasks • {expectedRunsToday.toLocaleString()} expected runs/day
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 200, px: 2 }}>
          {jobAccountingOverTime.map((day, i) => {
            const maxJobs = Math.max(...jobAccountingOverTime.map(d => d.scheduled), 1);
            
            // Calculate absolute pixel heights for each segment
            // Use 170px max height (leaving 30px for labels)
            const maxHeight = 170;
            const completedPx = day.completed > 0 ? Math.max((day.completed / maxJobs) * maxHeight, 8) : 0;
            const failedPx = day.failed > 0 ? Math.max((day.failed / maxJobs) * maxHeight, 8) : 0;
            const skippedPx = day.skipped > 0 ? Math.max((day.skipped / maxJobs) * maxHeight, 8) : 0;
            
            // Total column height in pixels
            const totalColumnHeight = completedPx + failedPx + skippedPx;
            
            return (
              <Box key={i} sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                <Tooltip 
                  title={
                    <Box sx={{ p: 1 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1, fontSize: '0.85rem' }}>
                        {day.date}
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                        <Typography variant="caption" sx={{ display: 'block', fontSize: '0.75rem', color: '#9CA3AF' }}>
                          <strong>{day.scheduled}</strong> executions
                        </Typography>
                        <Box sx={{ pl: 1, borderLeft: '2px solid rgba(255, 255, 255, 0.1)', display: 'flex', flexDirection: 'column', gap: 0.3 }}>
                          <Typography variant="caption" sx={{ display: 'block', fontSize: '0.75rem', color: '#10B981' }}>
                            ✓ <strong>{day.completed}</strong> completed
                          </Typography>
                          <Typography variant="caption" sx={{ display: 'block', fontSize: '0.75rem', color: '#EF4444' }}>
                            ✗ <strong>{day.failed}</strong> failed
                          </Typography>
                          <Typography variant="caption" sx={{ display: 'block', fontSize: '0.75rem', color: '#F59E0B' }}>
                            ⊘ <strong>{day.skipped}</strong> skipped
                          </Typography>
                        </Box>
                        {day.completed + day.failed > 0 && (
                          <Typography variant="caption" sx={{ display: 'block', fontSize: '0.75rem', mt: 0.5, fontWeight: 600, color: day.successRate >= 90 ? '#10B981' : day.successRate >= 70 ? '#F59E0B' : '#EF4444' }}>
                            {day.successRate}% success rate
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  }
                  componentsProps={{
                    tooltip: {
                      sx: {
                        bgcolor: 'rgba(17, 24, 39, 0.95)',
                        backdropFilter: 'blur(20px)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '8px',
                        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                      },
                    },
                    arrow: {
                      sx: {
                        color: 'rgba(17, 24, 39, 0.95)',
                        '&::before': {
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                        },
                      },
                    },
                  }}
                  arrow
                >
                  <Box
                    sx={{
                      width: '100%',
                      height: `${totalColumnHeight}px`,
                      minHeight: day.scheduled > 0 ? '12px' : '0px',
                      display: 'flex',
                      flexDirection: 'column-reverse',
                      borderRadius: '8px 8px 0 0',
                      overflow: 'hidden',
                      cursor: day.scheduled > 0 ? 'pointer' : 'default',
                      transition: 'all 0.2s',
                      border: day.scheduled > 0 ? '1px solid rgba(255, 255, 255, 0.15)' : 'none',
                      boxShadow: day.scheduled > 0 ? '0 2px 8px rgba(0, 0, 0, 0.3)' : 'none',
                      '&:hover': day.scheduled > 0 ? {
                        transform: 'scaleY(1.05)',
                        border: '1px solid rgba(255, 255, 255, 0.25)',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
                      } : {},
                    }}
                  >
                    {/* Completed segment (bottom - green) */}
                    {day.completed > 0 && (
                      <Box
                        sx={{
                          height: `${(completedPx / totalColumnHeight) * 100}%`,
                          bgcolor: '#10B981',
                          position: 'relative',
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            height: '40%',
                            background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.25), transparent)',
                          },
                        }}
                      />
                    )}
                    {/* Failed segment (middle - red) */}
                    {day.failed > 0 && (
                      <Box
                        sx={{
                          height: `${(failedPx / totalColumnHeight) * 100}%`,
                          bgcolor: '#EF4444',
                          position: 'relative',
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            height: '40%',
                            background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.25), transparent)',
                          },
                        }}
                      />
                    )}
                    {/* Skipped segment (top - yellow) */}
                    {day.skipped > 0 && (
                      <Box
                        sx={{
                          height: `${(skippedPx / totalColumnHeight) * 100}%`,
                          bgcolor: '#F59E0B',
                          borderRadius: '6px 6px 0 0',
                          position: 'relative',
                          '&::after': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            height: '40%',
                            background: 'linear-gradient(to bottom, rgba(255, 255, 255, 0.25), transparent)',
                            borderRadius: '6px 6px 0 0',
                          },
                        }}
                      />
                    )}
                    {/* Empty state - show subtle placeholder */}
                    {day.scheduled === 0 && (
                      <Box
                        sx={{
                          width: '100%',
                          height: '4px',
                          bgcolor: 'rgba(107, 114, 128, 0.15)',
                          borderRadius: '2px',
                        }}
                      />
                    )}
                  </Box>
                </Tooltip>
                <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', fontWeight: 500 }}>
                  {day.date.split(' ')[1]}
                </Typography>
              </Box>
            );
          })}
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 4, mt: 3, pt: 2, borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Box sx={{ width: 16, height: 16, bgcolor: '#10B981', borderRadius: '4px', border: '1px solid rgba(255, 255, 255, 0.2)', boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)' }} />
            <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.primary', fontWeight: 500 }}>Completed</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Box sx={{ width: 16, height: 16, bgcolor: '#EF4444', borderRadius: '4px', border: '1px solid rgba(255, 255, 255, 0.2)', boxShadow: '0 2px 4px rgba(239, 68, 68, 0.3)' }} />
            <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.primary', fontWeight: 500 }}>Failed</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Box sx={{ width: 16, height: 16, bgcolor: '#F59E0B', borderRadius: '4px', border: '1px solid rgba(255, 255, 255, 0.2)', boxShadow: '0 2px 4px rgba(245, 158, 11, 0.3)' }} />
            <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.primary', fontWeight: 500 }}>Skipped</Typography>
          </Box>
        </Box>
      </Paper>

      {/* Failed Jobs Details */}
      {failedJobsDetails.length > 0 && (
        <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600, color: '#EF4444' }}>
                Failed Jobs Today
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {failedJobsDetails.length} job{failedJobsDetails.length !== 1 ? 's' : ''} failed - requires attention
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {failedJobsDetails.slice(0, 5).map((job) => (
              <Box
                key={job.execution_id}
                onClick={() => handleExecutionClick(job)}
                sx={{
                  p: 2,
                  borderRadius: '8px',
                  bgcolor: 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    bgcolor: 'rgba(239, 68, 68, 0.1)',
                    borderColor: 'rgba(239, 68, 68, 0.4)',
                  },
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {job.task_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                      {job.execution_id}
                    </Typography>
                  </Box>
                  <Chip
                    label="FAILED"
                    size="small"
                    icon={<ErrorIcon sx={{ fontSize: 14 }} />}
                    sx={{
                      bgcolor: 'rgba(239, 68, 68, 0.15)',
                      color: '#EF4444',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      fontSize: '0.65rem',
                      height: 22,
                      fontWeight: 600,
                    }}
                  />
                </Box>
                {job.error_message && (
                  <Box sx={{ mt: 1, p: 1.5, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: '6px' }}>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', display: 'block', mb: 0.5, fontWeight: 600 }}>
                      Error:
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.75rem', color: '#EF4444', fontFamily: 'monospace', wordBreak: 'break-word' }}>
                      {job.error_message}
                    </Typography>
                  </Box>
                )}
                <Box sx={{ display: 'flex', gap: 2, mt: 1.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                    Started: {new Date(job.started_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                  </Typography>
                  {job.duration_seconds && (
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                      Duration: {job.duration_seconds.toFixed(2)}s
                    </Typography>
                  )}
                </Box>
              </Box>
            ))}
            {failedJobsDetails.length > 5 && (
              <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.secondary', textAlign: 'center', mt: 1 }}>
                +{failedJobsDetails.length - 5} more failed jobs (scroll down to see all in Recent Jobs)
              </Typography>
            )}
          </Box>
        </Paper>
      )}

      {/* Skipped Jobs (Warnings) */}
      {skippedJobsDetails.length > 0 && (
        <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600, color: '#F59E0B' }}>
                Skipped Jobs Today
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {skippedJobsDetails.length} job{skippedJobsDetails.length !== 1 ? 's' : ''} skipped - not errors, just deferred
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {skippedJobsDetails.slice(0, 3).map((job) => (
              <Box
                key={job.execution_id}
                onClick={() => handleExecutionClick(job)}
                sx={{
                  p: 2,
                  borderRadius: '8px',
                  bgcolor: 'rgba(245, 158, 11, 0.05)',
                  border: '1px solid rgba(245, 158, 11, 0.2)',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    bgcolor: 'rgba(245, 158, 11, 0.1)',
                    borderColor: 'rgba(245, 158, 11, 0.4)',
                  },
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {job.task_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                      {job.execution_id}
                    </Typography>
                  </Box>
                  <Chip
                    label="SKIPPED"
                    size="small"
                    icon={<PauseIcon sx={{ fontSize: 14 }} />}
                    sx={{
                      bgcolor: 'rgba(245, 158, 11, 0.15)',
                      color: '#F59E0B',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      fontSize: '0.65rem',
                      height: 22,
                      fontWeight: 600,
                    }}
                  />
                </Box>
                <Box sx={{ mt: 1, p: 1.5, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: '6px' }}>
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', display: 'block', mb: 0.5, fontWeight: 600 }}>
                    Reason:
                  </Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', color: '#F59E0B', fontFamily: 'monospace' }}>
                    {job.skip_reason}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, mt: 1.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                    Started: {new Date(job.started_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
                  </Typography>
                  {job.duration_seconds && (
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                      Duration: {job.duration_seconds.toFixed(2)}s
                    </Typography>
                  )}
                </Box>
              </Box>
            ))}
            {skippedJobsDetails.length > 3 && (
              <Typography variant="caption" sx={{ fontSize: '0.75rem', color: 'text.secondary', textAlign: 'center', mt: 1 }}>
                +{skippedJobsDetails.length - 3} more skipped jobs
              </Typography>
            )}
          </Box>
        </Paper>
      )}

      {/* Recent Jobs */}
      <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600 }}>
            Recent Jobs
          </Typography>
          <Tooltip title="Export">
            <IconButton size="small">
              <DownloadIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Filters */}
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            size="small"
            placeholder="Search jobs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{
              flex: 1,
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                fontSize: '0.85rem',
              },
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                </InputAdornment>
              ),
            }}
          />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel sx={{ fontSize: '0.85rem' }}>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                fontSize: '0.85rem',
              }}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="success">Success</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel sx={{ fontSize: '0.85rem' }}>Time Range</InputLabel>
            <Select
              value={dateFilter}
              label="Time Range"
              onChange={(e) => setDateFilter(e.target.value as 'today' | 'last7days')}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                fontSize: '0.85rem',
              }}
            >
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="last7days">Last 7 Days</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Jobs Table */}
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Job ID
                </TableCell>
                <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Status
                </TableCell>
                <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Started At
                </TableCell>
                <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Duration
                </TableCell>
                <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      Loading jobs...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : paginatedExecutions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      No jobs found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedExecutions.map((execution) => (
                  <ExecutionRow
                    key={execution.execution_id}
                    execution={execution as TaskExecution & { task_id?: string }}
                    onExecutionClick={handleExecutionClick}
                    onUserInteraction={handleUserInteraction}
                    onCopyUuid={handleCopyUuid}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination */}
        <TablePagination
          component="div"
          count={filteredExecutions.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[10, 25, 50]}
          sx={{
            borderTop: '1px solid',
            borderColor: 'divider',
            '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
              fontSize: '0.75rem',
            },
          }}
        />
      </Paper>

      {/* Detail Drawers */}
      {selectedTask && (
        <TaskDetailDrawer
          open={taskDrawerOpen}
          task={selectedTask}
          onClose={() => {
            setTaskDrawerOpen(false);
            setSelectedTask(null);
          }}
          onTaskUpdated={loadData}
          onTriggerTask={handleTriggerTask}
        />
      )}

      {selectedExecution && (
        <JobDetailDrawer
          open={jobDrawerOpen}
          execution={selectedExecution}
          onClose={() => {
            setJobDrawerOpen(false);
            setSelectedExecution(null);
          }}
        />
      )}
    </Box>
  );
};
