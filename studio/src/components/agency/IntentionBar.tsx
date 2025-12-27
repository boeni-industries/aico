import React from 'react';
import { Box, Chip, Typography, Paper } from '@mui/material';
import { GoalSummary, GoalOrigin } from '../../types/agency';

interface IntentionBarProps {
  primaryFocus?: GoalSummary;
  activeIntentions: GoalSummary[];
  onGoalClick: (goal: GoalSummary) => void;
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

function ScoreBadge({ score, origin }: { score?: number; origin: GoalOrigin }) {
  if (!score) return null;
  
  const percentage = Math.round(score * 100);
  const colors = originColors[origin];
  
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.5,
        px: 1,
        py: 0.25,
        borderRadius: '8px',
        bgcolor: colors.bg,
        border: '1px solid',
        borderColor: colors.border,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          fontSize: '0.65rem',
          fontWeight: 700,
          fontFamily: 'monospace',
          color: colors.text,
        }}
      >
        {percentage}%
      </Typography>
    </Box>
  );
}

export const IntentionBar: React.FC<IntentionBarProps> = ({
  primaryFocus,
  activeIntentions,
  onGoalClick,
}) => {
  return (
    <Box
      sx={{
        bgcolor: 'background.paper',
        borderRadius: '20px',
        p: 2,
        mb: 2,
        border: '1.5px solid',
        borderColor: 'divider',
        boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Color Legend */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, pb: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Typography
          variant="caption"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontWeight: 600,
            color: 'text.secondary',
            fontSize: '0.7rem',
          }}
        >
          Origin:
        </Typography>
        {Object.entries(originLabels).map(([key, label]) => (
          <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: originColors[key as GoalOrigin].text,
                boxShadow: `0 0 8px ${originColors[key as GoalOrigin].text}40`,
              }}
            />
            <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
              {label}
            </Typography>
          </Box>
        ))}
      </Box>
      {primaryFocus && (
        <Box sx={{ mb: activeIntentions.length > 0 ? 1.5 : 0 }}>
          <Typography
            variant="caption"
            sx={{
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 600,
              color: 'text.secondary',
              mb: 0.75,
              display: 'block',
            }}
          >
            Primary Focus
          </Typography>
          <Paper
            onClick={(e) => {
              e.stopPropagation();
              onGoalClick(primaryFocus);
            }}
            sx={{
              p: 2,
              borderRadius: '16px',
              border: '1.5px solid',
              borderColor: originColors[primaryFocus.origin].border,
              bgcolor: 'background.paper',
              backdropFilter: 'blur(12px)',
              boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                borderColor: originColors[primaryFocus.origin].text,
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  bgcolor: originColors[primaryFocus.origin].text,
                  mt: 0.75,
                  flexShrink: 0,
                  boxShadow: `0 0 12px ${originColors[primaryFocus.origin].text}40`,
                }}
              />
              <Box sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography
                    variant="subtitle2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      textTransform: 'capitalize',
                      color: 'text.primary',
                    }}
                  >
                    {primaryFocus.title}
                  </Typography>
                  <ScoreBadge score={primaryFocus.score} origin={primaryFocus.origin} />
                </Box>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontSize: '0.8rem',
                    lineHeight: 1.4,
                    display: '-webkit-box',
                    WebkitLineClamp: 1,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {primaryFocus.description || 'No description'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  <Chip
                    label={originLabels[primaryFocus.origin]}
                    size="small"
                    sx={{
                      bgcolor: originColors[primaryFocus.origin].bg,
                      color: originColors[primaryFocus.origin].text,
                      border: '1px solid',
                      borderColor: originColors[primaryFocus.origin].border,
                      fontSize: '0.7rem',
                      height: 22,
                      fontWeight: 600,
                    }}
                  />
                  <Chip
                    label={primaryFocus.priority.toUpperCase()}
                    size="small"
                    sx={{
                      bgcolor: 'action.hover',
                      color: 'text.primary',
                      border: '1px solid',
                      borderColor: 'divider',
                      fontSize: '0.7rem',
                      height: 22,
                      fontWeight: 600,
                    }}
                  />
                </Box>
              </Box>
            </Box>
          </Paper>
        </Box>
      )}

      {activeIntentions.length > 0 && (
        <Box>
          <Typography
            variant="caption"
            sx={{
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 600,
              color: 'text.secondary',
              mb: 1,
              display: 'block',
            }}
          >
            Active Intentions ({activeIntentions.length})
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
              gap: 1.5,
            }}
          >
            {activeIntentions.map((intention) => (
              <Paper
                key={intention.goal_id}
                onClick={(e) => {
                  e.stopPropagation();
                  onGoalClick(intention);
                }}
                sx={{
                  p: 1.5,
                  borderRadius: '12px',
                  border: '1.5px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.paper',
                  backdropFilter: 'blur(12px)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                    borderColor: originColors[intention.origin].border,
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: originColors[intention.origin].text,
                      mt: 0.75,
                      flexShrink: 0,
                      boxShadow: `0 0 12px ${originColors[intention.origin].text}40`,
                    }}
                  />
                  <Box sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontWeight: 600,
                          fontSize: '0.8rem',
                          textTransform: 'capitalize',
                          lineHeight: 1.2,
                        }}
                      >
                        {intention.title}
                      </Typography>
                      <ScoreBadge score={intention.score} origin={intention.origin} />
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5, mt: 0.75 }}>
                      <Chip
                        label={originLabels[intention.origin]}
                        size="small"
                        sx={{
                          bgcolor: originColors[intention.origin].bg,
                          color: originColors[intention.origin].text,
                          border: '1px solid',
                          borderColor: originColors[intention.origin].border,
                          fontSize: '0.65rem',
                          height: 20,
                          fontWeight: 600,
                        }}
                      />
                      <Chip
                        label={intention.priority.toUpperCase()}
                        size="small"
                        sx={{
                          bgcolor: 'action.hover',
                          fontSize: '0.65rem',
                          height: 20,
                        }}
                      />
                    </Box>
                  </Box>
                </Box>
              </Paper>
            ))}
          </Box>
        </Box>
      )}

      {!primaryFocus && activeIntentions.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
          No active intentions
        </Typography>
      )}
    </Box>
  );
};
