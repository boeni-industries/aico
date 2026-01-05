import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { Plus as AddIcon, Pencil as EditIcon, Trash2 as DeleteIcon } from 'lucide-react';

interface TimelineEvent {
  id: string;
  timestamp: string;
  eventType: 'created' | 'updated' | 'invalidated';
  nodeId: string;
  nodeLabel: string;
  nodeType: string;
  changes?: string[];
}

interface TemporalTimelineProps {
  events: TimelineEvent[];
  onEventClick?: (event: TimelineEvent) => void;
}

const eventTypeConfig = {
  created: {
    icon: AddIcon,
    color: '#10B981',
    bg: 'rgba(16, 185, 129, 0.12)',
    border: 'rgba(16, 185, 129, 0.3)',
    label: 'Created',
  },
  updated: {
    icon: EditIcon,
    color: '#3B82F6',
    bg: 'rgba(59, 130, 246, 0.12)',
    border: 'rgba(59, 130, 246, 0.3)',
    label: 'Updated',
  },
  invalidated: {
    icon: DeleteIcon,
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.12)',
    border: 'rgba(239, 68, 68, 0.3)',
    label: 'Invalidated',
  },
};

export const TemporalTimeline: React.FC<TemporalTimelineProps> = ({
  events,
  onEventClick,
}) => {
  const groupEventsByDate = (events: TimelineEvent[]) => {
    const groups: Record<string, TimelineEvent[]> = {};
    events.forEach((event) => {
      const date = new Date(event.timestamp).toLocaleDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(event);
    });
    return groups;
  };

  const groupedEvents = groupEventsByDate(events);

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
        Graph Evolution Timeline
      </Typography>

      <Box sx={{ position: 'relative' }}>
        {/* Timeline Line */}
        <Box
          sx={{
            position: 'absolute',
            left: 20,
            top: 0,
            bottom: 0,
            width: 2,
            bgcolor: 'divider',
          }}
        />

        {/* Events */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {Object.entries(groupedEvents).map(([date, dateEvents]) => (
            <Box key={date}>
              {/* Date Header */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    bgcolor: 'primary.main',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1,
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem' }}>
                    {new Date(date).getDate()}
                  </Typography>
                </Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {date}
                </Typography>
                <Chip
                  label={`${dateEvents.length} events`}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    bgcolor: 'rgba(139, 92, 246, 0.12)',
                    color: '#8B5CF6',
                  }}
                />
              </Box>

              {/* Events for this date */}
              <Box sx={{ ml: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {dateEvents.map((event) => {
                  const config = eventTypeConfig[event.eventType];
                  const Icon = config.icon;

                  return (
                    <Paper
                      key={event.id}
                      onClick={() => onEventClick?.(event)}
                      sx={{
                        p: 2,
                        borderRadius: '12px',
                        border: '1px solid',
                        borderColor: config.border,
                        bgcolor: config.bg,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        '&:hover': {
                          transform: 'translateX(4px)',
                          boxShadow: `0 4px 12px ${config.color}40`,
                        },
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                        <Box
                          sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '8px',
                            bgcolor: config.bg,
                            border: '1px solid',
                            borderColor: config.border,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                          }}
                        >
                          <Icon sx={{ fontSize: 18, color: config.color }} />
                        </Box>

                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Chip
                              label={config.label}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: '0.6rem',
                                bgcolor: config.bg,
                                color: config.color,
                                border: '1px solid',
                                borderColor: config.border,
                                fontWeight: 700,
                              }}
                            />
                            <Chip
                              label={event.nodeType.toUpperCase()}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: '0.6rem',
                                bgcolor: 'rgba(148, 163, 184, 0.12)',
                                color: '#94A3B8',
                              }}
                            />
                            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', ml: 'auto' }}>
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </Typography>
                          </Box>

                          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem', mb: 0.5 }}>
                            {event.nodeLabel}
                          </Typography>

                          {event.changes && event.changes.length > 0 && (
                            <Box sx={{ mt: 1 }}>
                              {event.changes.map((change, i) => (
                                <Typography
                                  key={i}
                                  variant="caption"
                                  sx={{
                                    fontSize: '0.7rem',
                                    color: 'text.secondary',
                                    display: 'block',
                                  }}
                                >
                                  • {change}
                                </Typography>
                              ))}
                            </Box>
                          )}
                        </Box>
                      </Box>
                    </Paper>
                  );
                })}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
};
