import React from 'react';
import { Box, Typography, Tabs, Tab, IconButton, Tooltip, CircularProgress, Alert } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import SyncIcon from '@mui/icons-material/Sync';
import { IntentionBar } from '../components/agency/IntentionBar';
import { GoalBoard } from '../components/agency/GoalBoard';
import { GoalDetailDrawer } from '../components/agency/GoalDetailDrawer';
import { AgencyMetrics } from '../components/agency/AgencyMetrics';
import { CuriosityDashboard } from '../components/agency/CuriosityDashboard';
import { ValueProfile } from '../components/agency/ValueProfile';
import { RecentActivity } from '../components/agency/RecentActivity';
import { LearningDashboard } from '../components/agency/LearningDashboard';
import {
  fetchAgencyState,
  fetchGoals,
  fetchGoal,
} from '../api/agency';
import {
  AgencyStateResponse,
  GoalSummary,
  GoalResponse,
  AgencyMetrics as AgencyMetricsType,
} from '../types/agency';

type TabValue = 'overview' | 'goals' | 'curiosity' | 'learning' | 'values';

export const AgencyPage: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<TabValue>('overview');
  const [agencyState, setAgencyState] = React.useState<AgencyStateResponse | null>(null);
  const [allGoals, setAllGoals] = React.useState<GoalSummary[]>([]);
  const [selectedGoal, setSelectedGoal] = React.useState<GoalResponse | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [goalLoading, setGoalLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = React.useState(true);

  const loadAgencyData = React.useCallback(async () => {
    try {
      const [state, goalsResponse] = await Promise.all([
        fetchAgencyState(),
        fetchGoals({ limit: 100 }),
      ]);

      setAgencyState(state);
      setAllGoals(goalsResponse.goals);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load agency data:', err);
      const errorMessage = err.message || 'Failed to load agency data';
      
      if (!autoRefresh) {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [autoRefresh]);

  React.useEffect(() => {
    loadAgencyData();
  }, [loadAgencyData]);

  React.useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadAgencyData();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, loadAgencyData]);


  const handleGoalClick = async (goal: GoalSummary) => {
    setDrawerOpen(true);
    setGoalLoading(true);
    
    try {
      const fullGoal = await fetchGoal(goal.goal_id);
      setSelectedGoal(fullGoal);
    } catch (err: any) {
      console.error('Failed to load goal details:', err);
      setSelectedGoal(null);
    } finally {
      setGoalLoading(false);
    }
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
    setTimeout(() => setSelectedGoal(null), 300);
  };

  const handleRefresh = () => {
    setLoading(true);
    loadAgencyData();
  };

  const metrics: AgencyMetricsType | null = agencyState
    ? {
        active_goals: agencyState.intention_set.active_intentions.length,
        plans_in_flight: agencyState.intention_set.active_intentions.filter(
          (g) => g.metadata?.plan_id
        ).length,
        proactive_messages_24h: 0,
        curiosity_level: agencyState.curiosity_status.curiosity_level,
        reflection_runs_7d: 0,
        lessons_applied: 0,
      }
    : null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
        <Tooltip title={autoRefresh ? 'Auto-refresh enabled (5s)' : 'Auto-refresh disabled'}>
          <IconButton
            size="small"
            onClick={() => setAutoRefresh(!autoRefresh)}
            sx={{
              color: autoRefresh ? 'primary.main' : 'text.secondary',
            }}
          >
            <AutorenewIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Refresh now">
          <IconButton size="small" onClick={handleRefresh} disabled={loading}>
            <SyncIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {agencyState && (
        <IntentionBar
          primaryFocus={agencyState.intention_set.primary_focus}
          activeIntentions={agencyState.intention_set.active_intentions}
          onGoalClick={handleGoalClick}
        />
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 500,
              fontSize: '0.9rem',
            },
          }}
        >
          <Tab label="Overview" value="overview" />
          <Tab label="Goals" value="goals" />
          <Tab label="Curiosity" value="curiosity" />
          <Tab label="Learning" value="learning" />
          <Tab label="Values" value="values" />
        </Tabs>
      </Box>

      <Box sx={{ py: 2 }}>
        {activeTab === 'overview' && (
          <Box>
            <AgencyMetrics metrics={metrics} loading={loading} />
            <Box sx={{ mt: 4 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                Recent Activity
              </Typography>
              <RecentActivity
                events={[
                  {
                    id: '1',
                    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
                    type: 'goal_activated',
                    title: 'Practice English Communication',
                    description: 'Goal activated for language practice',
                    origin: 'User',
                  },
                  {
                    id: '2',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
                    type: 'goal_created',
                    title: 'Knowledge Graph Curation',
                    description: 'New curiosity-driven goal created',
                    origin: 'Curiosity',
                  },
                  {
                    id: '3',
                    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
                    type: 'goal_completed',
                    title: 'User Understanding Analysis',
                    description: 'Goal completed successfully',
                    origin: 'System',
                  },
                ]}
                loading={loading}
              />
            </Box>
          </Box>
        )}

        {activeTab === 'goals' && (
          <GoalBoard goals={allGoals} loading={loading} onGoalClick={handleGoalClick} />
        )}

        {activeTab === 'curiosity' && (
          <CuriosityDashboard
            curiosityStatus={agencyState?.curiosity_status || null}
            loading={loading}
          />
        )}

        {activeTab === 'learning' && (
          <LearningDashboard
            reflectionStats={{
              total_reflections: 42,
              reflections_7d: metrics?.reflection_runs_7d || 0,
              lessons_learned: 15,
              lessons_applied: metrics?.lessons_applied || 0,
              avg_confidence: 0.78,
            }}
            recentLessons={[
              {
                lesson_id: '1',
                title: 'User prefers concise responses in technical discussions',
                category: 'Communication Style',
                confidence: 0.85,
                applied_count: 12,
                created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
              },
              {
                lesson_id: '2',
                title: 'Context switching requires explicit acknowledgment',
                category: 'Conversation Flow',
                confidence: 0.72,
                applied_count: 8,
                created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString(),
              },
              {
                lesson_id: '3',
                title: 'User values transparency about system limitations',
                category: 'Trust Building',
                confidence: 0.91,
                applied_count: 15,
                created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7).toISOString(),
              },
            ]}
            loading={loading}
          />
        )}

        {activeTab === 'values' && (
          <ValueProfile
            valueProfile={agencyState?.value_profile || null}
            loading={loading}
          />
        )}

        {loading && activeTab !== 'overview' && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        )}
      </Box>

      <GoalDetailDrawer
        open={drawerOpen}
        goal={selectedGoal}
        loading={goalLoading}
        onClose={handleDrawerClose}
      />
    </Box>
  );
};
