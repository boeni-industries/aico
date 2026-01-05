import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  TextField,
  InputAdornment,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  SelectChangeEvent,
  Menu,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { Search as SearchIcon, User as PersonIcon, ShieldCheck as AdminIcon, Monitor as SystemIcon, Circle as CircleIcon, Lock as LockIcon, CheckCircle as CheckCircleIcon, ChevronLeft as ChevronLeftIcon, ChevronRight as ChevronRightIcon, Download as DownloadIcon, MoreVertical as MoreVertIcon } from 'lucide-react';
import { UserWithSessions } from '../../api/usersSessions';
import { exportUsersToCSV, exportUsersToJSON } from '../../utils/exportData';

interface UsersListPanelProps {
  users: UserWithSessions[];
  onUserClick?: (user: UserWithSessions) => void;
  loading?: boolean;
  onInteraction?: () => void;
}

export const UsersListPanel: React.FC<UsersListPanelProps> = React.memo(({
  users,
  onUserClick,
  loading = false,
  onInteraction,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [userTypeFilter, setUserTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);

  // Filter users with useMemo to prevent recalculation on every render
  const filteredUsers = useMemo(() => users.filter(user => {
    const matchesSearch = 
      user.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.uuid.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (user.nickname && user.nickname.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesType = userTypeFilter === 'all' || user.user_type === userTypeFilter;
    const matchesStatus = 
      statusFilter === 'all' ||
      (statusFilter === 'active' && user.is_active) ||
      (statusFilter === 'inactive' && !user.is_active) ||
      (statusFilter === 'has_sessions' && user.active_session_count > 0);
    
    return matchesSearch && matchesType && matchesStatus;
  }), [users, searchQuery, userTypeFilter, statusFilter]);

  // Paginated users
  const paginatedUsers = useMemo(
    () => filteredUsers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [filteredUsers, page, rowsPerPage]
  );

  // Reset page when filters change
  React.useEffect(() => {
    setPage(0);
  }, [searchQuery, userTypeFilter, statusFilter]);

  const handleChangePage = (newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: SelectChangeEvent<number>) => {
    setRowsPerPage(Number(event.target.value));
    setPage(0);
  };

  const handleExportClick = (event: React.MouseEvent<HTMLElement>) => {
    setExportMenuAnchor(event.currentTarget);
  };

  const handleExportClose = () => {
    setExportMenuAnchor(null);
  };

  const handleExportCSV = () => {
    exportUsersToCSV(filteredUsers);
    handleExportClose();
  };

  const handleExportJSON = () => {
    exportUsersToJSON(filteredUsers);
    handleExportClose();
  };

  const getUserTypeIcon = (userType: string) => {
    switch (userType) {
      case 'admin':
        return <AdminIcon sx={{ fontSize: 18, color: '#A78BFA' }} />;
      case 'system':
        return <SystemIcon sx={{ fontSize: 18, color: '#60A5FA' }} />;
      default:
        return <PersonIcon sx={{ fontSize: 18, color: '#10B981' }} />;
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
    <Paper
      sx={{
        p: 3,
        borderRadius: '20px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'divider',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
      onMouseEnter={onInteraction}
      onScroll={onInteraction}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '10px',
              bgcolor: 'rgba(167, 139, 250, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <PersonIcon sx={{ color: '#A78BFA' }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1.1rem' }}>
              Users ({users.length})
            </Typography>
          </Box>
        </Box>
        <Tooltip title="Export data">
          <IconButton
            size="small"
            onClick={handleExportClick}
            sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)' }}
          >
            <DownloadIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
        <Menu
          anchorEl={exportMenuAnchor}
          open={Boolean(exportMenuAnchor)}
          onClose={handleExportClose}
        >
          <MenuItem onClick={handleExportCSV}>
            <ListItemText>Export as CSV</ListItemText>
          </MenuItem>
          <MenuItem onClick={handleExportJSON}>
            <ListItemText>Export as JSON</ListItemText>
          </MenuItem>
        </Menu>
        <Chip
          label={`${users.filter(u => u.active_session_count > 0).length} active`}
          size="small"
          sx={{
            bgcolor: 'rgba(16, 185, 129, 0.15)',
            color: '#10B981',
            border: '1px solid',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            fontSize: '0.7rem',
            height: 24,
            fontWeight: 600,
          }}
        />
      </Box>

      {/* Filters */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <TextField
          size="small"
          placeholder="Search users..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{
            flex: 1,
            '& .MuiOutlinedInput-root': {
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              fontSize: '0.85rem',
            },
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
              </InputAdornment>
            ),
          }}
        />
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel sx={{ fontSize: '0.85rem' }}>Type</InputLabel>
          <Select
            value={userTypeFilter}
            label="Type"
            onChange={(e) => setUserTypeFilter(e.target.value)}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              fontSize: '0.85rem',
            }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="person">Person</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
            <MenuItem value="system">System</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel sx={{ fontSize: '0.85rem' }}>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              fontSize: '0.85rem',
            }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
            <MenuItem value="has_sessions">Has Sessions</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Users Table */}
      <TableContainer sx={{ flex: 1, overflow: 'auto' }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                User
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Type
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Status
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Sessions
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Last Activity
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    Loading users...
                  </Typography>
                </TableCell>
              </TableRow>
            ) : filteredUsers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No users found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedUsers.map((user) => (
                <TableRow
                  key={user.uuid}
                  hover
                  onClick={() => onUserClick?.(user)}
                  sx={{
                    cursor: onUserClick ? 'pointer' : 'default',
                    '&:hover': {
                      bgcolor: 'rgba(167, 139, 250, 0.05)',
                    },
                  }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getUserTypeIcon(user.user_type)}
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                          {user.full_name}
                        </Typography>
                        {user.nickname && (
                          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                            @{user.nickname}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.user_type}
                      size="small"
                      sx={{
                        bgcolor: `${getUserTypeColor(user.user_type)}15`,
                        color: getUserTypeColor(user.user_type),
                        fontSize: '0.7rem',
                        height: 20,
                        textTransform: 'capitalize',
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {user.is_active ? (
                        <Tooltip title="Active">
                          <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />
                        </Tooltip>
                      ) : (
                        <Tooltip title="Inactive">
                          <CircleIcon sx={{ fontSize: 16, color: '#6B7280' }} />
                        </Tooltip>
                      )}
                      {user.credentials?.is_locked && (
                        <Tooltip title="Account Locked">
                          <LockIcon sx={{ fontSize: 14, color: '#EF4444' }} />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                        {user.active_session_count} active
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        {user.total_session_count} total
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                      {user.last_activity || 'Never'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination Controls */}
      {filteredUsers.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            pt: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Rows per page:
            </Typography>
            <Select
              size="small"
              value={rowsPerPage}
              onChange={handleChangeRowsPerPage}
              sx={{
                fontSize: '0.75rem',
                '& .MuiSelect-select': { py: 0.5, px: 1 },
              }}
            >
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={25}>25</MenuItem>
              <MenuItem value={50}>50</MenuItem>
              <MenuItem value={100}>100</MenuItem>
            </Select>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              {page * rowsPerPage + 1}-{Math.min((page + 1) * rowsPerPage, filteredUsers.length)} of{' '}
              {filteredUsers.length}
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <IconButton
                size="small"
                onClick={() => handleChangePage(page - 1)}
                disabled={page === 0}
                sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)' }}
              >
                <ChevronLeftIcon sx={{ fontSize: 18 }} />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => handleChangePage(page + 1)}
                disabled={page >= Math.ceil(filteredUsers.length / rowsPerPage) - 1}
                sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)' }}
              >
                <ChevronRightIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Box>
          </Box>
        </Box>
      )}
    </Paper>
  );
});

UsersListPanel.displayName = 'UsersListPanel';
