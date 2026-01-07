import React, { useState } from 'react';
import { Box, Typography, TextField, Button, CircularProgress, Alert, Chip, Slider, Collapse, IconButton } from '@mui/material';
import { Search, Eye, Copy, ChevronDown, ChevronUp } from 'lucide-react';
import { searchChromaDB, ChromaDBDocument } from '../../api/operations';

interface ChromaDBBrowserProps {
  collectionName: string;
  color: string;
}

export const ChromaDBBrowser: React.FC<ChromaDBBrowserProps> = ({ collectionName, color }) => {
  const [queryText, setQueryText] = useState('');
  const [userId, setUserId] = useState('');
  const [conversationId, setConversationId] = useState('');
  const [minSimilarity, setMinSimilarity] = useState(0.1);
  const [documents, setDocuments] = useState<ChromaDBDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!queryText.trim()) {
      setError('Please enter a search query');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await searchChromaDB({
        collection_name: collectionName,
        query_text: queryText,
        user_id: userId || undefined,
        conversation_id: conversationId || undefined,
        min_similarity: minSimilarity,
        limit: 10,
      });

      setDocuments(response.documents);
    } catch (err: any) {
      setError(err.message || 'Failed to search ChromaDB');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const getSimilarityColor = (score: number): string => {
    if (score >= 0.8) return '#10B981'; // Green
    if (score >= 0.6) return '#F59E0B'; // Yellow
    return '#EF4444'; // Red
  };

  const getSimilarityLabel = (score: number): string => {
    if (score >= 0.8) return 'High';
    if (score >= 0.6) return 'Medium';
    return 'Low';
  };

  return (
    <Box>
      {/* Search Interface */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block', color }}>
          Semantic Search
        </Typography>
        <TextField
          fullWidth
          size="small"
          placeholder="Enter natural language query (e.g., 'AI projects and memory systems')..."
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          sx={{
            mb: 1.5,
            '& .MuiOutlinedInput-root': {
              bgcolor: 'rgba(0, 0, 0, 0.3)',
              '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
            },
          }}
        />

        {/* Filters */}
        <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
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
          <TextField
            size="small"
            placeholder="Conversation ID..."
            value={conversationId}
            onChange={(e) => setConversationId(e.target.value)}
            sx={{
              flex: 1,
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(0, 0, 0, 0.3)',
                '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' },
              },
            }}
          />
        </Box>

        {/* Similarity Threshold */}
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            Min Similarity: {minSimilarity.toFixed(2)}
          </Typography>
          <Slider
            value={minSimilarity}
            onChange={(_, value) => setMinSimilarity(value as number)}
            min={0}
            max={1}
            step={0.05}
            sx={{
              color,
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
            }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            size="small"
            startIcon={loading ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : <Search size={16} />}
            onClick={handleSearch}
            disabled={loading || !queryText.trim()}
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
              setQueryText('');
              setUserId('');
              setConversationId('');
              setDocuments([]);
              setExpandedDoc(null);
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
      {documents.length > 0 && (
        <Box>
          <Typography variant="caption" sx={{ fontWeight: 600, mb: 1, display: 'block', color }}>
            Results: {documents.length} documents (sorted by relevance)
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {documents.map((doc) => {
              const isExpanded = expandedDoc === doc.id;
              const similarityColor = getSimilarityColor(doc.similarity_score);
              const contentPreview = doc.content.length > 200 ? doc.content.substring(0, 200) + '...' : doc.content;

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
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 0.5 }}>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            bgcolor: similarityColor,
                          }}
                        />
                        <Typography variant="caption" sx={{ fontWeight: 600, color: similarityColor, fontSize: '0.7rem' }}>
                          {doc.similarity_score.toFixed(3)} - {getSimilarityLabel(doc.similarity_score)}
                        </Typography>
                      </Box>
                      <Typography variant="body2" sx={{ fontSize: '0.75rem', mb: 0.5 }}>
                        {isExpanded ? doc.content : contentPreview}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {doc.metadata.user_id && (
                          <Chip
                            label={`User: ${doc.metadata.user_id}`}
                            size="small"
                            sx={{
                              bgcolor: `${color}15`,
                              color,
                              fontSize: '0.65rem',
                              height: 20,
                            }}
                          />
                        )}
                        {doc.metadata.role && (
                          <Chip
                            label={doc.metadata.role === 'user' ? '👤 User' : '🤖 Assistant'}
                            size="small"
                            sx={{
                              bgcolor: doc.metadata.role === 'user' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(139, 92, 246, 0.15)',
                              color: doc.metadata.role === 'user' ? '#3B82F6' : '#8B5CF6',
                              fontSize: '0.65rem',
                              height: 20,
                              fontWeight: 600,
                            }}
                          />
                        )}
                        {doc.metadata.timestamp && (
                          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', lineHeight: '20px' }}>
                            {new Date(doc.metadata.timestamp).toLocaleString()}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 0.5, ml: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleCopyContent(doc.content)}
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

                  {/* Expanded Content and Metadata */}
                  <Collapse in={isExpanded}>
                    <Box sx={{ mt: 1 }}>
                      {/* Full Content */}
                      <Box
                        sx={{
                          p: 1.5,
                          borderRadius: '6px',
                          bgcolor: 'rgba(0, 0, 0, 0.4)',
                          mb: 1,
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5, color }}>
                          Full Content:
                        </Typography>
                        <Typography variant="body2" sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {doc.content}
                        </Typography>
                      </Box>
                      
                      {/* Metadata */}
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
                          Metadata:
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
      {!loading && documents.length === 0 && queryText && (
        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', display: 'block', textAlign: 'center', py: 2 }}>
          No documents found matching your query
        </Typography>
      )}
    </Box>
  );
};
