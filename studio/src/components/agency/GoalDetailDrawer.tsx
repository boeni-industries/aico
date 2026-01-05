import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Divider,
  CircularProgress,
} from '@mui/material';
import { DetailDrawer } from '../common/DetailDrawer';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import PauseCircleIcon from '@mui/icons-material/PauseCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { GoalResponse, GoalOrigin, GoalPriority } from '../../types/agency';
import { formatDistanceToNow } from 'date-fns';

interface GoalDetailDrawerProps {
  open: boolean;
  goal: GoalResponse | null;
  loading?: boolean;
  onClose: () => void;
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

const statusIcons: Record<string, React.ReactElement> = {
  completed: <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />,
  running: <CircularProgress size={14} sx={{ color: 'primary.main' }} />,
  pending: <RadioButtonUncheckedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />,
  paused: <PauseCircleIcon sx={{ fontSize: 16, color: 'warning.main' }} />,
  failed: <CancelIcon sx={{ fontSize: 16, color: 'error.main' }} />,
};

export const GoalDetailDrawer: React.FC<GoalDetailDrawerProps> = ({
  open,
  goal,
  loading,
  onClose,
}) => {
  if (!goal && !loading) return null;

  const planSteps = goal?.metadata?.plan_steps || [];
  const createdAge = goal
    ? formatDistanceToNow(new Date(goal.created_at), { addSuffix: true })
    : '';
  const updatedAge = goal
    ? formatDistanceToNow(new Date(goal.updated_at), { addSuffix: true })
    : '';

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title="Goal Details"
      width={480}
    >
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : goal ? (
        <>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  bgcolor: originColors[goal.origin],
                  mt: 0.5,
                  mr: 1.5,
                  flexShrink: 0,
                }}
              />
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 600,
                  lineHeight: 1.3,
                  textTransform: 'capitalize',
                }}
              >
                {goal.title}
              </Typography>
            </Box>

            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 2,
                p: 2.5,
                bgcolor: 'background.paper',
                borderRadius: '16px',
                border: '1.5px solid',
                borderColor: 'divider',
                backdropFilter: 'blur(12px)',
                boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
              }}
            >
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Origin
                </Typography>
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
                  }}
                />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Priority
                </Typography>
                <Chip
                  label={goal.priority.toUpperCase()}
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
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Status
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: 500, textTransform: 'capitalize' }}
                >
                  {goal.status}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Type
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: 500, textTransform: 'capitalize' }}
                >
                  {goal.goal_type}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Created
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {createdAge}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  Updated
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {updatedAge}
                </Typography>
              </Box>
            </Box>
          </Box>

          <Divider sx={{ my: 3 }} />

          {goal.description && (
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: 600, mb: 1, textTransform: 'uppercase', fontSize: '0.75rem' }}
              >
                Description
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                {goal.description}
              </Typography>
            </Box>
          )}

          {goal.metadata?.plan_id && (
            <>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 2 }}>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      bgcolor: originColors[goal.origin],
                      mt: 0.5,
                      mr: 1.5,
                      flexShrink: 0,
                    }}
                  />
                  <Typography
                    variant="h5"
                    sx={{
                      fontWeight: 600,
                      lineHeight: 1.3,
                      textTransform: 'capitalize',
                    }}
                  >
                    {goal.title}
                  </Typography>
                </Box>

                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 2,
                    p: 2.5,
                    bgcolor: 'background.paper',
                    borderRadius: '16px',
                    border: '1.5px solid',
                    borderColor: 'divider',
                    backdropFilter: 'blur(12px)',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                  }}
                >
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Origin
                    </Typography>
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
                      }}
                    />
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Priority
                    </Typography>
                    <Chip
                      label={goal.priority.toUpperCase()}
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
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Status
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 500, textTransform: 'capitalize' }}
                    >
                      {goal.status}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Type
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 500, textTransform: 'capitalize' }}
                    >
                      {goal.goal_type}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Created
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {createdAge}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      Updated
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {updatedAge}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Divider sx={{ my: 3 }} />

              {goal.description && (
                <Box sx={{ mb: 3 }}>
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: 600, mb: 1, textTransform: 'uppercase', fontSize: '0.75rem' }}
                  >
                    Description
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
                    {goal.description}
                  </Typography>
                </Box>
              )}

              {goal.metadata?.plan_id && (
                <>
                  <Divider sx={{ my: 3 }} />

                  <Box sx={{ mb: 3 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: 600, mb: 1, textTransform: 'uppercase', fontSize: '0.75rem' }}
                    >
                      Plan
                    </Typography>
                    <Box
                      sx={{
                        p: 2.5,
                        bgcolor: 'background.paper',
                        borderRadius: '16px',
                        border: '1.5px solid',
                        borderColor: 'divider',
                        backdropFilter: 'blur(12px)',
                        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                        mb: 2,
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.5 }}>
                        {goal.metadata.plan_title || 'Untitled Plan'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Strategy: {goal.metadata.plan_strategy || 'Unknown'}
                      </Typography>
                    </Box>

                    {planSteps.length > 0 && (
                      <Box sx={{ pl: 1 }}>
                        {planSteps.map((step: any, index: number) => (
                          <Box
                            key={index}
                            sx={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              mb: 2,
                              pl: 2,
                              borderLeft: 2,
                              borderColor: 'divider',
                            }}
                          >
                            <Box sx={{ mr: 1.5, mt: 0.25 }}>
                              {statusIcons[step.status] || statusIcons.pending}
                            </Box>
                            <Box sx={{ flexGrow: 1 }}>
                              <Typography variant="body2" sx={{ fontWeight: 500, mb: 0.25 }}>
                                {step.title || `Step ${index + 1}`}
                              </Typography>
                              {step.skill && (
                                <Typography variant="caption" color="text.secondary">
                                  Skill: {step.skill}
                                </Typography>
                              )}
                              {step.duration && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{ ml: 1 }}
                                >
                                  ({step.duration})
                                </Typography>
                              )}
                            </Box>
                          </Box>
                        ))}
                      </Box>
                    )}
                  </Box>
                </>
              )}

              {goal.metadata?.provenance && (
                <>
                  <Divider sx={{ my: 3 }} />

                  <Box sx={{ mb: 3 }}>
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}
                    >
                      Provenance Chain
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                      {goal.metadata.provenance.conversation && (
                        <Box
                          sx={{
                            p: 2,
                            bgcolor: 'rgba(59, 130, 246, 0.08)',
                            borderRadius: '12px',
                            border: '1px solid',
                            borderColor: 'rgba(59, 130, 246, 0.2)',
                          }}
                        >
                          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                            SOURCE CONVERSATION
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500, color: '#3B82F6' }}>
                            {goal.metadata.provenance.conversation}
                          </Typography>
                        </Box>
                      )}
                      {goal.metadata.provenance.memory && (
                        <Box
                          sx={{
                            p: 2,
                            bgcolor: 'rgba(139, 92, 246, 0.08)',
                            borderRadius: '12px',
                            border: '1px solid',
                            borderColor: 'rgba(139, 92, 246, 0.2)',
                          }}
                        >
                          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                            MEMORY REFERENCE
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500, color: '#8B5CF6' }}>
                            {goal.metadata.provenance.memory}
                          </Typography>
                        </Box>
                      )}
                      {goal.metadata.provenance.emotion && (
                        <Box
                          sx={{
                            p: 2,
                            bgcolor: 'rgba(236, 72, 153, 0.08)',
                            borderRadius: '12px',
                            border: '1px solid',
                            borderColor: 'rgba(236, 72, 153, 0.2)',
                          }}
                        >
                          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                            EMOTIONAL CONTEXT
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 500, color: '#EC4899' }}>
                            {goal.metadata.provenance.emotion}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                </>
              )}

              {goal.metadata?.executions && (
                <>
                  <Divider sx={{ my: 3 }} />

                  <Box>
                    <Typography
                      variant="subtitle2"
                      sx={{ fontWeight: 600, mb: 2, textTransform: 'uppercase', fontSize: '0.75rem' }}
                    >
                      Execution History
                    </Typography>
                    <Box
                      sx={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: 1.5,
                      }}
                    >
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: 'rgba(16, 185, 129, 0.08)',
                          borderRadius: '12px',
                          border: '1px solid',
                          borderColor: 'rgba(16, 185, 129, 0.2)',
                        }}
                      >
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                          COMPLETED
                        </Typography>
                        <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
                          {goal.metadata.executions.completed || 0}
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: 'rgba(59, 130, 246, 0.08)',
                          borderRadius: '12px',
                          border: '1px solid',
                          borderColor: 'rgba(59, 130, 246, 0.2)',
                        }}
                      >
                        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                          RUNNING
                        </Typography>
                        <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
                          {goal.metadata.executions.running || 0}
                        </Typography>
                      </Box>
                    </Box>
                    {(goal.metadata.executions.total_time || goal.metadata.executions.last_run) && (
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: '12px' }}>
                        {goal.metadata.executions.total_time && (
                          <Typography variant="body2" sx={{ mb: 0.5, fontSize: '0.85rem' }}>
                            <strong>Total Time:</strong> {goal.metadata.executions.total_time}
                          </Typography>
                        )}
                        {goal.metadata.executions.last_run && (
                          <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                            <strong>Last Run:</strong> {goal.metadata.executions.last_run}
                          </Typography>
                        )}
                      </Box>
                    )}
                  </Box>
                </>
              )}
            </>
          )}
        </>
      ) : null}
    </DetailDrawer>
  );
};
