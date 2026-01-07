import React, { useState } from 'react';
import { Box, Typography, TextField, Button, CircularProgress, Alert, Chip, IconButton, Collapse } from '@mui/material';
import { Search, ChevronLeft, ChevronRight, Eye, Copy } from 'lucide-react';
import { browseLMDBKeys, getLMDBKeyValue, LMDBKeyInfo, LMDBKeyValueResponse } from '../../api/operations';

interface LMDBBrowserProps {
  databaseName: string;
  color: string;
}

export const LMDBBrowser: React.FC<LMDBBrowserProps> = ({ databaseName, color }) => {
  const [keyPrefix, setKeyPrefix] = useState('');
  const [userId, setUserId] = useState('');
  const [keys, setKeys] = useState<LMDBKeyInfo[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKey, setSelectedKey] = useState<LMDBKeyValueResponse | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const pageSize = 50;

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
    try {
      setLoadingKey(key);
      const response = await getLMDBKeyValue(databaseName, key);
      setSelectedKey(response);
    } catch (err: any) {
      setError(err.message || 'Failed to load key value');
    } finally {
      setLoadingKey(null);
    }
  };

  const handleCopyValue = (value: string) => {
    navigator.clipboard.writeText(value);
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
          Filter Keys
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <TextField
            size="small"
            placeholder="Key prefix..."
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
          <TextField
            size="small"
            placeholder="User ID..."
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            sx={{
              flex: 1,
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0, 0, 0, 0.3)',
                '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
              },
            }}
          />
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
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
            Search
          </Button>
          <Button
            variant="outlined"
            size="small"
            onClick={() => {
              setKeyPrefix('');
              setUserId('');
              setKeys([]);
              setSelectedKey(null);
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
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, color }}>
              Results: {totalCount} keys
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
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
            {keys.map((keyInfo) => (
              <Box
                key={keyInfo.key}
                sx={{
                  p: 1.5,
                  borderRadius: '8px',
                  bgcolor: `${color}08`,
                  border: '1px solid',
                  borderColor: `${color}20`,
                  transition: 'all 0.2s',
                  '&:hover': {
                    bgcolor: `${color}12`,
                    borderColor: `${color}40`,
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {keyInfo.key}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
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
                      onClick={() => handleViewKey(keyInfo.key)}
                      disabled={loadingKey === keyInfo.key}
                      sx={{ color }}
                    >
                      {loadingKey === keyInfo.key ? <CircularProgress size={14} /> : <Eye size={14} />}
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
            ))}
          </Box>
        </Box>
      )}

      {/* Selected Key Value Viewer */}
      <Collapse in={!!selectedKey}>
        {selectedKey && (
          <Box
            sx={{
              mt: 2,
              p: 2,
              borderRadius: '8px',
              bgcolor: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid',
              borderColor: `${color}30`,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="caption" sx={{ fontWeight: 600, color }}>
                Key: {selectedKey.key}
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
                borderRadius: '6px',
                bgcolor: 'rgba(0, 0, 0, 0.5)',
                fontFamily: 'monospace',
                fontSize: '0.7rem',
                maxHeight: 300,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {JSON.stringify(selectedKey.value, null, 2)}
            </Box>
          </Box>
        )}
      </Collapse>
    </Box>
  );
};
