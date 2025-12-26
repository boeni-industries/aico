import React from 'react';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
  Button,
} from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { OverviewMetrics, OverviewDomainKey } from '../data/overview';

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
            label={`Uptime ${data.uptime}`}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
          <Chip
            label={`${data.activeConversations} active conversations`}
            variant="outlined"
            sx={{ borderRadius: 999 }}
          />
          <Chip
            label={`${data.activeGoals} active goals`}
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
        {data.domains.map((domain) => (
          <Paper
            key={domain.key}
            sx={{
              p: 2.5,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: 1.5,
            }}
          >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {domain.title}
                </Typography>
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
        ))}
      </Box>

      {/* Events / anomalies list */}
      <Paper sx={{ p: 2.5 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Recent events & anomalies
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Placeholder data – wired to backend event stream later.
          </Typography>
        </Box>

        <Stack spacing={1.25}>
          {data.events.map((event) => (
            <Box
              key={event.id}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
              }}
            >
              <Chip
                size="small"
                label={event.severity.toUpperCase()}
                color={
                  event.severity === 'error'
                    ? 'error'
                    : event.severity === 'warning'
                    ? 'warning'
                    : 'default'
                }
                variant={event.severity === 'info' ? 'outlined' : 'filled'}
              />
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {event.title}
                </Typography>
                {event.description && (
                  <Typography variant="body2" color="text.secondary">
                    {event.description}
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary">
                  {/* Time is a plain string for now; can be replaced with relative time later. */}
                  {event.time}
                  {event.domain !== 'overview' && ` · ${event.domain}`}
                </Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Paper>
    </Box>
  );
};
