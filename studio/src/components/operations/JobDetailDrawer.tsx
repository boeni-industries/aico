import React from 'react';
import {
  Box,
  Typography,
  Divider,
  Chip,
  Paper,
} from '@mui/material';
import { CheckCircle as CheckCircleIcon, AlertCircle as ErrorIcon, Hourglass as HourglassEmptyIcon, Pause as PauseIcon, X as CancelIcon } from 'lucide-react';
import { DetailDrawer } from '../common/DetailDrawer';
import { type TaskExecution } from '../../api/scheduler';

interface JobDetailDrawerProps {
  open: boolean;
  execution: TaskExecution;
  onClose: () => void;
}

export const JobDetailDrawer: React.FC<JobDetailDrawerProps> = ({
  open,
  execution,
  onClose,
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon sx={{ fontSize: 20, color: '#10B981' }} />;
      case 'failed':
        return <ErrorIcon sx={{ fontSize: 20, color: '#EF4444' }} />;
      case 'running':
        return <HourglassEmptyIcon sx={{ fontSize: 20, color: '#60A5FA' }} />;
      case 'pending':
        return <HourglassEmptyIcon sx={{ fontSize: 20, color: '#9CA3AF' }} />;
      case 'skipped':
      case 'deferred':
        return <PauseIcon sx={{ fontSize: 20, color: '#F59E0B' }} />;
      case 'cancelled':
        return <CancelIcon sx={{ fontSize: 20, color: '#6B7280' }} />;
      default:
        return null;
    }
  };

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

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title="Job Execution Details"
      subtitle={
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.9rem', mb: 0.5, color: '#60A5FA' }}>
            {(execution as any).task_id || 'Unknown Task'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
            {execution.execution_id}
          </Typography>
        </Box>
      }
      width={600}
    >
          {/* Status Badge */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
            {getStatusIcon(execution.status)}
            <Chip
              label={execution.status.toUpperCase()}
              size="small"
              sx={{
                bgcolor: `${getStatusColor(execution.status)}15`,
                color: getStatusColor(execution.status),
                border: '1px solid',
                borderColor: `${getStatusColor(execution.status)}30`,
                fontSize: '0.7rem',
                fontWeight: 600,
              }}
            />
          </Box>

          <Divider sx={{ mb: 3, borderColor: 'rgba(255, 255, 255, 0.08)' }} />

          {/* Execution Information */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Execution Information
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Started At
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                {new Date(execution.started_at).toLocaleString()}
              </Typography>
            </Box>

            {execution.completed_at && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  Completed At
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                  {new Date(execution.completed_at).toLocaleString()}
                </Typography>
              </Box>
            )}

            {execution.duration_seconds !== null && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  Duration
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                  {execution.duration_seconds.toFixed(2)} seconds
                </Typography>
              </Box>
            )}
          </Box>
        </Box>

        {/* Result */}
        {execution.result && Object.keys(execution.result).length > 0 && (
          <>
            <Divider sx={{ mb: 3, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Result
              </Typography>
              <Paper sx={{ 
                p: 2, 
                background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.2) 100%)',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(10px)',
              }}>
                <pre style={{ 
                  margin: 0, 
                  fontSize: '0.75rem', 
                  fontFamily: 'monospace', 
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {JSON.stringify(execution.result, null, 2)}
                </pre>
              </Paper>
            </Box>
          </>
        )}

        {/* Error Message */}
        {execution.error_message && (
          <>
            <Divider sx={{ mb: 3, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#EF4444' }}>
                Error Details
              </Typography>
              <Paper sx={{ 
                p: 2, 
                background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.1) 100%)',
                borderRadius: '12px',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                backdropFilter: 'blur(10px)',
              }}>
                <Typography variant="body2" sx={{ 
                  fontSize: '0.75rem', 
                  fontFamily: 'monospace',
                  color: '#EF4444',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {execution.error_message}
                </Typography>
              </Paper>
            </Box>
          </>
        )}

        {/* Execution Metadata */}
        <Divider sx={{ mb: 3, borderColor: 'rgba(255, 255, 255, 0.08)' }} />
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Metadata
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Execution ID
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                {execution.execution_id}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                Status
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.75rem', textTransform: 'capitalize' }}>
                {execution.status}
              </Typography>
            </Box>

            {execution.duration_seconds !== null && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  Execution Time
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                  {execution.duration_seconds < 1 
                    ? `${(execution.duration_seconds * 1000).toFixed(0)}ms`
                    : `${execution.duration_seconds.toFixed(2)}s`}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>
    </DetailDrawer>
  );
};
