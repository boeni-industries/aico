import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useToast } from '../common/Toast';
import { Box, Typography, Paper, CircularProgress, Chip } from '@mui/material';
import { Users as PeopleIcon, Smartphone as DevicesIcon, TrendingUp as TrendingUpIcon, RefreshCw as UpdateIcon } from 'lucide-react';
import { UsersListPanel } from './UsersListPanel';
import { SessionsListPanel } from './SessionsListPanel';
import { UserDetailDrawer } from './UserDetailDrawer';
import { SessionDetailDrawer } from './SessionDetailDrawer';
import {
  fetchUsers,
  fetchSessions,
  fetchSessionStatistics,
  revokeSession,
  UserWithSessions,
  SessionWithUser,
  SessionStatsResponse,
} from '../../api/usersSessions';

interface UsersSessionsProps {
  refreshTrigger?: number;
}

export const UsersSessions: React.FC<UsersSessionsProps> = ({ refreshTrigger }) => {
  const { showSuccess, showError } = useToast();
  const [users, setUsers] = useState<UserWithSessions[]>([]);
  const [sessions, setSessions] = useState<SessionWithUser[]>([]);
  const [statistics, setStatistics] = useState<SessionStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUserInteracting, setIsUserInteracting] = useState(false);
  const [hasPendingUpdate, setHasPendingUpdate] = useState(false);
  const [selectedUserUuid, setSelectedUserUuid] = useState<string | null>(null);
  const [userDrawerOpen, setUserDrawerOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState<SessionWithUser | null>(null);
  const [sessionDrawerOpen, setSessionDrawerOpen] = useState(false);
  const interactionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingDataRef = useRef<{
    users: UserWithSessions[];
    sessions: SessionWithUser[];
    statistics: SessionStatsResponse;
  } | null>(null);

  const loadData = async (isBackgroundRefresh = false) => {
    try {
      if (!isBackgroundRefresh) {
        setLoading(true);
      }
      setError(null);

      // Fetch all data in parallel
      const [usersData, sessionsData, statsData] = await Promise.all([
        fetchUsers(),
        fetchSessions({ is_active: true }), // Only active sessions by default
        fetchSessionStatistics(),
      ]);

      // If user is interacting, store data for later
      if (isBackgroundRefresh && isUserInteracting) {
        pendingDataRef.current = {
          users: usersData.users,
          sessions: sessionsData.sessions,
          statistics: statsData,
        };
        setHasPendingUpdate(true);
      } else {
        // Apply updates immediately
        setUsers(usersData.users);
        setSessions(sessionsData.sessions);
        setStatistics(statsData);
        setHasPendingUpdate(false);
        pendingDataRef.current = null;
      }
    } catch (err) {
      console.error('Failed to load users & sessions data:', err);
      if (!isBackgroundRefresh) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      }
    } finally {
      if (!isBackgroundRefresh) {
        setLoading(false);
      }
    }
  };

  // Apply pending updates when user stops interacting
  useEffect(() => {
    if (!isUserInteracting && pendingDataRef.current) {
      setUsers(pendingDataRef.current.users);
      setSessions(pendingDataRef.current.sessions);
      setStatistics(pendingDataRef.current.statistics);
      setHasPendingUpdate(false);
      pendingDataRef.current = null;
    }
  }, [isUserInteracting]);

  // Track user interaction
  const handleUserInteraction = useCallback(() => {
    setIsUserInteracting(true);
    
    // Clear existing timeout
    if (interactionTimeoutRef.current) {
      clearTimeout(interactionTimeoutRef.current);
    }
    
    // Set timeout to mark interaction as ended after 3 seconds of inactivity
    interactionTimeoutRef.current = setTimeout(() => {
      setIsUserInteracting(false);
    }, 3000);
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (interactionTimeoutRef.current) {
        clearTimeout(interactionTimeoutRef.current);
      }
    };
  }, []);

  // Initial load
  useEffect(() => {
    loadData(false);
  }, []);

  // Background refresh on trigger
  useEffect(() => {
    if (refreshTrigger && refreshTrigger > 0) {
      loadData(true);
    }
  }, [refreshTrigger]);

  const handleUserClick = useCallback((user: UserWithSessions) => {
    setSelectedUserUuid(user.uuid);
    setUserDrawerOpen(true);
  }, []);

  const handleCloseUserDrawer = useCallback(() => {
    setUserDrawerOpen(false);
    setTimeout(() => setSelectedUserUuid(null), 300);
  }, []);

  const handleSessionClick = useCallback((session: SessionWithUser) => {
    setSelectedSession(session);
    setSessionDrawerOpen(true);
  }, []);

  const handleCloseSessionDrawer = useCallback(() => {
    setSessionDrawerOpen(false);
    setTimeout(() => setSelectedSession(null), 300);
  }, []);

  const handleRevokeSession = useCallback(async (sessionUuid: string) => {
    try {
      await revokeSession(sessionUuid, 'Revoked by administrator');
      showSuccess('Session revoked successfully');
      await loadData(true);
      handleCloseSessionDrawer();
    } catch (err) {
      console.error('Failed to revoke session:', err);
      showError(err instanceof Error ? err.message : 'Failed to revoke session');
    }
  }, [showSuccess, showError]);

  const activeUsersCount = useMemo(
    () => users.filter(u => u.active_session_count > 0).length,
    [users]
  );

  const sessionTypeCount = useMemo(
    () => Object.keys(statistics?.statistics.sessions_by_type || {}).length,
    [statistics]
  );

  const deviceTypeCount = useMemo(
    () => Object.keys(statistics?.statistics.sessions_by_device_type || {}).length,
    [statistics]
  );

  if (loading && !users.length) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box 
      sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}
      onMouseMove={handleUserInteraction}
      onScroll={handleUserInteraction}
      onClick={handleUserInteraction}
    >
      {/* Pending Update Indicator */}
      {hasPendingUpdate && (
        <Box
          sx={{
            position: 'fixed',
            top: 80,
            right: 24,
            zIndex: 1000,
          }}
        >
          <Chip
            icon={<UpdateIcon sx={{ fontSize: 16 }} />}
            label="Updates available"
            size="small"
            sx={{
              bgcolor: 'rgba(96, 165, 250, 0.15)',
              color: '#60A5FA',
              border: '1px solid',
              borderColor: 'rgba(96, 165, 250, 0.3)',
              fontSize: '0.75rem',
              fontWeight: 600,
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.6 },
              },
            }}
          />
        </Box>
      )}
      {/* Top Row - Statistics Overview */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 2 }}>
          <Paper
            sx={{
              p: 2.5,
              borderRadius: '16px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.3s ease',
              '&:hover': {
                borderColor: '#A78BFA',
                boxShadow: '0 8px 24px rgba(167, 139, 250, 0.15)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  bgcolor: 'rgba(167, 139, 250, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <PeopleIcon sx={{ color: '#A78BFA', fontSize: 28 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  Total Users
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#A78BFA' }}>
                  {users.length}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {activeUsersCount} with active sessions
                </Typography>
              </Box>
            </Box>
          </Paper>
          <Paper
            sx={{
              p: 2.5,
              borderRadius: '16px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.3s ease',
              '&:hover': {
                borderColor: '#60A5FA',
                boxShadow: '0 8px 24px rgba(96, 165, 250, 0.15)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  bgcolor: 'rgba(96, 165, 250, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <DevicesIcon sx={{ color: '#60A5FA', fontSize: 28 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  Active Sessions
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#60A5FA' }}>
                  {statistics?.statistics.active_sessions || 0}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {statistics?.statistics.total_sessions || 0} total sessions
                </Typography>
              </Box>
            </Box>
          </Paper>
          <Paper
            sx={{
              p: 2.5,
              borderRadius: '16px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.3s ease',
              '&:hover': {
                borderColor: '#10B981',
                boxShadow: '0 8px 24px rgba(16, 185, 129, 0.15)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box
                sx={{
                  width: 48,
                  height: 48,
                  borderRadius: '12px',
                  bgcolor: 'rgba(16, 185, 129, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <TrendingUpIcon sx={{ color: '#10B981', fontSize: 28 }} />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  Session Types
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
                  {sessionTypeCount}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                  {deviceTypeCount} device types
                </Typography>
              </Box>
            </Box>
          </Paper>
      </Box>

      {/* Main Content - Two Column Layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, 1fr)' }, gap: 3 }}>
          <UsersListPanel
            users={users}
            onUserClick={handleUserClick}
            loading={loading}
            onInteraction={handleUserInteraction}
          />
          <SessionsListPanel
            sessions={sessions}
            onSessionClick={handleSessionClick}
            loading={loading}
            onInteraction={handleUserInteraction}
          />
      </Box>

      {/* User Detail Drawer */}
      <UserDetailDrawer
        open={userDrawerOpen}
        onClose={handleCloseUserDrawer}
        userUuid={selectedUserUuid}
        onUserUpdated={() => loadData(true)}
      />

      {/* Session Detail Drawer */}
      <SessionDetailDrawer
        open={sessionDrawerOpen}
        onClose={handleCloseSessionDrawer}
        session={selectedSession}
        onRevokeSession={handleRevokeSession}
      />
    </Box>
  );
};
