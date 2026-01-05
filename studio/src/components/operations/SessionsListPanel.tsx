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
  ListItemText,
} from '@mui/material';
import { Search as SearchIcon, Smartphone as DevicesIcon, CheckCircle as CheckCircleIcon, X as CancelIcon, Monitor as ComputerIcon, Smartphone as PhoneIcon, Monitor as DesktopIcon, ChevronLeft as ChevronLeftIcon, ChevronRight as ChevronRightIcon, Download as DownloadIcon } from 'lucide-react';
import { SessionWithUser } from '../../api/usersSessions';
import { exportSessionsToCSV, exportSessionsToJSON } from '../../utils/exportData';

interface SessionsListPanelProps {
  sessions: SessionWithUser[];
  onSessionClick?: (session: SessionWithUser) => void;
  loading?: boolean;
  onInteraction?: () => void;
}

export const SessionsListPanel: React.FC<SessionsListPanelProps> = React.memo(({
  sessions,
  onSessionClick,
  loading = false,
  onInteraction,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [sessionTypeFilter, setSessionTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);

  // Filter sessions with useMemo to prevent recalculation on every render
  const filteredSessions = useMemo(() => sessions.filter(session => {
    const matchesSearch = 
      session.user_full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.uuid.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (session.user_nickname && session.user_nickname.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesType = sessionTypeFilter === 'all' || session.session_type === sessionTypeFilter;
    const matchesStatus = 
      statusFilter === 'all' ||
      (statusFilter === 'active' && session.is_active) ||
      (statusFilter === 'expired' && !session.is_active);
    
    return matchesSearch && matchesType && matchesStatus;
  }), [sessions, searchQuery, sessionTypeFilter, statusFilter]);

  // Paginated sessions
  const paginatedSessions = useMemo(
    () => filteredSessions.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [filteredSessions, page, rowsPerPage]
  );

  // Reset page when filters change
  React.useEffect(() => {
    setPage(0);
  }, [searchQuery, sessionTypeFilter, statusFilter]);

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
    exportSessionsToCSV(filteredSessions);
    handleExportClose();
  };

  const handleExportJSON = () => {
    exportSessionsToJSON(filteredSessions);
    handleExportClose();
  };

  const getDeviceIcon = (deviceType?: string) => {
    switch (deviceType?.toLowerCase()) {
      case 'mobile':
      case 'phone':
        return <PhoneIcon sx={{ fontSize: 16, color: '#60A5FA' }} />;
      case 'desktop':
      case 'computer':
        return <DesktopIcon sx={{ fontSize: 16, color: '#A78BFA' }} />;
      default:
        return <ComputerIcon sx={{ fontSize: 16, color: '#10B981' }} />;
    }
  };

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
              bgcolor: 'rgba(96, 165, 250, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <DevicesIcon sx={{ color: '#60A5FA' }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1.1rem' }}>
              Sessions ({sessions.length})
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
          label={`${sessions.filter(s => s.is_active).length} active`}
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
          placeholder="Search sessions..."
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
            value={sessionTypeFilter}
            label="Type"
            onChange={(e) => setSessionTypeFilter(e.target.value)}
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              fontSize: '0.85rem',
            }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="unified">Unified</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 120 }}>
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
            <MenuItem value="expired">Expired</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Sessions Table */}
      <TableContainer sx={{ flex: 1, overflow: 'auto' }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                User
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Device
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Type
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Status
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Time Remaining
              </TableCell>
              <TableCell sx={{ bgcolor: 'rgba(255, 255, 255, 0.02)', fontSize: '0.75rem', fontWeight: 600 }}>
                Created
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    Loading sessions...
                  </Typography>
                </TableCell>
              </TableRow>
            ) : filteredSessions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    No sessions found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedSessions.map((session) => (
                <TableRow
                  key={session.uuid}
                  hover
                  onClick={() => onSessionClick?.(session)}
                  sx={{
                    cursor: onSessionClick ? 'pointer' : 'default',
                    '&:hover': {
                      bgcolor: 'rgba(96, 165, 250, 0.05)',
                    },
                  }}
                >
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                        {session.user_full_name}
                      </Typography>
                      {session.user_nickname && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                          @{session.user_nickname}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {getDeviceIcon(session.device_type)}
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        {session.device_name || session.device_type || 'Unknown'}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Chip
                      label={session.session_type}
                      size="small"
                      sx={{
                        bgcolor: `${getSessionTypeColor(session.session_type)}15`,
                        color: getSessionTypeColor(session.session_type),
                        fontSize: '0.7rem',
                        height: 20,
                        textTransform: 'capitalize',
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {session.is_active ? (
                        <Tooltip title="Active">
                          <CheckCircleIcon sx={{ fontSize: 16, color: '#10B981' }} />
                        </Tooltip>
                      ) : (
                        <Tooltip title="Expired">
                          <CancelIcon sx={{ fontSize: 16, color: '#EF4444' }} />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.8rem',
                        color: session.is_active ? 'text.primary' : 'text.secondary',
                      }}
                    >
                      {session.time_remaining || 'Expired'}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                      {new Date(session.created_at).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination Controls */}
      {filteredSessions.length > 0 && (
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
              {page * rowsPerPage + 1}-{Math.min((page + 1) * rowsPerPage, filteredSessions.length)} of{' '}
              {filteredSessions.length}
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
                disabled={page >= Math.ceil(filteredSessions.length / rowsPerPage) - 1}
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

SessionsListPanel.displayName = 'SessionsListPanel';
