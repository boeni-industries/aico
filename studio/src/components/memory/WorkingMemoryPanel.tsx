import React, { useState } from 'react';
import { Box, Typography, LinearProgress, Paper, Chip, Select, MenuItem, FormControl, IconButton } from '@mui/material';
import { Clock as TimeIcon, Trash2 as DeleteIcon, Info as InfoIcon, User as PersonIcon, Bot as BotIcon, ChevronDown as ExpandIcon, ChevronUp as CollapseIcon } from 'lucide-react';
import { StyledTooltip } from '../common/StyledTooltip';

interface WorkingMemoryPanelProps {
  activeItems: number;
  capacity: number;
  ttlUtilization: number;
  evictionRate: number;
  recentActivity: Array<{
    id: string;
    timestamp: string;
    action: string;
    conversation_id?: string;
    role?: string;
    preview?: string;
  }>;
}

export const WorkingMemoryPanel: React.FC<WorkingMemoryPanelProps> = ({
  activeItems,
  capacity,
  ttlUtilization,
  evictionRate,
  recentActivity,
}) => {
  const utilizationPercent = (activeItems / capacity) * 100;
  const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
  const [messageCount, setMessageCount] = useState<number>(5);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.1em',
            color: 'text.secondary',
          }}
        >
          Working Memory (LMDB)
        </Typography>
        <StyledTooltip title="Fast, short-term storage for active conversation messages. Messages are kept for 24 hours before automatic cleanup." arrow>
          <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
        </StyledTooltip>
      </Box>

      {/* Metrics Grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              ACTIVE ITEMS
            </Typography>
            <StyledTooltip title="Number of conversation messages currently stored in working memory." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
            {activeItems.toLocaleString()}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            / {capacity.toLocaleString()} capacity
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              TTL UTILIZATION
            </Typography>
            <StyledTooltip title="Average time-to-live usage: how much of the 24-hour retention period has elapsed for stored messages." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#F59E0B' }}>
            {ttlUtilization.toFixed(1)}%
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              EVICTION RATE
            </Typography>
            <StyledTooltip title="Rate at which expired messages are being removed from working memory." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#EF4444' }}>
            {evictionRate.toFixed(2)}/min
          </Typography>
        </Paper>
      </Box>

      {/* Utilization Bar */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Memory Utilization
            </Typography>
            <StyledTooltip title="Percentage of working memory capacity currently in use. Shows how full the active message storage is." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem' }}>
            {utilizationPercent.toFixed(1)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={utilizationPercent}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'rgba(59, 130, 246, 0.12)',
            '& .MuiLinearProgress-bar': {
              bgcolor: utilizationPercent > 80 ? '#EF4444' : utilizationPercent > 60 ? '#F59E0B' : '#3B82F6',
              borderRadius: 4,
            },
          }}
        />
      </Box>

      {/* Recent Messages */}
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              ACTIVE CONTEXT MESSAGES
            </Typography>
            <StyledTooltip title="These are the most recent messages stored in working memory that form AICO's active conversation context. Messages older than 24 hours are automatically moved to semantic memory." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <FormControl size="small" sx={{ minWidth: 80 }}>
            <Select
              value={messageCount}
              onChange={(e) => setMessageCount(e.target.value as number)}
              sx={{
                fontSize: '0.7rem',
                height: 24,
                '& .MuiSelect-select': { py: 0.5, px: 1 },
              }}
            >
              <MenuItem value={5} sx={{ fontSize: '0.7rem' }}>5 msgs</MenuItem>
              <MenuItem value={10} sx={{ fontSize: '0.7rem' }}>10 msgs</MenuItem>
              <MenuItem value={20} sx={{ fontSize: '0.7rem' }}>20 msgs</MenuItem>
              <MenuItem value={50} sx={{ fontSize: '0.7rem' }}>50 msgs</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {recentActivity.length > 0 ? (
            recentActivity.slice(0, messageCount).map((activity, index) => {
              const isExpanded = expandedMessage === activity.id;
              const messageText = activity.preview || 'No content available';
              const shouldTruncate = messageText.length > 100;
              const displayText = isExpanded || !shouldTruncate ? messageText : `${messageText.substring(0, 100)}...`;
              
              return (
                <Box
                  key={activity.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 1.5,
                    p: 1.5,
                    borderRadius: '8px',
                    bgcolor: isExpanded ? 'rgba(255, 255, 255, 0.04)' : 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid',
                    borderColor: isExpanded ? 'rgba(59, 130, 246, 0.3)' : 'divider',
                    cursor: shouldTruncate ? 'pointer' : 'default',
                    transition: 'all 0.2s ease',
                    '&:hover': shouldTruncate ? {
                      bgcolor: 'rgba(255, 255, 255, 0.04)',
                      borderColor: 'rgba(59, 130, 246, 0.2)',
                    } : {},
                  }}
                  onClick={() => shouldTruncate && setExpandedMessage(isExpanded ? null : activity.id)}
                >
                  {activity.role === 'user' ? (
                    <PersonIcon sx={{ fontSize: 18, color: '#3B82F6', mt: 0.2 }} />
                  ) : activity.role === 'assistant' ? (
                    <BotIcon sx={{ fontSize: 18, color: '#8B5CF6', mt: 0.2 }} />
                  ) : (
                    <TimeIcon sx={{ fontSize: 18, color: 'text.secondary', mt: 0.2 }} />
                  )}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                      <Chip
                        label={activity.role?.toUpperCase() || 'UNKNOWN'}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.6rem',
                          fontWeight: 700,
                          bgcolor: activity.role === 'user' ? 'rgba(59, 130, 246, 0.12)' : 'rgba(139, 92, 246, 0.12)',
                          color: activity.role === 'user' ? '#3B82F6' : '#8B5CF6',
                        }}
                      />
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </Typography>
                      {activity.conversation_id && (
                        <StyledTooltip title={`Conversation: ${activity.conversation_id}`} arrow>
                          <Chip
                            label="CONV"
                            size="small"
                            sx={{
                              height: 18,
                              fontSize: '0.55rem',
                              fontWeight: 600,
                              bgcolor: 'rgba(16, 185, 129, 0.12)',
                              color: '#10B981',
                            }}
                          />
                        </StyledTooltip>
                      )}
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', ml: 'auto' }}>
                        #{index + 1}
                      </Typography>
                    </Box>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontSize: '0.8rem', 
                        color: 'text.secondary',
                        whiteSpace: isExpanded ? 'pre-wrap' : 'normal',
                        wordBreak: 'break-word',
                      }}
                    >
                      {displayText}
                    </Typography>
                  </Box>
                  <Box sx={{ width: 28, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {shouldTruncate ? (
                      <IconButton
                        size="small"
                        sx={{ 
                          p: 0.5, 
                          mt: 0.2,
                          color: 'text.secondary',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedMessage(isExpanded ? null : activity.id);
                        }}
                      >
                        {isExpanded ? <CollapseIcon sx={{ fontSize: 16 }} /> : <ExpandIcon sx={{ fontSize: 16 }} />}
                      </IconButton>
                    ) : (
                      <Box sx={{ width: 28, height: 28 }} />
                    )}
                  </Box>
                </Box>
              );
            })
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2, fontSize: '0.8rem' }}>
              No messages in working memory. Messages appear here when you have active conversations.
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
};
