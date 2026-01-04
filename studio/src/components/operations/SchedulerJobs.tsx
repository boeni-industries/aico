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
  LinearProgress,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TablePagination,
  Button,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  HourglassEmpty as HourglassEmptyIcon,
  Pause as PauseIcon,
  Cancel as CancelIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  ContentCopy as ContentCopyIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import {
  fetchSchedulerStatus,
  fetchTasks,
  fetchTaskExecutions,
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

export const SchedulerJobs: React.FC<SchedulerJobsProps> = ({ refreshTrigger }) => {
  const { showToast } = useToast();
  
  // State
  const [loading, setLoading] = useState(true);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [queueFilter, setQueueFilter] = useState<string>('all');
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
  const loadData = async (isBackgroundRefresh = false) => {
    try {
      if (!isBackgroundRefresh) {
        setLoading(true);
      }

      const [statusData, tasksData] = await Promise.all([
        fetchSchedulerStatus(),
        fetchTasks(),
      ]);

      // Load recent executions for all tasks
      const executionsPromises = tasksData.tasks.map(task =>
        fetchTaskExecutions(task.task_id, 5)
          .then(result => result.executions.map(exec => ({ ...exec, task_id: task.task_id })))
          .catch(() => [])
      );
      const executionsResults = await Promise.all(executionsPromises);
      const allExecutions = executionsResults.flat();
      
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
  };

  // Apply pending updates when user stops interacting
  useEffect(() => {
    if (!isUserInteracting && pendingDataRef.current) {
      setSchedulerStatus(pendingDataRef.current.status);
      setTasks(pendingDataRef.current.tasks);
      setExecutions(pendingDataRef.current.executions);
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
  }, []);

  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      loadData(true);
    }
  }, [refreshTrigger]);

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

  // Handle task click
  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setTaskDrawerOpen(true);
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

  // Calculate KPIs
  const jobsToday = executions.filter(e => {
    const startDate = new Date(e.started_at);
    const today = new Date();
    return startDate.toDateString() === today.toDateString();
  }).length;

  const failedJobs = executions.filter(e => e.status === 'failed').length;
  const successfulJobs = executions.filter(e => e.status === 'success').length;
  const successRate = executions.length > 0 
    ? Math.round((successfulJobs / executions.length) * 100) 
    : 0;
  const runningJobs = executions.filter(e => e.status === 'running').length;

  // Filter executions
  const filteredExecutions = executions.filter(execution => {
    const matchesSearch = searchQuery === '' || 
      execution.execution_id.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || execution.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Paginate
  const paginatedExecutions = filteredExecutions.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />;
      case 'failed':
        return <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />;
      case 'running':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#60A5FA' }} />;
      case 'pending':
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
      case 'success': return '#10B981';
      case 'failed': return '#EF4444';
      case 'running': return '#60A5FA';
      case 'pending': return '#F59E0B';
      case 'cancelled': return '#6B7280';
      default: return '#6B7280';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
        {/* Jobs Today */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Jobs Today
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700 }}>
            {jobsToday}
          </Typography>
        </Paper>

        {/* Failed Jobs */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Failed Jobs
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: failedJobs > 0 ? '#EF4444' : 'inherit' }}>
            {failedJobs}
          </Typography>
        </Paper>

        {/* Success Rate */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Success Rate
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: successRate >= 90 ? '#10B981' : successRate >= 70 ? '#F59E0B' : '#EF4444' }}>
            {successRate}%
          </Typography>
        </Paper>

        {/* Active Jobs */}
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Active Jobs
          </Typography>
          <Typography variant="h4" sx={{ mt: 1, fontWeight: 700, color: '#60A5FA' }}>
            {runningJobs}
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
            <Chip 
              label={schedulerStatus.running ? 'RUNNING' : 'STOPPED'}
              size="small"
              sx={{
                bgcolor: schedulerStatus.running ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: schedulerStatus.running ? '#10B981' : '#EF4444',
                border: '1px solid',
                borderColor: schedulerStatus.running ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                fontSize: '0.7rem',
                fontWeight: 600,
              }}
            />
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

      {/* Recent Jobs */}
      <Paper sx={{ p: 3, borderRadius: '16px', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontSize: '0.9rem', fontWeight: 600 }}>
            Recent Jobs
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={() => loadData(false)}>
                <RefreshIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Export">
              <IconButton size="small">
                <DownloadIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          </Box>
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
                  <TableRow
                    key={execution.execution_id}
                    hover
                    onClick={() => handleExecutionClick(execution)}
                    onMouseEnter={handleUserInteraction}
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
                          {(execution as any).task_id || 'Unknown Task'}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace', fontSize: '0.7rem' }}>
                            {execution.execution_id}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={(e) => handleCopyUuid(execution.execution_id, e)}
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
                            bgcolor: `${getStatusColor(execution.status)}15`,
                            color: getStatusColor(execution.status),
                            fontSize: '0.7rem',
                            height: 20,
                            textTransform: 'capitalize',
                          }}
                        />
                      </Box>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        {new Date(execution.started_at).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        {execution.duration_seconds 
                          ? `${execution.duration_seconds.toFixed(2)}s`
                          : execution.status === 'running' 
                            ? 'Running...' 
                            : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Tooltip title="View Details">
                        <IconButton size="small" onClick={(e) => {
                          e.stopPropagation();
                          handleExecutionClick(execution);
                        }}>
                          <PlayArrowIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
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
