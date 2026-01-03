import React from 'react';
import { Box, Card, Typography, LinearProgress, Chip } from '@mui/material';
import { GoalSummary, GoalOrigin, GoalPriority } from '../../types/agency';
import { formatDistanceToNow } from 'date-fns';

interface GoalCardProps {
  goal: GoalSummary;
  onClick: (goal: GoalSummary) => void;
}

const originColors: Record<GoalOrigin, { bg: string; text: string; border: string }> = {
  user: { 
    bg: 'rgba(184, 161, 234, 0.12)', 
    text: '#B8A1EA',
    border: 'rgba(184, 161, 234, 0.3)'
  },
  curiosity: { 
    bg: 'rgba(94, 234, 212, 0.12)', 
    text: '#5EEAD4',
    border: 'rgba(94, 234, 212, 0.3)'
  },
  hobby: { 
    bg: 'rgba(252, 211, 77, 0.12)', 
    text: '#FCD34D',
    border: 'rgba(252, 211, 77, 0.3)'
  },
  maintenance: { 
    bg: 'rgba(148, 163, 184, 0.12)', 
    text: '#94A3B8',
    border: 'rgba(148, 163, 184, 0.3)'
  },
};

const originLabels: Record<GoalOrigin, string> = {
  user: 'User',
  curiosity: 'Curiosity',
  hobby: 'Hobby',
  maintenance: 'System',
};

const priorityColors: Record<GoalPriority, string> = {
  critical: '#DC2626',
  high: '#F59E0B',
  normal: '#3B82F6',
  low: '#9CA3AF',
};

export const GoalCard: React.FC<GoalCardProps> = ({ goal, onClick }) => {
  const planSteps = goal.metadata?.plan_steps || 0;
  const completedSteps = goal.metadata?.completed_steps || 0;
  const progress = planSteps > 0 ? (completedSteps / planSteps) * 100 : 0;

  const age = React.useMemo(() => {
    try {
      return formatDistanceToNow(new Date(goal.created_at), { addSuffix: true });
    } catch {
      return 'Unknown';
    }
  }, [goal.created_at]);

  return (
    <Card
      onClick={(e) => {
        e.stopPropagation();
        onClick(goal);
      }}
      sx={{
        p: 2.5,
        mb: 2,
        cursor: 'pointer',
        borderRadius: '20px',
        border: '1.5px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-3px)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          borderColor: originColors[goal.origin].border,
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1.5 }}>
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            bgcolor: originColors[goal.origin].text,
            mt: 0.75,
            mr: 1.5,
            flexShrink: 0,
            boxShadow: `0 0 12px ${originColors[goal.origin].text}40`,
          }}
        />
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            fontSize: '0.95rem',
            lineHeight: 1.4,
            flexGrow: 1,
            textTransform: 'capitalize',
          }}
        >
          {goal.title}
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', gap: 0.75, mb: 1.5, flexWrap: 'wrap' }}>
        <Chip
          label={originLabels[goal.origin]}
          size="small"
          sx={{
            bgcolor: originColors[goal.origin].bg,
            color: originColors[goal.origin].text,
            border: '1px solid',
            borderColor: originColors[goal.origin].border,
            fontSize: '0.7rem',
            height: 22,
            fontWeight: 600,
            backdropFilter: 'blur(4px)',
          }}
        />
        <Chip
          label={goal.priority.toUpperCase()}
          size="small"
          sx={{
            bgcolor: 'background.default',
            color: 'text.secondary',
            border: '1px solid',
            borderColor: 'divider',
            fontSize: '0.7rem',
            height: 22,
            fontWeight: 600,
          }}
        />
        <Chip
          label={age}
          size="small"
          sx={{
            bgcolor: 'background.default',
            fontSize: '0.7rem',
            height: 20,
          }}
        />
      </Box>

      {goal.description && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mb: 1.5,
            fontSize: '0.85rem',
            lineHeight: 1.5,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {goal.description}
        </Typography>
      )}

      {planSteps > 0 && (
        <Box sx={{ mb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Progress
            </Typography>
            <Typography
              variant="caption"
              sx={{ fontSize: '0.7rem', fontWeight: 500, fontFamily: 'monospace' }}
            >
              {Math.round(progress)}% ({completedSteps}/{planSteps} steps)
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: 'background.default',
              '& .MuiLinearProgress-bar': {
                bgcolor: originColors[goal.origin].text,
                borderRadius: 3,
                boxShadow: `0 0 8px ${originColors[goal.origin].text}40`,
              },
            }}
          />
        </Box>
      )}

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pt: 1,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        {goal.score !== undefined && (
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.7rem',
              fontWeight: 500,
              fontFamily: 'monospace',
            }}
          >
            Score: {goal.score.toFixed(2)}
          </Typography>
        )}
        {goal.metadata?.plan_id && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontSize: '0.7rem' }}
          >
            Plan: {goal.metadata.plan_status || 'Active'}
          </Typography>
        )}
      </Box>
    </Card>
  );
};
