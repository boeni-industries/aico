import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, CircularProgress, Alert, Chip, IconButton, Collapse, Autocomplete, Checkbox, Dialog, DialogTitle, DialogContent, DialogActions, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Search, ChevronLeft, ChevronRight, Eye, Copy, ChevronDown, ChevronUp, Trash2, AlertTriangle } from 'lucide-react';
import { browseLMDBKeys, getLMDBKeyValue, LMDBKeyInfo, LMDBKeyValueResponse, deleteLMDBKeys, findOrphanedLMDBEntries, OrphanedEntry } from '../../api/operations';
import { fetchUsers, UserWithSessions } from '../../api/usersSessions';

interface LMDBBrowserProps {
  databaseName: string;
  color: string;
}

export const LMDBBrowser: React.FC<LMDBBrowserProps> = ({ databaseName, color }) => {
  const [keyPrefix, setKeyPrefix] = useState('');
  const [userId, setUserId] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserWithSessions | null>(null);
  const [users, setUsers] = useState<UserWithSessions[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [keys, setKeys] = useState<LMDBKeyInfo[]>([]);
  const [filteredKeys, setFilteredKeys] = useState<LMDBKeyInfo[]>([]);
  const [contentFilter, setContentFilter] = useState('');
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<LMDBKeyValueResponse | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [orphanedEntries, setOrphanedEntries] = useState<OrphanedEntry[]>([]);
  const [orphanedDialogOpen, setOrphanedDialogOpen] = useState(false);
  const [loadingOrphans, setLoadingOrphans] = useState(false);
  const [pageSize, setPageSize] = useState(10);

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    // Filter keys based on content filter
    if (!contentFilter.trim()) {
      setFilteredKeys(keys);
    } else {
      const lowerFilter = contentFilter.toLowerCase();
      const filtered = keys.filter(keyInfo => {
        // Search in key, value preview, timestamp, and full content if loaded
        const searchableContent = [
          keyInfo.key,
          keyInfo.value_preview,
          keyInfo.timestamp || '',
          (keyInfo as any)._fullContent || '', // Include full content if expanded
        ].join(' ').toLowerCase();
        
        return searchableContent.includes(lowerFilter);
      });
      setFilteredKeys(filtered);
    }
  }, [keys, contentFilter]);

  const loadUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await fetchUsers();
      setUsers(response.users);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoadingUsers(false);
    }
  };


  const handleSearch = async (newPage: number = 0) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await browseLMDBKeys({
        database_name: databaseName,
        key_prefix: keyPrefix || undefined,
        user_id: userId || undefined,
        limit: pageSize,
        offset: newPage * pageSize,
      });

      setKeys(response.keys);
      setTotalCount(response.total_count);
      setHasMore(response.has_more);
      setPage(newPage);
    } catch (err: any) {
      setError(err.message || 'Failed to browse LMDB keys');
    } finally {
      setLoading(false);
    }
  };

  const handleViewKey = async (key: string) => {
    // Toggle expansion
    if (expandedKey === key) {
      setExpandedKey(null);
      setSelectedKey(null);
      return;
    }

    try {
      setLoadingKey(key);
      const response = await getLMDBKeyValue(databaseName, key);
      setSelectedKey(response);
      setExpandedKey(key);
      
      // Update the key info with full content for filtering
      setKeys(prevKeys => 
        prevKeys.map(k => 
          k.key === key 
            ? { ...k, _fullContent: JSON.stringify(response.value) + JSON.stringify(response.metadata || {}) }
            : k
        )
      );
    } catch (err: any) {
      setError(err.message || 'Failed to load key value');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleCopyValue = (value: string) => {
    navigator.clipboard.writeText(value);
  };

  const handleDelete = async () => {
    if (selectedKeys.size === 0) return;

    if (!window.confirm(`Delete ${selectedKeys.size} key(s)? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(true);
      setError(null);
      
      await deleteLMDBKeys({
        database_name: databaseName,
        keys: Array.from(selectedKeys),
      });
      
      setKeys(keys => keys.filter(k => !selectedKeys.has(k.key)));
      setSelectedKeys(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete keys');
    } finally {
      setDeleting(false);
    }
  };

  const handleFindOrphans = async () => {
    try {
      setLoadingOrphans(true);
      setError(null);
      
      const response = await findOrphanedLMDBEntries(databaseName);
      setOrphanedEntries(response.orphaned_entries);
      setOrphanedDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to find orphaned entries');
    } finally {
      setLoadingOrphans(false);
    }
  };

  const handleDeleteOrphans = async () => {
    if (orphanedEntries.length === 0) return;

    if (!window.confirm(`Delete ${orphanedEntries.length} orphaned entries? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(true);
      setError(null);
      
      await deleteLMDBKeys({
        database_name: databaseName,
        keys: orphanedEntries.map(e => e.key),
      });
      
      setKeys(keys => keys.filter(k => !orphanedEntries.some(e => e.key === k.key)));
      setOrphanedDialogOpen(false);
      setOrphanedEntries([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete orphaned entries');
    } finally {
      setDeleting(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <Box>
      {/* Filters */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block', color }}>
          Browse LMDB Keys
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1.5, display: 'block', fontStyle: 'italic' }}>
          LMDB stores working memory as key-value pairs. Leave filters empty to browse all keys, or filter by:
          <br />• <strong>Key prefix</strong>: Common prefixes include "conv:" (conversations), "msg:" (messages), "session:" (sessions)
          <br />• <strong>User</strong>: Filter by specific user
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <TextField
            size="small"
            placeholder="Key prefix (optional, e.g., 'conv:', 'msg:')..."
            value={keyPrefix}
            onChange={(e) => setKeyPrefix(e.target.value)}
            sx={{
              flex: 1,
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0, 0, 0, 0.3)',
                '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
              },
            }}
          />
          <Autocomplete
            size="small"
            options={users}
            getOptionLabel={(option) => {
              const name = option.full_name || option.nickname || 'Unknown';
              return `${name} (${option.uuid})`;
            }}
            renderOption={(props, option) => {
              const name = option.full_name || option.nickname || 'Unknown';
              return (
                <li {...props} key={option.uuid}>
                  <Box component="span">
                    {name}{' '}
                    <Box component="span" sx={{ fontSize: '0.75em', opacity: 0.6 }}>
                      ({option.uuid})
                    </Box>
                  </Box>
                </li>
              );
            }}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => {
                const name = option.full_name || option.nickname || 'Unknown';
                return (
                  <Chip
                    {...getTagProps({ index })}
                    key={option.uuid}
                    label={name}
                    size="small"
                    sx={{
                      '& .MuiChip-label': {
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5,
                      },
                    }}
                  />
                );
              })
            }
            value={selectedUser}
            onChange={(_, newValue) => {
              setSelectedUser(newValue);
              setUserId(newValue?.uuid || '');
            }}
            loading={loadingUsers}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="User (optional)..."
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'rgba(0, 0, 0, 0.3)',
                    '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
                  },
                }}
              />
            )}
            sx={{ flex: 1 }}
          />
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            size="small"
            startIcon={loading ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : <Search size={16} />}
            onClick={() => handleSearch(0)}
            disabled={loading}
            sx={{
              textTransform: 'none',
              bgcolor: color,
              '&:hover': { bgcolor: color, opacity: 0.9 },
            }}
          >
            Browse
          </Button>
          <Button
            variant="contained"
            size="small"
            startIcon={loadingOrphans ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : <AlertTriangle size={16} />}
            onClick={handleFindOrphans}
            disabled={loadingOrphans}
            sx={{
              textTransform: 'none',
              bgcolor: '#f59e0b',
              '&:hover': { bgcolor: '#f59e0b', opacity: 0.9 },
            }}
          >
            Find Orphans
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={() => {
              setKeyPrefix('');
              setUserId('');
              setSelectedUser(null);
              setKeys([]);
              setSelectedKey(null);
              setSelectedKeys(new Set());
            }}
            sx={{
              textTransform: 'none',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: 'rgba(255, 255, 255, 0.8)',
            }}
          >
            Clear
          </Button>
        </Box>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: '0.75rem' }}>
          {error}
        </Alert>
      )}

      {/* Results */}
      {keys.length > 0 && (
        <Box>
          {/* Content Filter */}
          <Box sx={{ mb: 2 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Filter results by content (searches all fields including expanded content)..."
              value={contentFilter}
              onChange={(e) => setContentFilter(e.target.value)}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'rgba(0, 0, 0, 0.3)',
                  '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
                },
              }}
            />
            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', mt: 0.5, display: 'block', fontStyle: 'italic' }}>
              💡 Tip: Expand entries to include their full content in the search
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="caption" sx={{ fontWeight: 600, color }}>
                Results: {filteredKeys.length > 0 ? `${page * pageSize + 1}-${Math.min(page * pageSize + filteredKeys.length, totalCount)} of ${contentFilter ? filteredKeys.length : totalCount}` : '0'} keys
              </Typography>
              {selectedKeys.size > 0 && (
                <Button
                  variant="contained"
                  size="small"
                  startIcon={deleting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : <Trash2 size={14} />}
                  onClick={handleDelete}
                  disabled={deleting}
                  sx={{
                    textTransform: 'none',
                    bgcolor: '#ef4444',
                    fontSize: '0.7rem',
                    py: 0.5,
                    '&:hover': { bgcolor: '#ef4444', opacity: 0.9 },
                  }}
                >
                  Delete ({selectedKeys.size})
                </Button>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
              <Select
                size="small"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(e.target.value as number);
                  setPage(0);
                }}
                sx={{
                  fontSize: '0.75rem',
                  height: '28px',
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(255, 255, 255, 0.3)',
                  },
                }}
              >
                <MenuItem value={10}>10 / page</MenuItem>
                <MenuItem value={25}>25 / page</MenuItem>
                <MenuItem value={50}>50 / page</MenuItem>
                <MenuItem value={100}>100 / page</MenuItem>
              </Select>
              <IconButton
                size="small"
                onClick={() => handleSearch(page - 1)}
                disabled={page === 0 || loading}
                sx={{ color }}
              >
                <ChevronLeft size={18} />
              </IconButton>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                Page {page + 1}
              </Typography>
              <IconButton
                size="small"
                onClick={() => handleSearch(page + 1)}
                disabled={!hasMore || loading}
                sx={{ color }}
              >
                <ChevronRight size={18} />
              </IconButton>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {filteredKeys.map((keyInfo) => (
              <Box
                key={keyInfo.key}
                sx={{
                  borderRadius: '8px',
                  bgcolor: `${color}08`,
                  border: '1px solid',
                  borderColor: expandedKey === keyInfo.key ? `${color}40` : `${color}20`,
                  transition: 'all 0.2s',
                }}
              >
                <Box
                  sx={{
                    p: 1.5,
                    display: 'flex',
                    gap: 1,
                    cursor: 'pointer',
                    '&:hover': {
                      bgcolor: `${color}12`,
                    },
                  }}
                  onClick={() => handleViewKey(keyInfo.key)}
                >
                  <Checkbox
                    checked={selectedKeys.has(keyInfo.key)}
                    onChange={(e) => {
                      e.stopPropagation();
                      const newSelected = new Set(selectedKeys);
                      if (e.target.checked) {
                        newSelected.add(keyInfo.key);
                      } else {
                        newSelected.delete(keyInfo.key);
                      }
                      setSelectedKeys(newSelected);
                    }}
                    size="small"
                    sx={{ 
                      color: color,
                      '&.Mui-checked': { color },
                      p: 0,
                    }}
                  />
                  <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 0.5 }}>
                    <Box sx={{ flex: 1, mr: 1 }}>
                      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', display: 'block', mb: 0.3 }}>
                        Key:
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-all' }}>
                        {keyInfo.key}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', flexShrink: 0 }}>
                      <Chip
                        label={formatBytes(keyInfo.size_bytes)}
                        size="small"
                        sx={{
                          bgcolor: `${color}15`,
                          color,
                          fontSize: '0.65rem',
                          height: 20,
                          fontWeight: 600,
                        }}
                      />
                      <IconButton
                        size="small"
                        disabled={loadingKey === keyInfo.key}
                        sx={{ color }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewKey(keyInfo.key);
                        }}
                      >
                        {loadingKey === keyInfo.key ? (
                          <CircularProgress size={14} />
                        ) : expandedKey === keyInfo.key ? (
                          <ChevronUp size={14} />
                        ) : (
                          <ChevronDown size={14} />
                        )}
                      </IconButton>
                    </Box>
                  </Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block' }}>
                    {keyInfo.value_preview}
                  </Typography>
                  {keyInfo.timestamp && (
                    <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', display: 'block', mt: 0.5 }}>
                      {new Date(keyInfo.timestamp).toLocaleString()}
                    </Typography>
                  )}
                  </Box>
                </Box>

                {/* Expanded Content */}
                <Collapse in={expandedKey === keyInfo.key && selectedKey?.key === keyInfo.key}>
                  {selectedKey?.key === keyInfo.key && (
                    <Box
                      sx={{
                        p: 2,
                        pt: 0,
                        borderTop: '1px solid',
                        borderColor: `${color}20`,
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color }}>
                          Full Value
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => handleCopyValue(JSON.stringify(selectedKey.value, null, 2))}
                          sx={{ color }}
                        >
                          <Copy size={14} />
                        </IconButton>
                      </Box>
                      <Box
                        sx={{
                          p: 1.5,
                          borderRadius: '4px',
                          bgcolor: 'rgba(0, 0, 0, 0.3)',
                          maxHeight: '400px',
                          overflow: 'auto',
                        }}
                      >
                        <pre style={{ margin: 0, fontSize: '0.7rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {JSON.stringify(selectedKey.value, null, 2)}
                        </pre>
                      </Box>
                      {selectedKey.metadata && Object.keys(selectedKey.metadata).length > 0 && (
                        <>
                          <Typography variant="caption" sx={{ fontWeight: 600, color, display: 'block', mt: 2, mb: 1 }}>
                            Metadata
                          </Typography>
                          <Box
                            sx={{
                              p: 1.5,
                              borderRadius: '4px',
                              bgcolor: 'rgba(0, 0, 0, 0.3)',
                            }}
                          >
                            <pre style={{ margin: 0, fontSize: '0.7rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                              {JSON.stringify(selectedKey.metadata, null, 2)}
                            </pre>
                          </Box>
                        </>
                      )}
                    </Box>
                  )}
                </Collapse>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Orphaned Entries Dialog - Award-Winning Design */}
      <Dialog
        open={orphanedDialogOpen}
        onClose={() => setOrphanedDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            background: 'linear-gradient(145deg, rgba(20, 20, 25, 0.98) 0%, rgba(30, 30, 40, 0.95) 100%)',
            backdropFilter: 'blur(40px) saturate(180%)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '20px',
            boxShadow: '0 20px 60px -10px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05) inset',
            overflow: 'hidden',
          }
        }}
        TransitionProps={{
          timeout: 400,
        }}
      >
        <DialogTitle sx={{ 
          background: orphanedEntries.length === 0 
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%)'
            : 'linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(245, 158, 11, 0.05) 100%)',
          borderBottom: orphanedEntries.length === 0
            ? '1px solid rgba(16, 185, 129, 0.2)'
            : '1px solid rgba(251, 191, 36, 0.2)',
          display: 'flex', 
          alignItems: 'center', 
          gap: 2,
          py: 3,
          px: 3,
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: orphanedEntries.length === 0
              ? 'linear-gradient(90deg, transparent, rgba(16, 185, 129, 0.5), transparent)'
              : 'linear-gradient(90deg, transparent, rgba(251, 191, 36, 0.5), transparent)',
          }
        }}>
          <Box sx={{ 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 48,
            height: 48,
            borderRadius: '12px',
            background: orphanedEntries.length === 0
              ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.1) 100%)'
              : 'linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(245, 158, 11, 0.1) 100%)',
            border: orphanedEntries.length === 0
              ? '1px solid rgba(16, 185, 129, 0.3)'
              : '1px solid rgba(251, 191, 36, 0.3)',
            boxShadow: orphanedEntries.length === 0
              ? '0 4px 12px rgba(16, 185, 129, 0.2)'
              : '0 4px 12px rgba(251, 191, 36, 0.2)',
          }}>
            {orphanedEntries.length === 0 ? (
              <Box sx={{ fontSize: '28px' }}>✓</Box>
            ) : (
              <AlertTriangle size={24} color="#fbbf24" strokeWidth={2.5} />
            )}
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" sx={{ 
              fontSize: '1.25rem', 
              fontWeight: 700,
              letterSpacing: '-0.02em',
              mb: 0.5,
              background: orphanedEntries.length === 0
                ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                : 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              {orphanedEntries.length === 0 ? 'Database Clean' : 'Orphaned Entries Detected'}
            </Typography>
            <Typography variant="caption" sx={{ 
              color: 'rgba(255, 255, 255, 0.6)',
              fontSize: '0.8rem',
              fontWeight: 500,
            }}>
              {orphanedEntries.length === 0 
                ? 'All entries reference valid users'
                : `${orphanedEntries.length} ${orphanedEntries.length === 1 ? 'entry' : 'entries'} from deleted users`
              }
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent sx={{ p: 3, pt: 3 }}>
          {orphanedEntries.length === 0 ? (
            <Box sx={{ 
              textAlign: 'center', 
              py: 6,
              px: 3,
            }}>
              <Box sx={{ 
                fontSize: '64px',
                mb: 2,
                opacity: 0.9,
                filter: 'drop-shadow(0 4px 12px rgba(16, 185, 129, 0.3))',
              }}>
                ✨
              </Box>
              <Typography variant="h6" sx={{ 
                color: 'rgba(255, 255, 255, 0.95)', 
                mb: 1.5,
                fontWeight: 600,
                fontSize: '1.1rem',
              }}>
                Perfect! No Cleanup Needed
              </Typography>
              <Typography variant="body2" sx={{ 
                color: 'rgba(255, 255, 255, 0.5)',
                fontSize: '0.9rem',
                lineHeight: 1.6,
                maxWidth: '400px',
                mx: 'auto',
              }}>
                All LMDB entries reference valid users in the system. Your database is clean and optimized.
              </Typography>
            </Box>
          ) : (
            <>
              <Box sx={{ 
                mb: 3,
                p: 2.5,
                borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(245, 158, 11, 0.04) 100%)',
                border: '1px solid rgba(251, 191, 36, 0.15)',
              }}>
                <Typography variant="body2" sx={{ 
                  color: 'rgba(255, 255, 255, 0.8)',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                }}>
                  Found <Box component="span" sx={{ 
                    fontWeight: 700,
                    color: '#fbbf24',
                    fontSize: '1rem',
                  }}>{orphanedEntries.length}</Box> orphaned {orphanedEntries.length === 1 ? 'entry' : 'entries'} referencing deleted users. These can be safely removed to optimize your database.
                </Typography>
              </Box>
              <Box sx={{ 
                maxHeight: '420px', 
                overflow: 'auto',
                pr: 1,
                '&::-webkit-scrollbar': {
                  width: '8px',
                },
                '&::-webkit-scrollbar-track': {
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: '4px',
                },
                '&::-webkit-scrollbar-thumb': {
                  background: 'rgba(251, 191, 36, 0.3)',
                  borderRadius: '4px',
                  '&:hover': {
                    background: 'rgba(251, 191, 36, 0.5)',
                  }
                },
              }}>
                {orphanedEntries.map((entry, index) => (
                  <Box
                    key={entry.key}
                    sx={{
                      p: 2.5,
                      mb: 1.5,
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.06) 0%, rgba(245, 158, 11, 0.03) 100%)',
                      border: '1px solid rgba(251, 191, 36, 0.15)',
                      backdropFilter: 'blur(10px)',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      position: 'relative',
                      overflow: 'hidden',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '3px',
                        height: '100%',
                        background: 'linear-gradient(180deg, #fbbf24 0%, #f59e0b 100%)',
                        opacity: 0,
                        transition: 'opacity 0.3s',
                      },
                      '&:hover': {
                        background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.12) 0%, rgba(245, 158, 11, 0.06) 100%)',
                        borderColor: 'rgba(251, 191, 36, 0.3)',
                        transform: 'translateX(4px)',
                        boxShadow: '0 8px 24px rgba(251, 191, 36, 0.15)',
                        '&::before': {
                          opacity: 1,
                        }
                      }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                      <Chip 
                        label={`#${index + 1}`}
                        size="small"
                        sx={{
                          height: '20px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(245, 158, 11, 0.15) 100%)',
                          color: '#fbbf24',
                          border: '1px solid rgba(251, 191, 36, 0.3)',
                        }}
                      />
                      <Typography variant="caption" sx={{ 
                        color: 'rgba(255, 255, 255, 0.4)',
                        fontSize: '0.7rem',
                        fontWeight: 500,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}>
                        Orphaned Entry
                      </Typography>
                    </Box>
                    <Box sx={{ mb: 1.5 }}>
                      <Typography variant="caption" sx={{ 
                        color: 'rgba(255, 255, 255, 0.5)',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        display: 'block',
                        mb: 0.5,
                      }}>
                        Key
                      </Typography>
                      <Typography variant="body2" sx={{ 
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                        color: 'rgba(255, 255, 255, 0.9)',
                        wordBreak: 'break-all',
                        lineHeight: 1.5,
                        background: 'rgba(0, 0, 0, 0.2)',
                        p: 1,
                        borderRadius: '6px',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                      }}>
                        {entry.key}
                      </Typography>
                    </Box>
                    <Box sx={{ mb: 1.5 }}>
                      <Typography variant="caption" sx={{ 
                        color: 'rgba(255, 255, 255, 0.5)',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        display: 'block',
                        mb: 0.5,
                      }}>
                        Deleted User ID
                      </Typography>
                      <Typography variant="body2" sx={{ 
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                        color: '#fbbf24',
                        fontWeight: 600,
                      }}>
                        {entry.user_id}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" sx={{ 
                        color: 'rgba(255, 255, 255, 0.5)',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        display: 'block',
                        mb: 0.5,
                      }}>
                        Preview
                      </Typography>
                      <Typography variant="caption" sx={{ 
                        fontSize: '0.75rem',
                        color: 'rgba(255, 255, 255, 0.6)',
                        lineHeight: 1.5,
                        display: 'block',
                      }}>
                        {entry.preview}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ 
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.3) 100%)',
          p: 3,
          gap: 1.5,
        }}>
          <Button 
            onClick={() => setOrphanedDialogOpen(false)}
            sx={{ 
              color: 'rgba(255, 255, 255, 0.7)',
              fontWeight: 600,
              fontSize: '0.9rem',
              px: 3,
              py: 1,
              borderRadius: '10px',
              textTransform: 'none',
              transition: 'all 0.2s',
              '&:hover': { 
                bgcolor: 'rgba(255, 255, 255, 0.08)',
                color: 'rgba(255, 255, 255, 0.9)',
              }
            }}
          >
            {orphanedEntries.length === 0 ? 'Close' : 'Cancel'}
          </Button>
          {orphanedEntries.length > 0 && (
            <Button
              onClick={handleDeleteOrphans}
              variant="contained"
              disabled={deleting}
              startIcon={deleting ? <CircularProgress size={18} sx={{ color: '#fff' }} /> : <Trash2 size={18} />}
              sx={{
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.9rem',
                px: 3,
                py: 1,
                borderRadius: '10px',
                textTransform: 'none',
                boxShadow: '0 4px 12px rgba(239, 68, 68, 0.4)',
                transition: 'all 0.2s',
                '&:hover': { 
                  background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
                  boxShadow: '0 6px 20px rgba(239, 68, 68, 0.5)',
                  transform: 'translateY(-1px)',
                },
                '&:active': {
                  transform: 'translateY(0)',
                },
                '&:disabled': { 
                  background: 'rgba(239, 68, 68, 0.3)',
                  boxShadow: 'none',
                }
              }}
            >
              Delete All Orphaned Entries
            </Button>
          )}
        </DialogActions>
      </Dialog>

    </Box>
  );
};
