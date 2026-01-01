import React, { useState, useEffect, useCallback } from 'react';
import { TextField, Box, Typography, Fade, CircularProgress } from '@mui/material';
import { CheckCircle as CheckIcon, Error as ErrorIcon, Warning as WarningIcon } from '@mui/icons-material';
import { parse } from '@neo4j-cypher/editor-support';

interface CypherQueryInputProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  helperText?: string;
  rows?: number;
  disabled?: boolean;
  error?: boolean;
  showValidation?: boolean;
  onValidationChange?: (status: 'idle' | 'validating' | 'valid' | 'warning' | 'error', message?: string) => void;
}

interface ValidationResult {
  status: 'idle' | 'validating' | 'valid' | 'warning' | 'error';
  message?: string;
}

export const CypherQueryInput: React.FC<CypherQueryInputProps> = ({
  value,
  onChange,
  label = 'Cypher Query',
  helperText,
  rows = 10,
  disabled = false,
  error = false,
  showValidation = true,
  onValidationChange,
}) => {
  const [validation, setValidation] = useState<ValidationResult>({ status: 'idle' });

  const validateQuery = useCallback((query: string): ValidationResult => {
    if (!query.trim()) {
      return { status: 'idle' };
    }

    try {
      const parseResult = parse(query) as any;
      
      if (!parseResult || !parseResult.errorListener) {
        return { 
          status: 'error', 
          message: 'Failed to parse query' 
        };
      }
      
      const errors = parseResult.errorListener.errors || [];
      
      if (errors.length > 0) {
        const firstError = errors[0];
        const rawMsg = firstError.msg || 'Syntax error';
        const location = firstError.line ? ` at line ${firstError.line}:${firstError.col}` : '';
        
        // Parse and simplify error messages
        let cleanMsg = rawMsg;
        
        // Handle "extraneous input" errors
        if (rawMsg.includes('extraneous input')) {
          const match = rawMsg.match(/extraneous input '([^']+)'/);
          if (match) {
            const token = match[1];
            cleanMsg = `Unexpected '${token}' - not a valid Cypher keyword`;
          }
        }
        // Handle "mismatched input" errors
        else if (rawMsg.includes('mismatched input')) {
          const match = rawMsg.match(/mismatched input '([^']+)'/);
          if (match) {
            const token = match[1];
            if (token === '<EOF>') {
              cleanMsg = 'Incomplete query - add RETURN clause';
            } else {
              cleanMsg = `Unexpected '${token}' here`;
            }
          }
        }
        // Handle "missing" errors
        else if (rawMsg.includes('missing')) {
          const match = rawMsg.match(/missing '([^']+)'/);
          if (match) {
            cleanMsg = `Missing '${match[1]}'`;
          }
        }
        // Truncate "expecting" lists - they're useless
        else if (rawMsg.includes('expecting {')) {
          cleanMsg = rawMsg.split('expecting {')[0].trim();
          if (!cleanMsg) {
            cleanMsg = 'Syntax error - check Cypher syntax';
          }
        }
        
        return { 
          status: 'error', 
          message: `${cleanMsg}${location}` 
        };
      }
      
      const trimmedQuery = query.trim().toUpperCase();
      const hasMatch = /\bMATCH\b/.test(trimmedQuery);
      const hasReturn = /\bRETURN\b/.test(trimmedQuery);
      const hasCreate = /\bCREATE\b/.test(trimmedQuery);
      const hasMerge = /\bMERGE\b/.test(trimmedQuery);
      const hasDelete = /\bDELETE\b/.test(trimmedQuery);
      const hasSet = /\bSET\b/.test(trimmedQuery);
      const hasRemove = /\bREMOVE\b/.test(trimmedQuery);
      
      // Check for incomplete queries
      if (hasMatch && !hasReturn && !hasDelete && !hasSet && !hasRemove) {
        return { 
          status: 'error', 
          message: 'Incomplete query - MATCH must be followed by RETURN, DELETE, SET, or REMOVE' 
        };
      }
      
      if ((hasCreate || hasMerge) && !hasReturn && !hasSet) {
        return { 
          status: 'warning', 
          message: 'Consider adding RETURN to see created nodes' 
        };
      }
      
      if (!hasMatch && !hasCreate && !hasMerge && !hasReturn) {
        return { 
          status: 'warning', 
          message: 'Query should start with MATCH, CREATE, or MERGE' 
        };
      }
      
      return { 
        status: 'valid', 
        message: 'Query looks complete ✓' 
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Syntax error in query';
      return { 
        status: 'error', 
        message: errorMsg
      };
    }
  }, []);

  useEffect(() => {
    if (!value.trim()) {
      setValidation({ status: 'idle' });
      onValidationChange?.('idle');
      return;
    }
    
    setValidation({ status: 'validating' });
    
    const timer = setTimeout(() => {
      const result = validateQuery(value);
      setValidation(result);
      onValidationChange?.(result.status, result.message);
    }, 500);
    
    return () => clearTimeout(timer);
  }, [value, validateQuery, onValidationChange]);

  const getBorderColor = () => {
    if (error) return '#ED7867';
    switch (validation.status) {
      case 'valid': return '#10B981';
      case 'warning': return '#F59E0B';
      case 'error': return '#ED7867';
      default: return 'rgba(255, 255, 255, 0.1)';
    }
  };

  const getValidationIcon = () => {
    switch (validation.status) {
      case 'validating': return <CircularProgress size={14} sx={{ color: '#8B5CF6' }} />;
      case 'valid': return <CheckIcon sx={{ fontSize: 16, color: '#10B981' }} />;
      case 'warning': return <WarningIcon sx={{ fontSize: 16, color: '#FBBF24' }} />;
      case 'error': return <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />;
      default: return null;
    }
  };

  const getValidationColor = () => {
    switch (validation.status) {
      case 'validating': return { bg: 'rgba(139, 92, 246, 0.15)', border: 'rgba(139, 92, 246, 0.3)', text: '#8B5CF6' };
      case 'valid': return { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)', text: '#10B981' };
      case 'warning': return { bg: 'rgba(251, 191, 36, 0.15)', border: 'rgba(251, 191, 36, 0.3)', text: '#FBBF24' };
      case 'error': return { bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.3)', text: '#EF4444' };
      default: return { bg: 'transparent', border: 'transparent', text: 'transparent' };
    }
  };

  const colors = getValidationColor();

  return (
    <Box>
      {showValidation && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
            {label}
          </Typography>
          <Fade in={validation.status !== 'idle'} timeout={300}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 0.75, 
              px: 1.5, 
              py: 0.5, 
              borderRadius: '8px', 
              backdropFilter: 'blur(10px)',
              bgcolor: colors.bg,
              border: `1px solid ${colors.border}`
            }}>
              {getValidationIcon()}
              <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600, color: colors.text }}>
                {validation.message || 'Validating...'}
              </Typography>
            </Box>
          </Fade>
        </Box>
      )}
      
      <TextField
        value={value}
        onChange={(e) => onChange(e.target.value)}
        error={error || validation.status === 'error'}
        helperText={helperText}
        fullWidth
        multiline
        rows={rows}
        disabled={disabled}
        sx={{
          '& textarea': { 
            fontFamily: '"Fira Code", monospace', 
            fontSize: '0.875rem', 
            lineHeight: 1.6 
          },
          '& .MuiOutlinedInput-root': {
            bgcolor: 'rgba(255, 255, 255, 0.03)',
            backdropFilter: 'blur(10px)',
            borderRadius: '20px',
            '& fieldset': { 
              borderColor: getBorderColor(),
              borderWidth: validation.status !== 'idle' ? '2px' : '1px'
            },
            '&:hover': { 
              bgcolor: 'rgba(255, 255, 255, 0.05)' 
            },
            '&:hover fieldset': { 
              borderColor: validation.status !== 'idle' ? getBorderColor() : 'rgba(184, 161, 234, 0.3)' 
            },
            '&.Mui-focused': { 
              bgcolor: 'rgba(255, 255, 255, 0.08)' 
            },
            '&.Mui-focused fieldset': {
              borderColor: getBorderColor(),
              borderWidth: '2px',
              boxShadow: `0 0 0 3px ${getBorderColor()}20`
            }
          }
        }}
      />
    </Box>
  );
};
