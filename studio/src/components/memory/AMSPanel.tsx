import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, LinearProgress, Chip, IconButton, Divider, Alert, CircularProgress } from '@mui/material';
import { Sparkles as AmsIcon, Clock as ScheduleIcon, Brain as BrainIcon, TrendingUp as TrendingIcon, RefreshCw as RefreshIcon, Info as InfoIcon, CheckCircle as CheckIcon, Clock as TimelineIcon, Lightbulb as LightbulbIcon, ThumbsUp as ThumbUpIcon, ThumbsDown as ThumbDownIcon, AlertTriangle as WarningIcon } from 'lucide-react';
import { StyledTooltip } from '../common/StyledTooltip';
import { fetchAMSStats } from '../../api/ams';
import type { AMSStats } from '../../api/ams';

interface AMSPanelProps {
  // No props needed - fetches own data
}

export const AMSPanel: React.FC<AMSPanelProps> = () => {
  const [amsData, setAmsData] = useState<AMSStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAMSData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAMSStats();
      setAmsData(data);
    } catch (err: any) {
      console.error('Failed to load AMS stats:', err);
      setError(err.message || 'Failed to load AMS statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAMSData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ borderRadius: '12px' }}>
        <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
          Failed to Load AMS Data
        </Typography>
        <Typography variant="caption">{error}</Typography>
      </Alert>
    );
  }

  if (!amsData) {
    return (
      <Alert severity="info" sx={{ borderRadius: '12px' }}>
        <Typography variant="body2">No AMS data available</Typography>
      </Alert>
    );
  }

  // Extract data from API response
  const consolidationStatus = {
    lastRun: amsData.consolidation.last_run,
    nextScheduled: amsData.consolidation.next_scheduled,
    currentCycle: { 
      day: amsData.consolidation.current_cycle_day, 
      total: amsData.consolidation.total_cycle_days 
    },
    status: amsData.consolidation.status as 'idle' | 'running' | 'scheduled',
    lastSession: amsData.consolidation.last_session ? {
      experiencesReplayed: amsData.consolidation.last_session.experiences_replayed,
      factsConsolidated: amsData.consolidation.last_session.facts_consolidated,
      graphUpdates: amsData.consolidation.last_session.graph_updates,
      duration: `${Math.floor(amsData.consolidation.last_session.duration_seconds / 60)} minutes`,
      success: amsData.consolidation.last_session.success,
    } : null,
  };

  const behavioralLearning = {
    activeSkills: amsData.behavioral_learning.active_skills,
    feedbackReceived: amsData.behavioral_learning.total_feedback_received,
    learningRate: amsData.behavioral_learning.learning_rate,
    confidence: amsData.behavioral_learning.average_confidence,
    topSkills: amsData.behavioral_learning.top_skills.map(skill => ({
      name: skill.name,
      confidence: skill.confidence,
      usage: skill.usage_count,
      lastFeedback: skill.last_feedback as 'positive' | 'negative' | 'neutral' | null,
    })),
    recentLearning: amsData.behavioral_learning.recent_learning_insights,
  };

  const userPreferences = {
    dimensions: amsData.user_preferences.dimensions,
    contextBuckets: amsData.user_preferences.context_buckets,
    insights: amsData.user_preferences.insights,
  };

  const feedbackStats = {
    total: amsData.feedback.total,
    positive: amsData.feedback.positive,
    negative: amsData.feedback.negative,
    neutral: amsData.feedback.neutral,
    responseRate: amsData.feedback.response_rate,
    recentFeedback: amsData.feedback.recent_feedback,
  };

  const cycleProgress = (consolidationStatus.currentCycle.day / consolidationStatus.currentCycle.total) * 100;

  // Helper to safely calculate percentages (avoid NaN when total is 0)
  const safePercentage = (value: number, total: number): number => {
    return total > 0 ? Math.round((value / total) * 100) : 0;
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <AmsIcon sx={{ fontSize: 28, color: '#F59E0B' }} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
            Adaptive Memory System
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
            Brain-inspired memory orchestration with complementary learning systems
          </Typography>
        </Box>
        <StyledTooltip title="AMS coordinates fast hippocampal learning (working memory) with slow cortical integration (semantic memory) through background consolidation, preventing catastrophic forgetting while enabling rapid adaptation." arrow>
          <InfoIcon sx={{ fontSize: 20, color: 'text.secondary', cursor: 'help' }} />
        </StyledTooltip>
      </Box>

      {/* Overview Metrics */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2.5, borderRadius: '16px', bgcolor: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <ScheduleIcon sx={{ fontSize: 20, color: '#F59E0B' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Consolidation Status
            </Typography>
            <StyledTooltip title="Current status of the memory consolidation engine. Shows when the last consolidation ran, the next scheduled run, and progress through the 7-day user rotation cycle. Consolidation transfers important memories from working memory to semantic memory during system idle periods." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title="Current consolidation engine state. 'Idle' means waiting for next scheduled run, 'Running' means actively consolidating memories." arrow>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#F59E0B', mb: 0.5, cursor: 'help' }}>
              {consolidationStatus.status === 'idle' ? 'Idle' : 'Running'}
            </Typography>
          </StyledTooltip>
          <StyledTooltip title="Time elapsed since the last consolidation session completed. Consolidation runs daily at 2 AM by default." arrow>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, cursor: 'help' }}>
              Last run: {consolidationStatus.lastRun}
            </Typography>
          </StyledTooltip>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <StyledTooltip title="Current position in the 7-day user rotation cycle. Users are divided into 7 groups, with one group consolidated each day to distribute system load evenly throughout the week." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', cursor: 'help' }}>
                Day {consolidationStatus.currentCycle.day}/{consolidationStatus.currentCycle.total} cycle
              </Typography>
            </StyledTooltip>
            <StyledTooltip title="Users are sharded across 7 days. Each user is consolidated once per week on their assigned day, preventing system overload." arrow>
              <Chip label="7-day rotation" size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title={`Progress through the 7-day cycle: ${consolidationStatus.currentCycle.day} of ${consolidationStatus.currentCycle.total} days completed (${cycleProgress.toFixed(0)}%)`} arrow>
            <LinearProgress variant="determinate" value={cycleProgress} sx={{ height: 6, borderRadius: 3, bgcolor: 'rgba(245, 158, 11, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#F59E0B' }, cursor: 'help' }} />
          </StyledTooltip>
          <StyledTooltip title="Next scheduled consolidation run. By default runs daily at 2 AM when system is idle. Schedule is configurable via backend settings." arrow>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontSize: '0.7rem', cursor: 'help' }}>
              Next: {consolidationStatus.nextScheduled}
            </Typography>
          </StyledTooltip>
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: '16px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <BrainIcon sx={{ fontSize: 20, color: '#8B5CF6' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Behavioral Learning
            </Typography>
            <StyledTooltip title="Skill-based learning system that adapts AICO's interaction style based on user feedback. Tracks 24+ skills like 'Technical Explanation', 'Casual Chat', 'Code Review' with confidence scores updated via RLHF (thumbs up/down)." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title="Total number of interaction skills AICO has learned. Each skill represents a specific way of responding (e.g., technical explanations, casual chat, empathy expression) that AICO can select based on context and past feedback." arrow>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#8B5CF6', mb: 0.5, cursor: 'help' }}>
              {behavioralLearning.activeSkills}
            </Typography>
          </StyledTooltip>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Active skills learned
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <StyledTooltip title="Total feedback events received from users (thumbs up/down, detailed feedback). Each interaction helps refine skill confidence scores and preference learning." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', cursor: 'help' }}>
                {behavioralLearning.feedbackReceived} interactions
              </Typography>
            </StyledTooltip>
            <StyledTooltip title="Current learning state. 'Adapting' means actively adjusting based on recent feedback. Learning rate controls how quickly skills adapt to new feedback signals." arrow>
              <Chip label={behavioralLearning.learningRate} size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(139, 92, 246, 0.15)', color: '#8B5CF6', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title={`Average confidence across all skills: ${behavioralLearning.confidence}%. Higher confidence means more reliable skill selection based on accumulated feedback. Confidence increases with positive feedback and decreases with negative feedback.`} arrow>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
              <LinearProgress variant="determinate" value={behavioralLearning.confidence} sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: 'rgba(139, 92, 246, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#8B5CF6' } }} />
              <Typography variant="caption" sx={{ fontWeight: 600, color: '#8B5CF6', fontSize: '0.75rem' }}>
                {behavioralLearning.confidence}%
              </Typography>
            </Box>
          </StyledTooltip>
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: '16px', bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <TimelineIcon sx={{ fontSize: 20, color: '#10B981' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Memory Evolution
            </Typography>
            <StyledTooltip title="Temporal tracking of how user preferences and interaction patterns change over time. Maintains 90-day history to detect preference shifts, seasonal patterns, and long-term trends in communication style." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title="Number of preference dimensions being tracked. Each dimension represents a different aspect of interaction style (verbosity, formality, technical depth, etc.). System tracks 16 dimensions total across 100 context buckets." arrow>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#10B981', mb: 0.5, cursor: 'help' }}>
              {userPreferences.dimensions.length}
            </Typography>
          </StyledTooltip>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Preference dimensions tracked
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <StyledTooltip title="Context buckets group similar situations (e.g., 'technical discussion in morning', 'casual chat in evening'). Preferences are learned separately for each bucket, allowing context-aware adaptation." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', cursor: 'help' }}>
                {userPreferences.contextBuckets} context buckets
              </Typography>
            </StyledTooltip>
            <StyledTooltip title="Historical data retention period. System maintains 90 days of preference evolution data to detect long-term trends and seasonal patterns in user interaction style." arrow>
              <Chip label="90 days history" size="small" sx={{ height: 18, fontSize: '0.6rem', bgcolor: 'rgba(16, 185, 129, 0.15)', color: '#10B981', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <StyledTooltip title="Preference stability indicator. 'Stable' means preferences haven't changed significantly recently. 'Evolving' indicates active preference shifts. 'Shifting' means major changes detected." arrow>
            <Chip label="Stable" size="small" sx={{ bgcolor: 'rgba(16, 185, 129, 0.2)', color: '#10B981', fontWeight: 600, fontSize: '0.7rem', cursor: 'help' }} />
          </StyledTooltip>
        </Paper>
      </Box>

      {/* Consolidation Engine */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <ScheduleIcon sx={{ fontSize: 24, color: '#F59E0B' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Consolidation Engine
            </Typography>
            <StyledTooltip title="Background 'sleep phases' that transfer experiences from working memory to semantic memory, updating knowledge graphs and behavioral patterns without disrupting active learning." arrow>
              <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <IconButton size="small" sx={{ color: 'text.secondary' }} onClick={loadAMSData}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
          Sleep-like memory integration during system idle periods
        </Typography>

        {consolidationStatus.lastSession ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
            <StyledTooltip title="Number of conversation segments replayed from working memory during last consolidation. Experience replay helps transfer important memories to long-term semantic storage while maintaining context." arrow>
              <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)', cursor: 'help' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  EXPERIENCES REPLAYED
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
                  {consolidationStatus.lastSession.experiencesReplayed}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                  conversations
                </Typography>
              </Box>
            </StyledTooltip>

            <StyledTooltip title="Number of facts extracted and stored in semantic memory during consolidation. Facts are key pieces of information (user preferences, important events, entity relationships) that persist long-term." arrow>
              <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)', cursor: 'help' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  FACTS CONSOLIDATED
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#8B5CF6' }}>
                  {consolidationStatus.lastSession.factsConsolidated}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                  new memories
                </Typography>
              </Box>
            </StyledTooltip>

            <StyledTooltip title="Knowledge graph updates during consolidation. Entities are people, places, concepts extracted from conversations. Relationships connect entities (e.g., 'Michael works_at Company'). Graph enables semantic queries and context-aware retrieval." arrow>
              <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)', cursor: 'help' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  GRAPH UPDATES
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
                  {consolidationStatus.lastSession.graphUpdates.entities + consolidationStatus.lastSession.graphUpdates.relationships}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                  {consolidationStatus.lastSession.graphUpdates.entities} entities, {consolidationStatus.lastSession.graphUpdates.relationships} relations
                </Typography>
              </Box>
            </StyledTooltip>

            <StyledTooltip title="Time taken to complete last consolidation session. Duration depends on number of users processed, amount of new data, and system load. Typical range: 5-15 minutes per batch." arrow>
              <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)', cursor: 'help' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  DURATION
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#F59E0B' }}>
                  {consolidationStatus.lastSession.duration}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                  <CheckIcon sx={{ fontSize: 14, color: '#10B981' }} />
                  <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#10B981', fontWeight: 600 }}>
                    Completed
                  </Typography>
                </Box>
              </Box>
            </StyledTooltip>
          </Box>
        ) : (
          <Box sx={{ p: 3, textAlign: 'center', bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
            <Typography variant="body2" color="text.secondary">
              No consolidation sessions completed yet. First session will run tonight at 2:00 AM.
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Behavioral Learning & User Preferences */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 3, mb: 3 }}>
        <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider', height: '100%' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <BrainIcon sx={{ fontSize: 24, color: '#8B5CF6' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Skill Library
            </Typography>
            <StyledTooltip title="Learned interaction patterns and behavioral skills that AICO adapts based on user feedback and context." arrow>
              <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
            Top performing skills with confidence scores
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {behavioralLearning.topSkills.map((skill, idx) => (
              <StyledTooltip key={idx} title={`${skill.name}: Confidence ${skill.confidence}% based on ${skill.usage} uses. Last feedback was ${skill.lastFeedback}. Confidence increases with positive feedback and decreases with negative feedback.`} arrow>
                <Box sx={{ p: 2, bgcolor: 'rgba(139, 92, 246, 0.05)', borderRadius: '12px', border: '1px solid rgba(139, 92, 246, 0.15)', cursor: 'help' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    {skill.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {skill.lastFeedback === 'positive' && <ThumbUpIcon sx={{ fontSize: 14, color: '#10B981' }} />}
                    {skill.lastFeedback === 'negative' && <ThumbDownIcon sx={{ fontSize: 14, color: '#EF4444' }} />}
                    <Typography variant="caption" sx={{ fontWeight: 700, color: '#8B5CF6' }}>
                      {skill.confidence}%
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress variant="determinate" value={skill.confidence} sx={{ flex: 1, height: 4, borderRadius: 2, bgcolor: 'rgba(139, 92, 246, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#8B5CF6' } }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    {skill.usage} uses
                  </Typography>
                </Box>
              </Box>
            </StyledTooltip>
            ))}
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, fontSize: '0.75rem', textTransform: 'uppercase', color: 'text.secondary' }}>
            Recent Learning
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {behavioralLearning.recentLearning.map((learning, idx) => (
              <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LightbulbIcon sx={{ fontSize: 16, color: '#F59E0B' }} />
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                  {learning}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>

        <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider', height: '100%' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <TrendingIcon sx={{ fontSize: 24, color: '#10B981' }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              User Preferences
            </Typography>
            <StyledTooltip title="16-dimensional preference profile tracking your interaction style across different contexts." arrow>
              <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
            Personalization profile across {userPreferences.contextBuckets} contexts
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 2 }}>
            {userPreferences.dimensions.map((dim, idx) => (
              <StyledTooltip key={idx} title={`${dim.name}: ${(dim.value * 100).toFixed(0)}% (${dim.label}). This dimension tracks your preference for ${dim.name.toLowerCase()} in responses. Value ranges from 0.0 to 1.0, learned from interaction patterns and feedback.`} arrow>
                <Box sx={{ cursor: 'help' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    {dim.name}
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.75rem', color: '#10B981' }}>
                    {dim.label}
                  </Typography>
                </Box>
                  <LinearProgress variant="determinate" value={dim.value * 100} sx={{ height: 6, borderRadius: 3, bgcolor: 'rgba(16, 185, 129, 0.1)', '& .MuiLinearProgress-bar': { bgcolor: '#10B981' } }} />
                </Box>
              </StyledTooltip>
            ))}
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, fontSize: '0.75rem', textTransform: 'uppercase', color: 'text.secondary' }}>
            Context Insights
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {userPreferences.insights.map((insight, idx) => (
              <Chip key={idx} label={insight} size="small" sx={{ justifyContent: 'flex-start', bgcolor: 'rgba(16, 185, 129, 0.1)', color: '#10B981', fontSize: '0.75rem' }} />
            ))}
          </Box>
        </Paper>
      </Box>

      {/* Feedback Integration */}
      <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <ThumbUpIcon sx={{ fontSize: 24, color: '#10B981' }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Feedback Integration
          </Typography>
          <StyledTooltip title="Learning from user interactions through explicit feedback and implicit signals." arrow>
            <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
          </StyledTooltip>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 2, mb: 3 }}>
          <StyledTooltip title={`${feedbackStats.positive} positive feedback events (${safePercentage(feedbackStats.positive, feedbackStats.total)}% of total). Positive feedback increases skill confidence and reinforces preferred interaction patterns.`} arrow>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(16, 185, 129, 0.08)', borderRadius: '12px', cursor: 'help' }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#10B981' }}>
              {feedbackStats.positive}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Positive ({safePercentage(feedbackStats.positive, feedbackStats.total)}%)
            </Typography>
            </Box>
          </StyledTooltip>
          <StyledTooltip title={`${feedbackStats.negative} negative feedback events (${safePercentage(feedbackStats.negative, feedbackStats.total)}% of total). Negative feedback decreases skill confidence and helps identify interaction patterns to avoid.`} arrow>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(239, 68, 68, 0.08)', borderRadius: '12px', cursor: 'help' }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#EF4444' }}>
              {feedbackStats.negative}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Negative ({safePercentage(feedbackStats.negative, feedbackStats.total)}%)
            </Typography>
            </Box>
          </StyledTooltip>
          <StyledTooltip title={`${feedbackStats.neutral} neutral feedback events (${safePercentage(feedbackStats.neutral, feedbackStats.total)}% of total). Neutral feedback indicates acceptable but not exceptional responses. Does not significantly affect confidence scores.`} arrow>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(156, 163, 175, 0.08)', borderRadius: '12px', cursor: 'help' }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#9CA3AF' }}>
              {feedbackStats.neutral}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Neutral ({safePercentage(feedbackStats.neutral, feedbackStats.total)}%)
            </Typography>
            </Box>
          </StyledTooltip>
          <StyledTooltip title={`${feedbackStats.responseRate}% of AI messages receive user feedback. Higher response rate provides more learning signal for skill refinement and preference adaptation.`} arrow>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'rgba(59, 130, 246, 0.08)', borderRadius: '12px', cursor: 'help' }}>
            <Typography variant="h4" sx={{ fontWeight: 700, color: '#3B82F6' }}>
              {feedbackStats.responseRate}%
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Response Rate
            </Typography>
            </Box>
          </StyledTooltip>
        </Box>

        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, fontSize: '0.75rem', textTransform: 'uppercase', color: 'text.secondary' }}>
          Recent Feedback
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {feedbackStats.recentFeedback.map((feedback, idx) => (
            <Box key={idx} sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {feedback.time}
                </Typography>
                {feedback.type === 'positive' && <ThumbUpIcon sx={{ fontSize: 16, color: '#10B981' }} />}
                {feedback.type === 'negative' && <ThumbDownIcon sx={{ fontSize: 16, color: '#EF4444' }} />}
              </Box>
              <Typography variant="body2" sx={{ fontSize: '0.85rem', mb: 0.5 }}>
                "{feedback.message}"
              </Typography>
              <Chip label={feedback.skill} size="small" sx={{ height: 18, fontSize: '0.65rem', bgcolor: 'rgba(139, 92, 246, 0.15)', color: '#8B5CF6' }} />
            </Box>
          ))}
        </Box>
      </Paper>
    </Box>
  );
};
