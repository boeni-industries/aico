import React from 'react';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import { GoalSummary, GoalStatus } from '../../types/agency';
import { GoalCard } from './GoalCard';

interface GoalBoardProps {
  goals: GoalSummary[];
  loading?: boolean;
  onGoalClick: (goal: GoalSummary) => void;
}

const statusLabels: Record<GoalStatus, string> = {
  pending: 'Proposed',
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
  retired: 'Dropped',
};

const statusColors: Record<GoalStatus, string> = {
  pending: '#E0E7FF',
  active: '#10B981',
  paused: '#F59E0B',
  completed: '#6B7280',
  retired: '#EF4444',
};

const columns: GoalStatus[] = ['pending', 'active', 'paused', 'completed', 'retired'];

export const GoalBoard: React.FC<GoalBoardProps> = ({ goals, loading, onGoalClick }) => {
  const goalsByStatus = React.useMemo(() => {
    const grouped: Record<GoalStatus, GoalSummary[]> = {
      pending: [],
      active: [],
      paused: [],
      completed: [],
      retired: [],
    };

    goals.forEach((goal) => {
      if (goal.status in grouped) {
        grouped[goal.status].push(goal);
      }
    });

    return grouped;
  }, [goals]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(3, 1fr)',
          lg: 'repeat(5, 1fr)',
        },
        gap: 3,
        pb: 3,
      }}
    >
      {columns.map((status) => {
        const columnGoals = goalsByStatus[status];
        
        return (
          <Box key={status} sx={{ minWidth: 0 }}>
            <Paper
              sx={{
                p: 2,
                mb: 2,
                bgcolor: 'background.paper',
                borderRadius: '12px',
                border: 1,
                borderColor: 'divider',
                position: 'sticky',
                top: 0,
                zIndex: 1,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    bgcolor: statusColors[status],
                  }}
                />
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    fontSize: '0.75rem',
                  }}
                >
                  {statusLabels[status]}
                </Typography>
                <Box
                  sx={{
                    ml: 'auto',
                    bgcolor: 'background.default',
                    px: 1,
                    py: 0.25,
                    borderRadius: '12px',
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.7rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    {columnGoals.length}
                  </Typography>
                </Box>
              </Box>
            </Paper>

            <Box
              sx={{
                maxHeight: 'calc(100vh - 300px)',
                overflowY: 'auto',
                pr: 0.5,
                '&::-webkit-scrollbar': {
                  width: 6,
                },
                '&::-webkit-scrollbar-thumb': {
                  bgcolor: 'divider',
                  borderRadius: 3,
                },
              }}
            >
              {columnGoals.length > 0 ? (
                columnGoals.map((goal) => (
                  <GoalCard key={goal.goal_id} goal={goal} onClick={onGoalClick} />
                ))
              ) : (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    textAlign: 'center',
                    py: 4,
                    fontSize: '0.85rem',
                  }}
                >
                  No goals
                </Typography>
              )}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};
