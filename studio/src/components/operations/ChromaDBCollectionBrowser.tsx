import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Button, CircularProgress, Alert, Chip, IconButton, Collapse, Checkbox } from '@mui/material';
import { Search, ChevronDown, ChevronUp, Copy, Trash2, RefreshCw } from 'lucide-react';
import { browseChromaDBCollection, deleteChromaDBDocuments, ChromaDBBrowseDocument } from '../../api/operations';

interface ChromaDBCollectionBrowserProps {
  collectionName: string;
  color: string;
  onRefresh?: () => void;
}

type Document = ChromaDBBrowseDocument;

export const ChromaDBCollectionBrowser: React.FC<ChromaDBCollectionBrowserProps> = ({ 
  collectionName, 
  color,
  onRefresh 
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [filterText, setFilterText] = useState('');

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await browseChromaDBCollection(collectionName, 100);
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [collectionName]);

  const handleDelete = async () => {
    if (selectedDocs.size === 0) return;

    if (!window.confirm(`Delete ${selectedDocs.size} document(s)? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(true);
      setError(null);
      
      await deleteChromaDBDocuments({
        collection_name: collectionName,
        document_ids: Array.from(selectedDocs),
      });
      
      setDocuments(docs => docs.filter(doc => !selectedDocs.has(doc.id)));
      setSelectedDocs(new Set());
      if (onRefresh) onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete documents');
    } finally {
      setDeleting(false);
    }
  };

  const toggleDocSelection = (docId: string) => {
    setSelectedDocs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedDocs.size === filteredDocs.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(filteredDocs.map(doc => doc.id)));
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  // Filter documents based on search text
  const filteredDocs = documents.filter(doc => {
    if (!filterText) return true;
    const searchLower = filterText.toLowerCase();
    return (
      doc.document.toLowerCase().includes(searchLower) ||
      doc.id.toLowerCase().includes(searchLower) ||
      JSON.stringify(doc.metadata).toLowerCase().includes(searchLower)
    );
  });

  const getEntityType = (doc: Document): string => {
    // Extract entity type from document string (e.g., "PERSON: {...}")
    const match = doc.document.match(/^([A-Z_]+):/);
    return match ? match[1] : 'UNKNOWN';
  };

  const getEntityColor = (type: string): string => {
    const colors: Record<string, string> = {
      'PERSON': '#8B5CF6',
      'NAME': '#3B82F6',
      'ORGANIZATION': '#10B981',
      'LOCATION': '#F59E0B',
      'DATE': '#EC4899',
      'INTERESTED_IN': '#6366F1',
      'RELATED_TO': '#14B8A6',
    };
    return colors[type] || '#6B7280';
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block', color }}>
          {collectionName === 'kg_nodes' ? 'Knowledge Graph Entities' : 
           collectionName === 'kg_edges' ? 'Knowledge Graph Relationships' : 
           'Collection Browser'}
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1.5, display: 'block', fontStyle: 'italic' }}>
          Browsing: {collectionName} collection ({documents.length} total documents)
        </Typography>

        {/* Filter */}
        <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Filter by content, ID, or metadata..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            sx={{
              '& .MuiOutlinedInput-root': {
                fontSize: '0.75rem',
                bgcolor: 'rgba(255, 255, 255, 0.05)',
              },
            }}
          />
          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshCw size={14} />}
            onClick={loadDocuments}
            disabled={loading}
            sx={{
              textTransform: 'none',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: 'rgba(255, 255, 255, 0.8)',
              fontSize: '0.7rem',
            }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: '0.75rem' }}>
          {error}
        </Alert>
      )}

      {/* Loading */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress size={24} sx={{ color }} />
        </Box>
      )}

      {/* Results */}
      {!loading && filteredDocs.length > 0 && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Checkbox
                size="small"
                checked={selectedDocs.size === filteredDocs.length && filteredDocs.length > 0}
                indeterminate={selectedDocs.size > 0 && selectedDocs.size < filteredDocs.length}
                onChange={toggleSelectAll}
                sx={{ color, '&.Mui-checked': { color } }}
              />
              <Typography variant="caption" sx={{ fontWeight: 600, color }}>
                {filteredDocs.length} documents {selectedDocs.size > 0 && `(${selectedDocs.size} selected)`}
              </Typography>
            </Box>
            {selectedDocs.size > 0 && (
              <Button
                variant="contained"
                size="small"
                startIcon={deleting ? <CircularProgress size={14} sx={{ color: '#fff' }} /> : <Trash2 size={14} />}
                onClick={handleDelete}
                disabled={deleting}
                sx={{
                  textTransform: 'none',
                  bgcolor: '#EF4444',
                  '&:hover': { bgcolor: '#DC2626' },
                  fontSize: '0.7rem',
                  py: 0.5,
                }}
              >
                Delete Selected
              </Button>
            )}
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: '500px', overflowY: 'auto' }}>
            {filteredDocs.map((doc) => {
              const isExpanded = expandedDoc === doc.id;
              const entityType = getEntityType(doc);
              const entityColor = getEntityColor(entityType);

              return (
                <Box
                  key={doc.id}
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
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                    <Checkbox
                      size="small"
                      checked={selectedDocs.has(doc.id)}
                      onChange={() => toggleDocSelection(doc.id)}
                      sx={{ 
                        color, 
                        '&.Mui-checked': { color },
                        mt: -0.5,
                      }}
                    />
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Chip
                          label={entityType}
                          size="small"
                          sx={{
                            bgcolor: `${entityColor}20`,
                            color: entityColor,
                            fontSize: '0.65rem',
                            height: 20,
                            fontWeight: 600,
                          }}
                        />
                        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                          ID: {doc.id.substring(0, 12)}...
                        </Typography>
                      </Box>
                      <Typography variant="body2" sx={{ fontSize: '0.75rem', mb: 0.5, fontFamily: 'monospace' }}>
                        {doc.document}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {doc.metadata.user_id && (
                          <Chip
                            label={`User: ${doc.metadata.user_id.substring(0, 8)}...`}
                            size="small"
                            sx={{
                              bgcolor: `${color}15`,
                              color,
                              fontSize: '0.65rem',
                              height: 20,
                            }}
                          />
                        )}
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleCopyContent(doc.document)}
                        sx={{ color }}
                      >
                        <Copy size={14} />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => setExpandedDoc(isExpanded ? null : doc.id)}
                        sx={{ color }}
                      >
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </IconButton>
                    </Box>
                  </Box>

                  {/* Expanded Metadata */}
                  <Collapse in={isExpanded}>
                    <Box sx={{ mt: 1 }}>
                      <Box
                        sx={{
                          p: 1,
                          borderRadius: '6px',
                          bgcolor: 'rgba(0, 0, 0, 0.3)',
                          fontSize: '0.7rem',
                          fontFamily: 'monospace',
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color }}>
                          Full Metadata:
                        </Typography>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {JSON.stringify(doc.metadata, null, 2)}
                        </pre>
                      </Box>
                    </Box>
                  </Collapse>
                </Box>
              );
            })}
          </Box>
        </Box>
      )}

      {/* No Results */}
      {!loading && filteredDocs.length === 0 && documents.length > 0 && (
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', display: 'block', textAlign: 'center', py: 2 }}>
          No documents match your filter
        </Typography>
      )}

      {!loading && documents.length === 0 && (
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', display: 'block', textAlign: 'center', py: 2 }}>
          No documents in this collection
        </Typography>
      )}
    </Box>
  );
};
