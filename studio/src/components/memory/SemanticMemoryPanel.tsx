import React, { useState } from 'react';
import { Box, Typography, Paper, Chip, LinearProgress, IconButton } from '@mui/material';
import { InfoOutlined as InfoIcon, Search as SearchIcon, Speed as SpeedIcon, Storage as StorageIcon } from '@mui/icons-material';
import { StyledTooltip } from '../common/StyledTooltip';

interface SemanticMemoryPanelProps {
  vectorCount: number;
  indexSize: string;
  avgLatency: number;
  collections: Array<{
    name: string;
    count: number;
    dimension: number;
  }>;
}

export const SemanticMemoryPanel: React.FC<SemanticMemoryPanelProps> = ({
  vectorCount,
  indexSize,
  avgLatency,
  collections,
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  
  // Calculate health metrics
  const vectorDensity = Math.min((vectorCount / 2000) * 100, 100);
  const latencyHealth = avgLatency < 50 ? 'excellent' : avgLatency < 100 ? 'good' : 'degraded';
  const storageEfficiency = vectorCount > 0 ? (parseFloat(indexSize) / (vectorCount / 1000)).toFixed(2) : '0';
  
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.1em',
            color: 'text.secondary',
          }}
        >
          Semantic Memory (ChromaDB)
        </Typography>
        <StyledTooltip title="Long-term conversation storage using vector embeddings. Enables AICO to recall past conversations through semantic similarity search, combining cosine similarity with BM25 keyword matching for hybrid retrieval." arrow>
          <InfoIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
        </StyledTooltip>
      </Box>
      
      {/* Context Explanation */}
      <Paper sx={{ p: 2, mb: 3, borderRadius: '12px', bgcolor: 'rgba(139, 92, 246, 0.05)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
        <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary', lineHeight: 1.6 }}>
          <strong>What is this?</strong> Conversation segments are converted into 384-dimensional vectors and stored in ChromaDB. 
          When AICO needs context, it uses <strong>hybrid search</strong> (semantic similarity + keyword matching) to retrieve 
          the most relevant past conversations. This enables AICO to remember and reference previous discussions naturally.
        </Typography>
      </Paper>

      {/* Primary Metrics Grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              STORED SEGMENTS
            </Typography>
            <StyledTooltip title="Number of conversation segments stored as vector embeddings. Each segment represents a meaningful chunk of conversation history." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#8B5CF6' }}>
            {vectorCount.toLocaleString()}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            {vectorDensity.toFixed(1)}% of target density
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              RETRIEVAL SPEED
            </Typography>
            <StyledTooltip title="Average time to search and retrieve relevant conversation segments using hybrid search (cosine similarity + BM25)." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: latencyHealth === 'excellent' ? '#10B981' : latencyHealth === 'good' ? '#F59E0B' : '#EF4444' }}>
            {avgLatency}ms
          </Typography>
          <Chip
            label={latencyHealth.toUpperCase()}
            size="small"
            sx={{
              height: 18,
              fontSize: '0.6rem',
              fontWeight: 700,
              bgcolor: latencyHealth === 'excellent' ? 'rgba(16, 185, 129, 0.12)' : latencyHealth === 'good' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(239, 68, 68, 0.12)',
              color: latencyHealth === 'excellent' ? '#10B981' : latencyHealth === 'good' ? '#F59E0B' : '#EF4444',
            }}
          />
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              STORAGE SIZE
            </Typography>
            <StyledTooltip title="Total disk space used by vector embeddings and HNSW index structures in ChromaDB." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
            {indexSize}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            {storageEfficiency} MB per 1K vectors
          </Typography>
        </Paper>
      </Box>
      
      {/* Search Technology Overview */}
      <Paper sx={{ p: 2.5, mb: 3, borderRadius: '12px', border: '1px solid', borderColor: 'divider', bgcolor: 'rgba(255, 255, 255, 0.02)' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <SearchIcon sx={{ fontSize: 20, color: '#8B5CF6' }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
            Hybrid Search Technology
          </Typography>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#8B5CF6', display: 'block', mb: 0.5 }}>
              SEMANTIC SIMILARITY
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary', lineHeight: 1.5 }}>
              Cosine similarity on 384-dim MiniLM embeddings finds conceptually related conversations
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#10B981', display: 'block', mb: 0.5 }}>
              KEYWORD MATCHING
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary', lineHeight: 1.5 }}>
              BM25 algorithm with IDF filtering ensures exact keyword matches aren't missed
            </Typography>
          </Box>
        </Box>
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, color: '#F59E0B', display: 'block', mb: 0.5 }}>
            RRF FUSION
          </Typography>
          <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary', lineHeight: 1.5 }}>
            Reciprocal Rank Fusion combines both methods, ranking results by relevance from multiple signals
          </Typography>
        </Box>
      </Paper>

      {/* Collections with Enhanced Info */}
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block' }}>
              CHROMADB COLLECTIONS
            </Typography>
            <StyledTooltip title="Collections organize vector embeddings by type. Each collection uses HNSW indexing for fast approximate nearest neighbor search." arrow>
              <InfoIcon sx={{ fontSize: 12, color: 'text.secondary', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          <IconButton
            size="small"
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            sx={{ color: 'text.secondary' }}
          >
            <InfoIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {collections.map((collection) => {
            const vectorsPerMB = collection.count > 0 ? (collection.count / parseFloat(indexSize)).toFixed(0) : '0';
            const estimatedConversations = Math.floor(collection.count / 10); // ~10 segments per conversation
            
            return (
              <Paper
                key={collection.name}
                sx={{
                  p: 2,
                  borderRadius: '12px',
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'rgba(255, 255, 255, 0.02)',
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <StorageIcon sx={{ fontSize: 18, color: '#8B5CF6' }} />
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                      {collection.name}
                    </Typography>
                  </Box>
                  <Chip
                    label={`${collection.count.toLocaleString()} segments`}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      bgcolor: 'rgba(139, 92, 246, 0.12)',
                      color: '#8B5CF6',
                      border: '1px solid rgba(139, 92, 246, 0.3)',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1.5, mt: 1.5 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block' }}>
                      Embedding Dimension
                    </Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                      {collection.dimension}d
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block' }}>
                      Est. Conversations
                    </Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                      ~{estimatedConversations.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block' }}>
                      Density
                    </Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                      {vectorsPerMB}/MB
                    </Typography>
                  </Box>
                </Box>
                {showTechnicalDetails && (
                  <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', display: 'block', mb: 0.5 }}>
                      <strong>Index Type:</strong> HNSW (Hierarchical Navigable Small World)
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', display: 'block', mb: 0.5 }}>
                      <strong>Distance Metric:</strong> Cosine Similarity
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', display: 'block' }}>
                      <strong>Model:</strong> all-MiniLM-L6-v2 (sentence-transformers)
                    </Typography>
                  </Box>
                )}
              </Paper>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
};
