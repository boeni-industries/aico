import React, { useState, useEffect } from 'react';
import { DetailDrawer } from '../common/DetailDrawer';
import {
  Box,
  Typography,
  Divider,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Switch,
  FormControlLabel,
} from '@mui/material';
import { Play as PlayArrowIcon, Pencil as EditIcon, Trash2 as DeleteIcon, CheckCircle as CheckCircleIcon, AlertCircle as ErrorIcon, Hourglass as HourglassEmptyIcon } from 'lucide-react';
import {
  fetchTaskExecutions,
  updateTask,
  deleteTask,
  type Task,
  type TaskExecution,
} from '../../api/scheduler';
import { useToast } from '../common/Toast';

interface TaskDetailDrawerProps {
  open: boolean;
  task: Task;
  onClose: () => void;
  onTaskUpdated: () => void;
  onTriggerTask: (taskId: string) => void;
}

export const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  open,
  task,
  onClose,
  onTaskUpdated,
  onTriggerTask,
}) => {
  const { showToast } = useToast();
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && task) {
      loadExecutions();
    }
  }, [open, task]);

  const loadExecutions = async () => {
    try {
      setLoading(true);
      const response = await fetchTaskExecutions(task.task_id, 20);
      setExecutions(response.executions);
    } catch (error) {
      console.error('Failed to load executions:', error);
      showToast('Failed to load execution history', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = async () => {
    try {
      await updateTask(task.task_id, { enabled: !task.enabled });
      showToast(`Task ${task.enabled ? 'disabled' : 'enabled'} successfully`, 'success');
      onTaskUpdated();
    } catch (error) {
      console.error('Failed to toggle task:', error);
      showToast('Failed to update task', 'error');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete task "${task.task_id}"?`)) {
      return;
    }

    try {
      await deleteTask(task.task_id);
      showToast('Task deleted successfully', 'success');
      onTaskUpdated();
      onClose();
    } catch (error) {
      console.error('Failed to delete task:', error);
      showToast('Failed to delete task', 'error');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />;
      case 'failed':
        return <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />;
      case 'running':
        return <HourglassEmptyIcon sx={{ fontSize: 16, color: '#60A5FA' }} />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return '#10B981';
      case 'failed': return '#EF4444';
      case 'running': return '#60A5FA';
      default: return '#6B7280';
    }
  };

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title="Task Details"
      width={600}
      headerActions={
        <>
          <Button
            variant="contained"
            size="small"
            startIcon={<PlayArrowIcon />}
            onClick={() => onTriggerTask(task.task_id)}
            sx={{
              bgcolor: '#10B981',
              '&:hover': { bgcolor: '#059669' },
            }}
          >
            Trigger
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<EditIcon />}
            sx={{ borderColor: 'rgba(255, 255, 255, 0.2)' }}
          >
            Edit
          </Button>
          <Button
            variant="outlined"
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleDelete}
          >
            Delete
          </Button>
        </>
      }
    >
        {/* Task ID */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
            {task.task_id}
          </Typography>
        </Box>

        {/* Status Badge */}
        <Box sx={{ mb: 3 }}>
          <Chip
            label={task.enabled ? 'ENABLED' : 'DISABLED'}
            size="small"
            sx={{
              bgcolor: task.enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(107, 114, 128, 0.15)',
              color: task.enabled ? '#10B981' : '#6B7280',
              border: '1px solid',
              borderColor: task.enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(107, 114, 128, 0.3)',
              fontSize: '0.7rem',
              fontWeight: 600,
            }}
          />
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Task Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Task Information
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Task Class
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                {task.task_class}
              </Typography>
            </Box>

            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Schedule (Cron)
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                {task.schedule}
              </Typography>
            </Box>

            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Created At
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                {new Date(task.created_at).toLocaleString()}
              </Typography>
            </Box>

            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Updated At
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                {new Date(task.updated_at).toLocaleString()}
              </Typography>
            </Box>

            {task.config && Object.keys(task.config).length > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Configuration
                </Typography>
                <Paper sx={{ p: 2, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px' }}>
                  <pre style={{ margin: 0, fontSize: '0.75rem', fontFamily: 'monospace', overflow: 'auto' }}>
                    {JSON.stringify(task.config, null, 2)}
                  </pre>
                </Paper>
              </Box>
            )}
          </Box>
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Actions */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Actions
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={task.enabled}
                  onChange={handleToggleEnabled}
                  size="small"
                />
              }
              label={<Typography variant="body2">Enable Task</Typography>}
            />

            <Button
              variant="outlined"
              startIcon={<PlayArrowIcon />}
              onClick={() => onTriggerTask(task.task_id)}
              fullWidth
              sx={{ justifyContent: 'flex-start' }}
            >
              Trigger Now
            </Button>

            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              fullWidth
              sx={{ justifyContent: 'flex-start' }}
              disabled
            >
              Edit Configuration
            </Button>

            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleDelete}
              fullWidth
              sx={{ justifyContent: 'flex-start' }}
            >
              Delete Task
            </Button>
          </Box>
        </Box>

        <Divider sx={{ mb: 3 }} />

        {/* Execution History */}
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Recent Executions
          </Typography>

          {loading ? (
            <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
              Loading executions...
            </Typography>
          ) : executions.length === 0 ? (
            <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
              No executions found
            </Typography>
          ) : (
            <TableContainer component={Paper} sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontSize: '0.7rem', fontWeight: 600 }}>Status</TableCell>
                    <TableCell sx={{ fontSize: '0.7rem', fontWeight: 600 }}>Started</TableCell>
                    <TableCell sx={{ fontSize: '0.7rem', fontWeight: 600 }}>Duration</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {executions.map((execution) => (
                    <TableRow key={execution.execution_id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {getStatusIcon(execution.status)}
                          <Chip
                            label={execution.status}
                            size="small"
                            sx={{
                              bgcolor: `${getStatusColor(execution.status)}15`,
                              color: getStatusColor(execution.status),
                              fontSize: '0.65rem',
                              height: 18,
                              textTransform: 'capitalize',
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.75rem' }}>
                        {new Date(execution.started_at).toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.75rem' }}>
                        {execution.duration_seconds 
                          ? `${execution.duration_seconds.toFixed(2)}s`
                          : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
    </DetailDrawer>
  );
};
