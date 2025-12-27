import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { Chat as ChatIcon, Person as PersonIcon, CalendarToday as CalendarIcon } from '@mui/icons-material';

interface Conversation {
  id: string;
  title: string;
  timestamp: string;
  person: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  messageCount: number;
  tags: string[];
}

interface MemoryAlbumPanelProps {
  conversations: Conversation[];
  onConversationClick?: (conversation: Conversation) => void;
}

const sentimentColors = {
  positive: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
  neutral: { bg: 'rgba(148, 163, 184, 0.12)', text: '#94A3B8', border: 'rgba(148, 163, 184, 0.3)' },
  negative: { bg: 'rgba(239, 68, 68, 0.12)', text: '#EF4444', border: 'rgba(239, 68, 68, 0.3)' },
};

export const MemoryAlbumPanel: React.FC<MemoryAlbumPanelProps> = ({
  conversations,
  onConversationClick,
}) => {
  return (
    <Box>
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          mb: 2,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
          color: 'text.secondary',
        }}
      >
        Memory Album
      </Typography>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>
        {conversations.map((conversation) => (
          <Paper
            key={conversation.id}
            onClick={() => onConversationClick?.(conversation)}
            sx={{
              p: 2.5,
              borderRadius: '16px',
              border: '1.5px solid',
              borderColor: 'divider',
              bgcolor: 'background.paper',
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                borderColor: 'primary.main',
              },
            }}
          >
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    mb: 0.5,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {conversation.title}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <PersonIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    {conversation.person}
                  </Typography>
                </Box>
              </Box>
              <Chip
                label={conversation.sentiment.toUpperCase()}
                size="small"
                sx={{
                  height: 20,
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  bgcolor: sentimentColors[conversation.sentiment].bg,
                  color: sentimentColors[conversation.sentiment].text,
                  border: '1px solid',
                  borderColor: sentimentColors[conversation.sentiment].border,
                }}
              />
            </Box>

            {/* Metadata */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <CalendarIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {conversation.timestamp}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <ChatIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {conversation.messageCount} messages
                </Typography>
              </Box>
            </Box>

            {/* Tags */}
            {conversation.tags.length > 0 && (
              <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                {conversation.tags.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: '0.65rem',
                      bgcolor: 'rgba(139, 92, 246, 0.12)',
                      color: '#8B5CF6',
                      border: '1px solid rgba(139, 92, 246, 0.2)',
                    }}
                  />
                ))}
              </Box>
            )}
          </Paper>
        ))}
      </Box>
    </Box>
  );
};
