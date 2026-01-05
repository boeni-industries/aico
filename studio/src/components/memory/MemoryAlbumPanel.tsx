import React, { useState } from 'react';
import { Box, Typography, Paper, Chip, TextField, InputAdornment, IconButton, Dialog, DialogContent, DialogTitle, Divider, Select, MenuItem, FormControl, InputLabel, Button, Checkbox, DialogActions } from '@mui/material';
import { StyledTooltip } from '../common/StyledTooltip';
import { Search as SearchIcon, Filter as FilterIcon, X as CloseIcon, Calendar as CalendarIcon, Tag as TagIcon, Info as InfoIcon, MessageCircle as ChatIcon, Trash2 as DeleteIcon, Download as DownloadIcon, BarChart3 as AnalyticsIcon } from 'lucide-react';

interface Conversation {
  id: string;
  title: string;
  full_content?: string;
  timestamp: string;
  person: string;
  user_uuid?: string;
  user_full_name?: string;
  user_nickname?: string | null;
  sentiment: 'positive' | 'neutral' | 'negative';
  messageCount: number;
  tags: string[];
  contentType?: 'conversation' | 'message';
  conversationTitle?: string;
  turnRange?: string;
  emotionalTone?: string;
}

interface MemoryAlbumPanelProps {
  conversations: Conversation[];
  onConversationClick?: (conversation: Conversation) => void;
  onDelete?: (ids: string[]) => Promise<void>;
}

export const MemoryAlbumPanel: React.FC<MemoryAlbumPanelProps> = ({
  conversations,
  onConversationClick,
  onDelete,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMemory, setSelectedMemory] = useState<Conversation | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [contentTypeFilter, setContentTypeFilter] = useState<string>('all');
  const [selectedMemories, setSelectedMemories] = useState<Set<string>>(new Set());
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [memoryToDelete, setMemoryToDelete] = useState<string | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [deletedIds] = useState<Set<string>>(new Set());

  // Get unique users from conversations (by user_uuid)
  const uniqueUserMap = new Map<string, { uuid: string; display: string; full_name: string }>();
  conversations.forEach(c => {
    if (c.user_uuid && !uniqueUserMap.has(c.user_uuid)) {
      uniqueUserMap.set(c.user_uuid, {
        uuid: c.user_uuid,
        display: c.person,
        full_name: c.user_full_name || c.person,
      });
    }
  });
  const users = Array.from(uniqueUserMap.values());

  // Filter logic
  const filteredConversations = conversations.filter(conv => {
    const notDeleted = !deletedIds.has(conv.id);
    const matchesSearch = conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesUser = selectedUser === 'all' || conv.user_uuid === selectedUser;
    const matchesType = contentTypeFilter === 'all' || conv.contentType === contentTypeFilter;
    return notDeleted && matchesSearch && matchesUser && matchesType;
  });

  // Analytics calculations (exclude deleted)
  const activeConversations = conversations.filter(c => !deletedIds.has(c.id));
  const totalMemories = activeConversations.length;
  const conversationMemories = activeConversations.filter(c => c.contentType === 'conversation').length;
  const messageMemories = activeConversations.filter(c => c.contentType === 'message').length;
  const memoriesPerUser = users.reduce((acc, user) => {
    acc[user.full_name] = activeConversations.filter(c => c.user_uuid === user.uuid).length;
    return acc;
  }, {} as Record<string, number>);

  // Bulk operations
  const handleSelectAll = () => {
    if (selectedMemories.size === filteredConversations.length) {
      setSelectedMemories(new Set());
    } else {
      setSelectedMemories(new Set(filteredConversations.map(c => c.id)));
    }
  };

  const handleToggleSelect = (id: string) => {
    const newSelected = new Set(selectedMemories);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedMemories(newSelected);
  };

  const confirmDelete = async () => {
    if (memoryToDelete && onDelete) {
      try {
        console.log('🗑️ Deleting memory:', memoryToDelete);
        await onDelete([memoryToDelete]);
        console.log('✅ Memory deleted successfully');
        setDeleteConfirmOpen(false);
        setMemoryToDelete(null);
      } catch (error) {
        console.error('❌ Failed to delete memory:', error);
        alert('Failed to delete memory. Please try again.');
      }
    }
  };

  const handleBulkDelete = async () => {
    if (selectedMemories.size > 0 && onDelete) {
      const idsToDelete = Array.from(selectedMemories);
      
      try {
        console.log('🗑️ Bulk delete operation:', idsToDelete);
        console.log(`🗑️ Deleting ${idsToDelete.length} memories...`);
        await onDelete(idsToDelete);
        console.log('✅ Memories deleted successfully');
        setSelectedMemories(new Set());
      } catch (error) {
        console.error('❌ Failed to delete memories:', error);
        alert(`Failed to delete ${idsToDelete.length} memories. Please try again.`);
      }
    }
  };

  const handleExport = (format: 'json' | 'csv') => {
    const dataToExport = selectedMemories.size > 0
      ? filteredConversations.filter(c => selectedMemories.has(c.id))
      : filteredConversations;

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories-${new Date().toISOString()}.json`;
      a.click();
    } else {
      const csv = [
        ['ID', 'Type', 'Content', 'Tags', 'Created', 'User'].join(','),
        ...dataToExport.map(c => [
          c.id,
          c.contentType || 'message',
          `"${c.title.replace(/"/g, '""')}"`,
          `"${c.tags.join(', ')}"`,
          c.timestamp,
          c.person
        ].join(','))
      ].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories-${new Date().toISOString()}.csv`;
      a.click();
    }
  };

  return (
    <Box>
      {/* Header with Search */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2, gap: 2 }}>
          <Box>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                fontSize: '1.25rem',
                color: 'text.primary',
                mb: 0.5,
              }}
            >
              Memory Album
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
              {filteredConversations.length} of {conversations.length} memories
              {selectedMemories.size > 0 && ` • ${selectedMemories.size} selected`}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <StyledTooltip title="Toggle analytics dashboard showing memory statistics, user breakdowns, and system health metrics" arrow>
              <IconButton
                size="small"
                onClick={() => setShowAnalytics(!showAnalytics)}
                sx={{
                  bgcolor: showAnalytics ? 'rgba(184, 161, 234, 0.2)' : 'rgba(255,255,255,0.05)',
                  '&:hover': { bgcolor: 'rgba(184, 161, 234, 0.3)' },
                }}
              >
                <AnalyticsIcon sx={{ fontSize: 20, color: '#B8A1EA' }} />
              </IconButton>
            </StyledTooltip>
            <StyledTooltip title="Toggle advanced filters for user selection and content type filtering" arrow>
              <IconButton
                size="small"
                onClick={() => setShowFilters(!showFilters)}
                sx={{
                  bgcolor: showFilters ? 'rgba(184, 161, 234, 0.2)' : 'rgba(255,255,255,0.05)',
                  '&:hover': { bgcolor: 'rgba(184, 161, 234, 0.3)' },
                }}
              >
                <FilterIcon sx={{ fontSize: 20, color: '#B8A1EA' }} />
              </IconButton>
            </StyledTooltip>
            <StyledTooltip title="Export filtered memories to JSON format. Select specific memories for partial export or export all visible results." arrow>
              <Button
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => handleExport('json')}
                sx={{
                  bgcolor: 'rgba(141, 214, 184, 0.15)',
                  color: '#8DD6B8',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  '&:hover': { bgcolor: 'rgba(141, 214, 184, 0.25)' },
                }}
              >
                Export
              </Button>
            </StyledTooltip>
          </Box>
        </Box>

        {/* Analytics Panel */}
        {showAnalytics && (
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              mb: 2,
              background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.08) 0%, rgba(141, 214, 184, 0.08) 100%)',
              backdropFilter: 'blur(24px)',
              border: '1.5px solid rgba(255,255,255,0.12)',
              borderRadius: '16px',
            }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 2, color: 'text.primary' }}>
              Analytics Overview
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 2 }}>
              <Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                  TOTAL MEMORIES
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#B8A1EA' }}>
                  {totalMemories}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                  CONVERSATIONS
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#8DD6B8' }}>
                  {conversationMemories}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                  MESSAGES
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: 'rgba(255,255,255,0.7)' }}>
                  {messageMemories}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                  USERS
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700, color: '#B8A1EA' }}>
                  {users.length}
                </Typography>
              </Box>
            </Box>
            {users.length > 1 && (
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', mb: 1, display: 'block' }}>
                  MEMORIES PER USER
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  {users.map(user => (
                    <Chip
                      key={user.uuid}
                      label={`${user.full_name}: ${memoriesPerUser[user.full_name]}`}
                      size="small"
                      sx={{
                        bgcolor: 'rgba(184, 161, 234, 0.15)',
                        color: '#B8A1EA',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                      }}
                    />
                  ))}
                </Box>
              </Box>
            )}
          </Paper>
        )}

        {/* Filters Panel */}
        {showFilters && (
          <Paper
            elevation={0}
            sx={{
              p: 2,
              mb: 2,
              background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.08) 0%, rgba(141, 214, 184, 0.08) 100%)',
              backdropFilter: 'blur(24px)',
              border: '1.5px solid rgba(255,255,255,0.12)',
              borderRadius: '16px',
            }}
          >
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 2 }}>
              <FormControl size="small" fullWidth>
                <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>User</InputLabel>
                <Select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  label="User"
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.05)',
                    '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.12)' },
                    '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(184, 161, 234, 0.5)' },
                  }}
                >
                  <MenuItem value="all">All Users</MenuItem>
                  {users.map(user => (
                    <MenuItem key={user.uuid} value={user.uuid}>{user.display}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" fullWidth>
                <InputLabel sx={{ color: 'rgba(255,255,255,0.5)' }}>Type</InputLabel>
                <Select
                  value={contentTypeFilter}
                  onChange={(e) => setContentTypeFilter(e.target.value)}
                  label="Type"
                  sx={{
                    bgcolor: 'rgba(255,255,255,0.05)',
                    '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.12)' },
                    '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(184, 161, 234, 0.5)' },
                  }}
                >
                  <MenuItem value="all">All Types</MenuItem>
                  <MenuItem value="conversation">Conversations</MenuItem>
                  <MenuItem value="message">Messages</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Paper>
        )}

        {/* Search Bar - Glassmorphic */}
        <Paper
          elevation={0}
          sx={{
            p: 1.5,
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.08) 0%, rgba(141, 214, 184, 0.08) 100%)',
            backdropFilter: 'blur(24px)',
            border: '1.5px solid rgba(255,255,255,0.12)',
            borderRadius: '16px',
            mb: 2,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }}
        >
          <TextField
            fullWidth
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            variant="standard"
            InputProps={{
              disableUnderline: true,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: 'rgba(255,255,255,0.4)', fontSize: 20 }} />
                </InputAdornment>
              ),
              endAdornment: searchQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchQuery('')}>
                    <CloseIcon sx={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }} />
                  </IconButton>
                </InputAdornment>
              ),
              sx: {
                color: 'text.primary',
                fontSize: '0.95rem',
                '& input::placeholder': {
                  color: 'rgba(255,255,255,0.3)',
                  opacity: 1,
                },
              },
            }}
          />
        </Paper>

        {/* Bulk Operations Toolbar */}
        {selectedMemories.size > 0 && (
          <Paper
            elevation={0}
            sx={{
              p: 1.5,
              mb: 2,
              background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.15) 0%, rgba(141, 214, 184, 0.15) 100%)',
              backdropFilter: 'blur(24px)',
              border: '1.5px solid rgba(184, 161, 234, 0.3)',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
              {selectedMemories.size} selected
            </Typography>
            <StyledTooltip title="Permanently delete all selected memories. This action cannot be undone." arrow>
              <Button
                size="small"
                startIcon={<DeleteIcon />}
                onClick={handleBulkDelete}
                sx={{
                  bgcolor: 'rgba(239, 68, 68, 0.15)',
                  color: '#EF4444',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.25)' },
                }}
              >
                Delete
              </Button>
            </StyledTooltip>
            <StyledTooltip title="Export only the selected memories to JSON format" arrow>
              <Button
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => handleExport('json')}
                sx={{
                  bgcolor: 'rgba(141, 214, 184, 0.15)',
                  color: '#8DD6B8',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  '&:hover': { bgcolor: 'rgba(141, 214, 184, 0.25)' },
                }}
              >
                Export Selected
              </Button>
            </StyledTooltip>
            <Button
              size="small"
              onClick={() => setSelectedMemories(new Set())}
              sx={{
                color: 'rgba(255,255,255,0.5)',
                fontSize: '0.75rem',
              }}
            >
              Clear
            </Button>
          </Paper>
        )}
      </Box>

      {/* Empty State */}
      {conversations.length === 0 ? (
        <Paper
          elevation={0}
          sx={{
            p: 6,
            textAlign: 'center',
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.05) 0%, rgba(141, 214, 184, 0.05) 100%)',
            backdropFilter: 'blur(24px)',
            border: '1.5px dashed rgba(255,255,255,0.15)',
            borderRadius: '24px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }}
        >
          <InfoIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.2)', mb: 2 }} />
          <Typography variant="h6" sx={{ mb: 1, color: 'text.primary', fontWeight: 600 }}>
            No Memories Yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Users can curate memories by clicking "Remember This" on messages
          </Typography>
        </Paper>
      ) : filteredConversations.length === 0 ? (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            textAlign: 'center',
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.05) 0%, rgba(141, 214, 184, 0.05) 100%)',
            backdropFilter: 'blur(24px)',
            border: '1.5px solid rgba(255,255,255,0.12)',
            borderRadius: '20px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }}
        >
          <Typography variant="body2" color="text.secondary">
            No memories match your search
          </Typography>
        </Paper>
      ) : (
        <>
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <StyledTooltip title="Select or deselect all visible memories for bulk operations" arrow>
              <Checkbox
                checked={selectedMemories.size === filteredConversations.length && filteredConversations.length > 0}
                indeterminate={selectedMemories.size > 0 && selectedMemories.size < filteredConversations.length}
                onChange={handleSelectAll}
                sx={{
                  color: 'rgba(184, 161, 234, 0.5)',
                  '&.Mui-checked': { color: '#B8A1EA' },
                  '&.MuiCheckbox-indeterminate': { color: '#B8A1EA' },
                }}
              />
            </StyledTooltip>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>
              Select All
            </Typography>
          </Box>
          <Box 
            sx={{ 
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)',
                lg: 'repeat(4, 1fr)',
              },
              gap: 2,
            }}
          >
          {filteredConversations.map((conversation) => (
            <Paper
              key={conversation.id}
              elevation={0}
              sx={{
                p: 2,
                background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.08) 0%, rgba(141, 214, 184, 0.08) 100%)',
                backdropFilter: 'blur(24px)',
                border: '1.5px solid rgba(255,255,255,0.12)',
                borderRadius: '16px',
                cursor: 'pointer',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '3px',
                  background: 'linear-gradient(90deg, #B8A1EA 0%, #8DD6B8 100%)',
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                },
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  inset: 0,
                  background: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 400 400\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")',
                  opacity: 0.03,
                  pointerEvents: 'none',
                  mixBlendMode: 'overlay',
                },
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 20px 48px rgba(184, 161, 234, 0.25)',
                  border: '1.5px solid rgba(184, 161, 234, 0.5)',
                  background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.12) 0%, rgba(141, 214, 184, 0.12) 100%)',
                  '&::before': {
                    opacity: 1,
                  },
                },
              }}
            >
              {/* Selection Checkbox */}
              <StyledTooltip title="Select this memory for bulk operations (delete, export)" arrow placement="right">
                <Box sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}>
                  <Checkbox
                    checked={selectedMemories.has(conversation.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      handleToggleSelect(conversation.id);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    sx={{
                      color: 'rgba(184, 161, 234, 0.3)',
                      '&.Mui-checked': { color: '#B8A1EA' },
                      padding: 0.5,
                    }}
                  />
                </Box>
              </StyledTooltip>

              {/* Card Content - Clickable */}
              <Box onClick={() => setSelectedMemory(conversation)} sx={{ cursor: 'pointer', pl: 4 }}>
              {/* Type Badge */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Chip
                  icon={conversation.contentType === 'conversation' ? <ChatIcon sx={{ fontSize: 12 }} /> : <InfoIcon sx={{ fontSize: 12 }} />}
                  label={conversation.contentType === 'conversation' ? 'Conversation' : 'Message'}
                  size="small"
                  sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    bgcolor: conversation.contentType === 'conversation' 
                      ? 'rgba(184, 161, 234, 0.15)' 
                      : 'rgba(255,255,255,0.08)',
                    color: conversation.contentType === 'conversation' ? '#B8A1EA' : 'rgba(255,255,255,0.6)',
                    border: '1px solid',
                    borderColor: conversation.contentType === 'conversation'
                      ? 'rgba(184, 161, 234, 0.3)'
                      : 'rgba(255,255,255,0.12)',
                    '& .MuiChip-icon': {
                      color: 'inherit',
                    },
                  }}
                />
                {conversation.turnRange && (
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.625rem' }}>
                    {conversation.turnRange}
                  </Typography>
                )}
              </Box>

              {/* Conversation Title (if exists) */}
              {conversation.conversationTitle && (
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    mb: 0.75,
                    color: '#8DD6B8',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    letterSpacing: '0.02em',
                  }}
                >
                  {conversation.conversationTitle}
                </Typography>
              )}

              {/* Truncated Preview with Gradient Fade */}
              <Box sx={{ position: 'relative', mb: 1.5 }}>
                <Typography
                  variant="body2"
                  sx={{
                    lineHeight: 1.6,
                    color: 'text.primary',
                    fontSize: '0.85rem',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    position: 'relative',
                  }}
                >
                  {conversation.title}
                </Typography>
                {conversation.title.length > 150 && (
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      right: 0,
                      height: '24px',
                      background: 'linear-gradient(to bottom, transparent, rgba(184, 161, 234, 0.08))',
                      pointerEvents: 'none',
                    }}
                  />
                )}
              </Box>

              {/* Metadata Bar */}
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 2, 
                flexWrap: 'wrap',
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <CalendarIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.35)' }} />
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem', fontWeight: 500 }}>
                    {conversation.timestamp}
                  </Typography>
                </Box>
                {/* Tags Inline */}
                {conversation.tags.length > 0 && (
                  <>
                    {conversation.tags.slice(0, 2).map((tag) => (
                      <Chip
                        key={tag}
                        label={tag}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.625rem',
                          fontWeight: 600,
                          bgcolor: 'rgba(139, 92, 246, 0.12)',
                          color: '#B8A1EA',
                          border: '1px solid rgba(139, 92, 246, 0.2)',
                          '& .MuiChip-label': {
                            px: 0.75,
                          },
                        }}
                      />
                    ))}
                    {conversation.tags.length > 2 && (
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.625rem', fontWeight: 500 }}>
                        +{conversation.tags.length - 2}
                      </Typography>
                    )}
                  </>
                )}
                {conversation.title.length > 150 && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 'auto' }}>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.625rem', fontStyle: 'italic' }}>
                      Click to read more
                    </Typography>
                  </Box>
                )}
              </Box>
              </Box>
            </Paper>
          ))}
          </Box>
        </>
      )}

      {/* Memory Detail Modal */}
      <Dialog
        open={Boolean(selectedMemory)}
        onClose={() => setSelectedMemory(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.12) 0%, rgba(141, 214, 184, 0.12) 100%)',
            backdropFilter: 'blur(40px)',
            border: '1.5px solid rgba(255,255,255,0.18)',
            borderRadius: '24px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
            position: 'relative',
            overflow: 'hidden',
            '&::after': {
              content: '""',
              position: 'absolute',
              inset: 0,
              background: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 400 400\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\'/%3E%3C/svg%3E")',
              opacity: 0.04,
              pointerEvents: 'none',
              mixBlendMode: 'overlay',
            },
          },
        }}
      >
        {selectedMemory && (
          <>
            <DialogTitle sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              pb: 2,
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
                Memory Details
              </Typography>
              <IconButton onClick={() => setSelectedMemory(null)} size="small">
                <CloseIcon sx={{ color: 'rgba(255,255,255,0.6)' }} />
              </IconButton>
            </DialogTitle>
            <DialogContent 
              sx={{ 
                pt: 3, 
                maxHeight: '70vh', 
                overflowY: 'auto',
                '&::-webkit-scrollbar': {
                  width: '8px',
                },
                '&::-webkit-scrollbar-track': {
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '4px',
                },
                '&::-webkit-scrollbar-thumb': {
                  background: 'linear-gradient(180deg, rgba(184, 161, 234, 0.4) 0%, rgba(141, 214, 184, 0.4) 100%)',
                  borderRadius: '4px',
                  '&:hover': {
                    background: 'linear-gradient(180deg, rgba(184, 161, 234, 0.6) 0%, rgba(141, 214, 184, 0.6) 100%)',
                  },
                },
              }}
            >
              {/* Premium Content Display */}
              <Box
                sx={{
                  p: 3,
                  mb: 3,
                  background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.05) 0%, rgba(141, 214, 184, 0.05) 100%)',
                  borderRadius: '16px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  position: 'relative',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: 'linear-gradient(90deg, #B8A1EA 0%, #8DD6B8 100%)',
                    borderRadius: '16px 16px 0 0',
                  },
                }}
              >
                <Typography
                  variant="body1"
                  sx={{
                    lineHeight: 1.9,
                    color: 'text.primary',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontSize: '1rem',
                    fontWeight: 400,
                    letterSpacing: '0.01em',
                  }}
                >
                  {selectedMemory.full_content || selectedMemory.title}
                </Typography>
              </Box>

              <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.08)' }} />

              {/* Metadata Section */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                <Box
                  sx={{
                    p: 2,
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <CalendarIcon sx={{ fontSize: 16, color: '#B8A1EA' }} />
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem', fontWeight: 700 }}>
                      Created
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 500, fontSize: '0.9rem' }}>
                    {selectedMemory.timestamp}
                  </Typography>
                </Box>

                {selectedMemory.tags.length > 0 && (
                  <Box
                    sx={{
                      p: 2,
                      background: 'rgba(255,255,255,0.02)',
                      borderRadius: '12px',
                      border: '1px solid rgba(255,255,255,0.06)',
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                      <TagIcon sx={{ fontSize: 16, color: '#8DD6B8' }} />
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.65rem', fontWeight: 700 }}>
                        Tags ({selectedMemory.tags.length})
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      {selectedMemory.tags.map((tag) => (
                        <Chip
                          key={tag}
                          label={tag}
                          size="small"
                          sx={{
                            height: 28,
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(141, 214, 184, 0.15) 100%)',
                            color: '#B8A1EA',
                            border: '1px solid rgba(139, 92, 246, 0.3)',
                            backdropFilter: 'blur(8px)',
                            transition: 'all 0.2s ease',
                            '&:hover': {
                              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.25) 0%, rgba(141, 214, 184, 0.25) 100%)',
                              transform: 'translateY(-1px)',
                            },
                          }}
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </DialogContent>
          </>
        )}
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        PaperProps={{
          sx: {
            background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.12) 0%, rgba(141, 214, 184, 0.12) 100%)',
            backdropFilter: 'blur(40px)',
            border: '1.5px solid rgba(255,255,255,0.18)',
            borderRadius: '20px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          },
        }}
      >
        <DialogTitle sx={{ fontWeight: 700, color: 'text.primary' }}>
          Confirm Delete
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            Are you sure you want to delete this memory? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2, pt: 0 }}>
          <Button
            onClick={() => setDeleteConfirmOpen(false)}
            sx={{ color: 'rgba(255,255,255,0.5)' }}
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDelete}
            variant="contained"
            sx={{
              bgcolor: 'rgba(239, 68, 68, 0.2)',
              color: '#EF4444',
              fontWeight: 600,
              '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.3)' },
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
