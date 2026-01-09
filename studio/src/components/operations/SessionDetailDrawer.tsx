import React from 'react';
import {
  Box,
  Typography,
  Divider,
  Chip,
  Button,
  Alert,
} from '@mui/material';
import { Clock as ScheduleIcon, User as PersonIcon, Smartphone as DevicesIcon, CheckCircle as CheckCircleIcon, X as CancelIcon, Ban as BlockIcon } from 'lucide-react';
import { DetailDrawer } from '../common/DetailDrawer';
import { SessionWithUser } from '../../api/usersSessions';

interface SessionDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  session: SessionWithUser | null;
  onRevokeSession?: (sessionUuid: string) => void;
}

export const SessionDetailDrawer: React.FC<SessionDetailDrawerProps> = ({
  open,
  onClose,
  session,
  onRevokeSession,
}) => {
  if (!session) return null;

  const getSessionTypeColor = (sessionType: string) => {
    switch (sessionType) {
      case 'admin':
        return '#EF4444';
      case 'unified':
        return '#10B981';
      default:
        return '#60A5FA';
    }
  };

  const handleRevoke = () => {
    if (session && onRevokeSession) {
      onRevokeSession(session.uuid);
    }
  };

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title="Session Details"
      width={450}
    >
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Session Status */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <ScheduleIcon sx={{ fontSize: 24, color: session.is_active ? '#10B981' : '#EF4444' }} />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {session.session_type.charAt(0).toUpperCase() + session.session_type.slice(1)} Session
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    {session.is_active ? (
                      <>
                        <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />
                        <Typography variant="body2" sx={{ color: '#10B981' }}>
                          Active
                        </Typography>
                      </>
                    ) : (
                      <>
                        <CancelIcon sx={{ fontSize: 16, color: '#EF4444' }} />
                        <Typography variant="body2" sx={{ color: '#EF4444' }}>
                          Expired
                        </Typography>
                      </>
                    )}
                  </Box>
                </Box>
                <Chip
                  label={session.session_type}
                  size="small"
                  sx={{
                    bgcolor: `${getSessionTypeColor(session.session_type)}15`,
                    color: getSessionTypeColor(session.session_type),
                    textTransform: 'capitalize',
                  }}
                />
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Session UUID:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {session.uuid}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Time Remaining:
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {session.time_remaining || 'Expired'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Created:
                  </Typography>
                  <Typography variant="body2">
                    {new Date(session.created_at).toLocaleString()}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Expires:
                  </Typography>
                  <Typography variant="body2">
                    {new Date(session.expires_at).toLocaleString()}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Divider />

            {/* User Information */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <PersonIcon sx={{ fontSize: 18, color: '#A78BFA' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  User Information
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Name:
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {session.user_full_name}
                  </Typography>
                </Box>
                {session.user_nickname && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                      Nickname:
                    </Typography>
                    <Typography variant="body2">@{session.user_nickname}</Typography>
                  </Box>
                )}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    User Type:
                  </Typography>
                  <Chip
                    label={session.user_type}
                    size="small"
                    sx={{
                      fontSize: '0.7rem',
                      height: 20,
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    User UUID:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {session.user_uuid}
                  </Typography>
                </Box>
              </Box>
            </Box>

            <Divider />

            {/* Device Information */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <DevicesIcon sx={{ fontSize: 18, color: '#60A5FA' }} />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Device Information
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Device Name:
                  </Typography>
                  <Typography variant="body2">
                    {session.device_name || 'Unknown'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Device Type:
                  </Typography>
                  <Chip
                    label={session.device_type || 'Unknown'}
                    size="small"
                    sx={{
                      fontSize: '0.7rem',
                      height: 20,
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: 140 }}>
                    Device UUID:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {session.device_uuid}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Actions */}
            {session.is_active && (
              <>
                <Divider />
                <Box>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Revoking this session will immediately terminate the user's access.
                  </Alert>
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<BlockIcon />}
                    onClick={handleRevoke}
                    fullWidth
                    sx={{
                      bgcolor: '#EF4444',
                      '&:hover': {
                        bgcolor: '#DC2626',
                      },
                    }}
                  >
                    Revoke Session
                  </Button>
                </Box>
              </>
            )}
          </Box>
    </DetailDrawer>
  );
};
