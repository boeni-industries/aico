import React, { useState, useEffect } from 'react';
import { useToast } from '../common/Toast';
import { DetailDrawer } from '../common/DetailDrawer';
import {
  Box,
  Typography,
  Divider,
  Chip,
  Button,
  ButtonGroup,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  Computer as SystemIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Lock as LockIcon,
  LockOpen as LockOpenIcon,
  Devices as DevicesIcon,
  Schedule as ScheduleIcon,
  Block as BlockIcon,
  DeleteSweep as DeleteSweepIcon,
} from '@mui/icons-material';
import { fetchUserDetail, lockUnlockUser, revokeAllUserSessions, cleanupExpiredSessions, UserDetailResponse } from '../../api/usersSessions';

interface UserDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  userUuid: string | null;
  onUserUpdated?: () => void;
}

export const UserDetailDrawer: React.FC<UserDetailDrawerProps> = ({
  open,
  onClose,
  userUuid,
  onUserUpdated,
}) => {
  const { showSuccess, showError } = useToast();
  const [userDetail, setUserDetail] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && userUuid) {
      loadUserDetail();
    }
  }, [open, userUuid]);

  const loadUserDetail = async () => {
    if (!userUuid) return;

    try {
      setLoading(true);
      setError(null);
      const data = await fetchUserDetail(userUuid);
      setUserDetail(data);
    } catch (err) {
      console.error('Failed to load user detail:', err);
      setError(err instanceof Error ? err.message : 'Failed to load user details');
    } finally {
      setLoading(false);
    }
  };

  const handleLockUnlock = async (lock: boolean) => {
    if (!userUuid) return;
    
    try {
      const result = await lockUnlockUser(userUuid, lock, lock ? 'Locked by administrator' : 'Unlocked by administrator');
      showSuccess(result.message);
      await loadUserDetail();
      onUserUpdated?.();
    } catch (err) {
      showError(err instanceof Error ? err.message : `Failed to ${lock ? 'lock' : 'unlock'} user`);
    }
  };

  const handleRevokeAllSessions = async () => {
    if (!userUuid) return;
    
    try {
      const result = await revokeAllUserSessions(userUuid, 'Revoked by administrator');
      showSuccess(result.message);
      await loadUserDetail();
      onUserUpdated?.();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to revoke sessions');
    }
  };

  const handleCleanupExpiredSessions = async () => {
    if (!userUuid) return;
    
    try {
      const result = await cleanupExpiredSessions(userUuid);
      showSuccess(result.message);
      await loadUserDetail();
      onUserUpdated?.();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to cleanup expired sessions');
    }
  };

  const getUserTypeIcon = (userType: string) => {
    switch (userType) {
      case 'admin':
        return <AdminIcon sx={{ fontSize: 20, color: '#A78BFA' }} />;
      case 'system':
        return <SystemIcon sx={{ fontSize: 20, color: '#60A5FA' }} />;
      default:
        return <PersonIcon sx={{ fontSize: 20, color: '#10B981' }} />;
    }
  };

  const getUserTypeColor = (userType: string) => {
    switch (userType) {
      case 'admin':
        return '#A78BFA';
      case 'system':
        return '#60A5FA';
      default:
        return '#10B981';
    }
  };

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title="User Details"
      width={500}
    >
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity="error">{error}</Alert>
          ) : userDetail ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {/* User Profile Section */}
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  {getUserTypeIcon(userDetail.user.user_type)}
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {userDetail.user.full_name}
                    </Typography>
                    {userDetail.user.nickname && (
                      <Typography variant="body2" color="text.secondary">
                        @{userDetail.user.nickname}
                      </Typography>
                    )}
                  </Box>
                  <Chip
                    label={userDetail.user.user_type}
                    size="small"
                    sx={{
                      bgcolor: `${getUserTypeColor(userDetail.user.user_type)}15`,
                      color: getUserTypeColor(userDetail.user.user_type),
                      textTransform: 'capitalize',
                    }}
                  />
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                      UUID:
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {userDetail.user.uuid}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                      Status:
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {userDetail.user.is_active ? (
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
                            Inactive
                          </Typography>
                        </>
                      )}
                    </Box>
                  </Box>
                  {userDetail.user.primary_language && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                        Language:
                      </Typography>
                      <Typography variant="body2">{userDetail.user.primary_language}</Typography>
                    </Box>
                  )}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                      Created:
                    </Typography>
                    <Typography variant="body2">
                      {new Date(userDetail.user.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Divider />

              {/* Credentials Section */}
              {userDetail.credentials && (
                <>
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                      Authentication
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                          PIN Status:
                        </Typography>
                        <Chip
                          label={userDetail.credentials.has_pin ? 'Configured' : 'Not Set'}
                          size="small"
                          sx={{
                            bgcolor: userDetail.credentials.has_pin
                              ? 'rgba(16, 185, 129, 0.15)'
                              : 'rgba(107, 114, 128, 0.15)',
                            color: userDetail.credentials.has_pin ? '#10B981' : '#6B7280',
                            fontSize: '0.7rem',
                            height: 20,
                          }}
                        />
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                          Failed Attempts:
                        </Typography>
                        <Typography variant="body2">
                          {userDetail.credentials.failed_attempts}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                          Account Lock:
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          {userDetail.credentials.is_locked ? (
                            <>
                              <LockIcon sx={{ fontSize: 16, color: '#EF4444' }} />
                              <Typography variant="body2" sx={{ color: '#EF4444' }}>
                                Locked
                              </Typography>
                            </>
                          ) : (
                            <>
                              <LockOpenIcon sx={{ fontSize: 16, color: '#10B981' }} />
                              <Typography variant="body2" sx={{ color: '#10B981' }}>
                                Unlocked
                              </Typography>
                            </>
                          )}
                        </Box>
                      </Box>
                      {userDetail.credentials.last_login && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120 }}>
                            Last Login:
                          </Typography>
                          <Typography variant="body2">
                            {new Date(userDetail.credentials.last_login).toLocaleString()}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>
                  <Divider />
                </>
              )}

              {/* Statistics Section */}
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                  Session Statistics
                </Typography>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid',
                      borderColor: 'rgba(16, 185, 129, 0.2)',
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Active Sessions
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#10B981' }}>
                      {userDetail.statistics.active_sessions}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: 'rgba(96, 165, 250, 0.1)',
                      border: '1px solid',
                      borderColor: 'rgba(96, 165, 250, 0.2)',
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Total Sessions
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#60A5FA' }}>
                      {userDetail.statistics.total_sessions}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid',
                      borderColor: 'rgba(239, 68, 68, 0.2)',
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Expired Sessions
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#EF4444' }}>
                      {userDetail.statistics.expired_sessions}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: 'rgba(167, 139, 250, 0.1)',
                      border: '1px solid',
                      borderColor: 'rgba(167, 139, 250, 0.2)',
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Devices
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#A78BFA' }}>
                      {userDetail.statistics.registered_devices}
                    </Typography>
                  </Box>
                </Box>
              </Box>

              <Divider />

              {/* Management Actions */}
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                  Management Actions
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {userDetail.credentials?.is_locked ? (
                    <Button
                      variant="contained"
                      startIcon={<LockOpenIcon />}
                      onClick={() => handleLockUnlock(false)}
                      fullWidth
                      sx={{
                        bgcolor: '#10B981',
                        '&:hover': { bgcolor: '#059669' },
                      }}
                    >
                      Unlock Account
                    </Button>
                  ) : (
                    <Button
                      variant="outlined"
                      color="error"
                      startIcon={<LockIcon />}
                      onClick={() => handleLockUnlock(true)}
                      fullWidth
                    >
                      Lock Account
                    </Button>
                  )}
                  {userDetail.statistics.active_sessions > 0 && (
                    <Button
                      variant="outlined"
                      color="warning"
                      startIcon={<DeleteSweepIcon />}
                      onClick={handleRevokeAllSessions}
                      fullWidth
                    >
                      Revoke All Sessions ({userDetail.statistics.active_sessions})
                    </Button>
                  )}
                  {userDetail.statistics.expired_sessions > 0 && (
                    <Button
                      variant="outlined"
                      color="info"
                      startIcon={<DeleteSweepIcon />}
                      onClick={handleCleanupExpiredSessions}
                      fullWidth
                    >
                      Clean Up Expired Sessions ({userDetail.statistics.expired_sessions})
                    </Button>
                  )}
                </Box>
              </Box>

              <Divider />

              {/* Active Sessions Section */}
              {userDetail.active_sessions.length > 0 && (
                <>
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <ScheduleIcon sx={{ fontSize: 18, color: '#10B981' }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        Active Sessions ({userDetail.active_sessions.length})
                      </Typography>
                    </Box>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ fontSize: '0.75rem', fontWeight: 600 }}>Type</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                              Time Remaining
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.75rem', fontWeight: 600 }}>Created</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {userDetail.active_sessions.map((session) => {
                            const isExpired = session.time_remaining === 'Expired' || !session.is_active;
                            return (
                            <TableRow 
                              key={session.uuid}
                              sx={{
                                bgcolor: isExpired ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)',
                                borderLeft: '3px solid',
                                borderLeftColor: isExpired ? '#EF4444' : '#10B981',
                              }}
                            >
                              <TableCell>
                                <Chip
                                  label={session.session_type}
                                  size="small"
                                  sx={{
                                    fontSize: '0.7rem',
                                    height: 20,
                                    textTransform: 'capitalize',
                                  }}
                                />
                              </TableCell>
                              <TableCell sx={{ fontSize: '0.8rem', color: isExpired ? '#EF4444' : '#10B981', fontWeight: 600 }}>
                                {session.time_remaining}
                              </TableCell>
                              <TableCell sx={{ fontSize: '0.8rem' }}>
                                {new Date(session.created_at).toLocaleString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </TableCell>
                            </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                  <Divider />
                </>
              )}

              {/* Devices Section */}
              {userDetail.devices.length > 0 && (
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <DevicesIcon sx={{ fontSize: 18, color: '#60A5FA' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Registered Devices ({userDetail.devices.length})
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {userDetail.devices.map((device) => (
                      <Box
                        key={device.uuid}
                        sx={{
                          p: 2,
                          borderRadius: '12px',
                          bgcolor: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {device.device_name}
                          </Typography>
                          <Chip
                            label={device.device_type}
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: 18,
                              textTransform: 'capitalize',
                            }}
                          />
                          {device.is_active && (
                            <Chip
                              label="Active"
                              size="small"
                              sx={{
                                bgcolor: 'rgba(16, 185, 129, 0.15)',
                                color: '#10B981',
                                fontSize: '0.7rem',
                                height: 18,
                              }}
                            />
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          Platform: {device.platform}
                        </Typography>
                        {device.last_seen && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            Last seen: {new Date(device.last_seen).toLocaleString()}
                          </Typography>
                        )}
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          ) : null}
    </DetailDrawer>
  );
};
