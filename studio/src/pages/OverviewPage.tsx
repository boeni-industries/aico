import React, { useState, useCallback } from 'react';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
  Button,
  Grid,
  IconButton,
  Tooltip,
} from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import { OverviewMetrics, OverviewDomainKey } from '../data/overview';
import { AgencyCard } from '../components/overview/AgencyCard';
import { EmotionCard } from '../components/overview/EmotionCard';
import { MemoryCard } from '../components/overview/MemoryCard';
import { fetchGraphStats } from '../api/kg';
import { fetchWorkingMemoryStats, fetchSemanticMemoryStats } from '../api/memory';
import { fetchSystemOverview, SystemOverview } from '../api/system';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import { AutoRefreshControls } from '../components/common/AutoRefreshControls';

export interface OverviewPageProps {
  data: OverviewMetrics;
  onOpenDomain: (key: OverviewDomainKey) => void;
}

const statusLabel: Record<OverviewMetrics['systemStatus'], string> = {
  ok: 'Healthy',
  degraded: 'Degraded',
  attention: 'Needs attention',
};

export const OverviewPage: React.FC<OverviewPageProps> = ({ data, onOpenDomain }) => {
  const [kgNodeCount, setKgNodeCount] = useState<number>(0);
  const [kgEdgeCount, setKgEdgeCount] = useState<number>(0);
  const [workingItems, setWorkingItems] = useState<number>(0);
  const [semanticVectors, setSemanticVectors] = useState<number>(0);
  const [retrievalQuality, setRetrievalQuality] = useState<number>(0);
  const [systemOverview, setSystemOverview] = useState<SystemOverview | null>(null);
  const [eventFilter, setEventFilter] = useState<'all' | 'error' | 'warning'>('all');
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  const loadAllStats = useCallback(async () => {
    const [kgStats, workingStats, semanticStats, sysOverview] = await Promise.all([
      fetchGraphStats(),
      fetchWorkingMemoryStats(),
      fetchSemanticMemoryStats(),
      fetchSystemOverview(),
    ]);
    
    setKgNodeCount(kgStats.total_nodes);
    setKgEdgeCount(kgStats.total_edges);
    setWorkingItems(workingStats.active_items);
    setSemanticVectors(semanticStats.total_vectors);
    setRetrievalQuality(Math.round(semanticStats.retrieval_quality_percent));
    setSystemOverview(sysOverview);
  }, []);

  const { autoRefreshEnabled, toggleAutoRefresh, refresh, isRefreshing } = useAutoRefresh({
    onRefresh: loadAllStats,
    interval: 5000,
    defaultEnabled: true,
  });

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Hero band */}
      <Paper
        sx={{
          p: 3,
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          alignItems: { xs: 'flex-start', md: 'center' },
          gap: 2,
          borderRadius: 1,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h1" sx={{ fontSize: '1.6rem', fontWeight: 700, mb: 0.5 }}>
            Studio Overview
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Root hub for AICO&apos;s health, intelligence, memory, agency, security, and system state.
          </Typography>
        </Box>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="center">
          <AutoRefreshControls
            autoRefreshEnabled={autoRefreshEnabled}
            onToggleAutoRefresh={toggleAutoRefresh}
            onRefresh={refresh}
            isRefreshing={isRefreshing}
            intervalSeconds={5}
          />
          <Chip
            icon={
              <CircleIcon
                fontSize="small"
                sx={{
                  color:
                    data.systemStatus === 'ok'
                      ? 'success.main'
                      : data.systemStatus === 'degraded'
                      ? 'warning.main'
                      : 'error.main',
                }}
              />
            }
            label={statusLabel[data.systemStatus]}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
          <Chip
            label={`Uptime ${systemOverview?.uptime_formatted || data.uptime}`}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
          <Chip
            label={`${systemOverview?.active_conversations ?? data.activeConversations} active conversations`}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
          <Chip
            label={`${systemOverview?.active_goals ?? data.activeGoals} active goals`}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
        </Stack>
      </Paper>

      {/* Domain cards grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            md: 'repeat(2, minmax(0, 1fr))',
            xl: 'repeat(3, minmax(0, 1fr))',
          },
          gap: 2,
        }}
      >
        {data.domains.map((domain) => {
          // Special handling for Agency domain - use custom card
          if (domain.key === 'agency') {
            return (
              <AgencyCard
                key={domain.key}
                activeGoals={parseInt(domain.kpiValue)}
                primaryFocus="Practice English Communication"
                curiosityLevel="low"
                lessonsLearned={12}
                onClick={() => onOpenDomain('agency')}
              />
            );
          }

          // Special handling for Emotion domain - use custom card
          if (domain.key === 'emotion') {
            const valence = parseFloat(domain.secondary.find(s => s.label === 'Valence')?.value || '0');
            const arousal = parseFloat(domain.secondary.find(s => s.label === 'Arousal')?.value || '0');
            return (
              <EmotionCard
                key={domain.key}
                currentState={domain.kpiValue}
                valence={valence}
                arousal={arousal}
                onClick={() => onOpenDomain('emotion')}
              />
            );
          }

          // Special handling for Memory domain - use custom card
          if (domain.key === 'memory') {
            return (
              <MemoryCard
                key={domain.key}
                workingMemoryItems={workingItems}
                semanticVectors={semanticVectors}
                knowledgeGraphNodes={kgNodeCount}
                knowledgeGraphEdges={kgEdgeCount}
                retrievalQuality={retrievalQuality}
                onClick={() => onOpenDomain('memory')}
              />
            );
          }
          
          // Default card for other domains
          return (
          <Paper
            key={domain.key}
            sx={{
              p: 2.5,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: 1.5,
              borderRadius: 1,
              border: domain.isImplemented
                ? '2px solid rgba(33, 150, 243, 0.3)' // Blue for implemented
                : '2px solid rgba(239, 83, 80, 0.3)', // Red-ish for mock
              position: 'relative',
            }}
          >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {domain.title}
                  </Typography>
                  {!domain.isImplemented && (
                    <Chip
                      label="Mock"
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        bgcolor: 'rgba(239, 83, 80, 0.15)',
                        color: 'rgb(239, 83, 80)',
                        border: '1px solid rgba(239, 83, 80, 0.4)',
                      }}
                    />
                  )}
                </Box>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ fontFamily: 'monospace' }}
                >
                  {domain.kpiLabel}
                </Typography>
              </Box>

              <Typography variant="h2" sx={{ fontSize: '1.4rem', fontWeight: 700 }}>
                {domain.kpiValue}
              </Typography>

              <Stack direction="row" spacing={2} flexWrap="wrap">
                {domain.secondary.map((metric) => (
                  <Box key={metric.label} sx={{ minWidth: 0 }}>
                    <Typography variant="caption" color="text.secondary">
                      {metric.label}
                    </Typography>
                    <Typography variant="body2">{metric.value}</Typography>
                  </Box>
                ))}
              </Stack>

              <Box sx={{ flex: 1 }} />
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  size="small"
                  endIcon={<ArrowForwardIcon fontSize="small" />}
                  onClick={() => onOpenDomain(domain.key)}
                >
                  Open {domain.title}
                </Button>
              </Box>
            </Paper>
          );
        })}
      </Box>

      {/* Events / anomalies list */}
      <Paper sx={{ p: 2.5, borderRadius: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Recent events & anomalies
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" color="text.secondary">
              Filter:
            </Typography>
            <Stack direction="row" spacing={0.5}>
              <Chip
                label="All"
                size="small"
                onClick={() => setEventFilter('all')}
                sx={{
                  bgcolor: eventFilter === 'all' ? 'primary.main' : 'transparent',
                  color: eventFilter === 'all' ? 'white' : 'text.secondary',
                  border: '1px solid',
                  borderColor: eventFilter === 'all' ? 'primary.main' : 'divider',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: eventFilter === 'all' ? 'primary.dark' : 'action.hover' },
                }}
              />
              <Chip
                label="Errors"
                size="small"
                onClick={() => setEventFilter('error')}
                sx={{
                  bgcolor: eventFilter === 'error' ? 'error.main' : 'transparent',
                  color: eventFilter === 'error' ? 'white' : 'text.secondary',
                  border: '1px solid',
                  borderColor: eventFilter === 'error' ? 'error.main' : 'divider',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: eventFilter === 'error' ? 'error.dark' : 'action.hover' },
                }}
              />
              <Chip
                label="Warnings"
                size="small"
                onClick={() => setEventFilter('warning')}
                sx={{
                  bgcolor: eventFilter === 'warning' ? 'warning.main' : 'transparent',
                  color: eventFilter === 'warning' ? 'white' : 'text.secondary',
                  border: '1px solid',
                  borderColor: eventFilter === 'warning' ? 'warning.main' : 'divider',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: eventFilter === 'warning' ? 'warning.dark' : 'action.hover' },
                }}
              />
            </Stack>
          </Stack>
        </Box>

        <Stack spacing={0.5}>
          {systemOverview && systemOverview.recent_events.length > 0 ? (
            systemOverview.recent_events
              .filter(event => eventFilter === 'all' || event.severity === eventFilter)
              .map((event, index) => (
              <Box
                key={index}
                onClick={() => setExpandedEvent(expandedEvent === index ? null : index)}
                sx={{
                  display: 'flex',
                  gap: 1,
                  p: 1,
                  bgcolor: 'background.default',
                  borderRadius: 1,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' },
                  transition: 'background-color 0.2s',
                }}
              >
                <Chip
                  label={event.severity === 'error' ? 'ERR' : 'WARN'}
                  size="small"
                  sx={{
                    bgcolor: event.severity === 'error' ? 'error.main' : 'warning.main',
                    color: 'white',
                    fontWeight: 600,
                    fontSize: '0.6rem',
                    height: 18,
                    minWidth: 40,
                  }}
                />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ minWidth: 'fit-content' }}>
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.875rem', flex: 1 }}>
                      {event.title}
                    </Typography>
                    {event.count > 1 && (
                      <Chip
                        label={`×${event.count}`}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.65rem',
                          bgcolor: 'action.selected',
                          fontWeight: 600,
                        }}
                      />
                    )}
                  </Box>
                  {expandedEvent === index && (
                    <>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, mb: 0.5 }}>
                        {event.description}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Latest: {new Date(event.timestamp).toLocaleString()} · {event.domain}
                      </Typography>
                    </>
                  )}
                </Box>
              </Box>
            ))
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
              No recent events available
            </Typography>
          )}
        </Stack>
      </Paper>
    </Box>
  );
};
