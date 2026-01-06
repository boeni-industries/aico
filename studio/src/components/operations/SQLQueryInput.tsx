import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { TextField, Box, Typography, Fade, CircularProgress } from '@mui/material';
import { CheckCircle as CheckIcon, AlertCircle as ErrorIcon, AlertTriangle as WarningIcon } from 'lucide-react';
import { format } from 'sql-formatter';
import { Parser } from 'node-sql-parser';

// Create parser instance outside component to avoid recreation on every render
const sqlParser = new Parser();

interface SQLQueryInputProps {
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

export const SQLQueryInput: React.FC<SQLQueryInputProps> = ({
  value,
  onChange,
  label = 'SQL Query',
  helperText,
  rows = 8,
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
      // Parse SQL query with SQLite dialect
      const ast = sqlParser.astify(query, { database: 'sqlite' });
      
      if (!ast) {
        return { 
          status: 'error', 
          message: 'Failed to parse query' 
        };
      }

      const trimmedQuery = query.trim().toUpperCase();
      
      // Check for destructive operations
      const hasDelete = /\bDELETE\s+FROM\b/.test(trimmedQuery);
      const hasUpdate = /\bUPDATE\s+\w+\s+SET\b/.test(trimmedQuery);
      const hasInsert = /\bINSERT\s+INTO\b/.test(trimmedQuery);
      const hasReplace = /\bREPLACE\s+INTO\b/.test(trimmedQuery);
      const isDestructive = hasDelete || hasUpdate || hasInsert || hasReplace;
      
      // Check for forbidden operations
      const hasDrop = /\bDROP\s+(TABLE|INDEX|VIEW)\b/.test(trimmedQuery);
      const hasAlter = /\bALTER\s+TABLE\b/.test(trimmedQuery);
      const hasTruncate = /\bTRUNCATE\b/.test(trimmedQuery);
      const hasCreate = /\bCREATE\s+(TABLE|INDEX|VIEW)\b/.test(trimmedQuery);
      const isForbidden = hasDrop || hasAlter || hasTruncate || hasCreate;
      
      if (isForbidden) {
        let operation = 'operation';
        if (hasDrop) operation = 'DROP';
        else if (hasAlter) operation = 'ALTER';
        else if (hasTruncate) operation = 'TRUNCATE';
        else if (hasCreate) operation = 'CREATE';
        
        return { 
          status: 'error', 
          message: `${operation} operations are forbidden for security` 
        };
      }
      
      if (isDestructive) {
        let operation = 'modification';
        if (hasDelete) operation = 'DELETE';
        else if (hasUpdate) operation = 'UPDATE';
        else if (hasInsert) operation = 'INSERT';
        else if (hasReplace) operation = 'REPLACE';
        
        return { 
          status: 'warning', 
          message: `${operation} detected - enable "Allow Modifications" to execute` 
        };
      }
      
      // Check for SELECT queries
      const hasSelect = /\bSELECT\b/.test(trimmedQuery);
      const hasPragma = /\bPRAGMA\b/.test(trimmedQuery);
      
      if (!hasSelect && !hasPragma && !isDestructive) {
        return { 
          status: 'idle', 
          message: 'Start typing SELECT or PRAGMA query...' 
        };
      }
      
      // Check for incomplete SELECT (missing FROM)
      if (hasSelect && !/\bFROM\b/.test(trimmedQuery) && !/\bSELECT\s+\d+/.test(trimmedQuery)) {
        // If query is very short, it's likely incomplete
        if (query.trim().length < 15) {
          return { 
            status: 'idle', 
            message: 'Continue typing query...' 
          };
        }
        return { 
          status: 'warning', 
          message: 'Add FROM clause to complete query' 
        };
      }
      
      return { 
        status: 'valid', 
        message: 'Query syntax valid ✓' 
      };
    } catch (error: any) {
      // For incomplete queries, show idle status instead of error
      const queryLength = query.trim().length;
      if (queryLength < 10) {
        return { 
          status: 'idle', 
          message: 'Continue typing query...' 
        };
      }
      
      // Parse SQL error messages
      let errorMsg = 'Syntax error in query';
      
      if (error.message) {
        const msg = error.message;
        
        // Check if it's likely an incomplete query
        if (msg.includes('Expected') && queryLength < 30) {
          return { 
            status: 'idle', 
            message: 'Continue typing query...' 
          };
        }
        
        // Extract meaningful error info
        if (msg.includes('Expected')) {
          const match = msg.match(/Expected\s+([^,]+)/);
          if (match) {
            const expected = match[1].replace(/\s+or\s+/g, ' or ');
            errorMsg = `Expected ${expected}`;
          }
        } else if (msg.includes('Unexpected')) {
          const match = msg.match(/Unexpected\s+"([^"]+)"/);
          if (match) {
            errorMsg = `Unexpected '${match[1]}'`;
          }
        } else if (msg.includes('near')) {
          const match = msg.match(/near\s+"([^"]+)"/);
          if (match) {
            errorMsg = `Syntax error near '${match[1]}'`;
          }
        } else {
          // Use first line of error message
          errorMsg = msg.split('\n')[0].substring(0, 100);
        }
        
        // Add location if available
        if (error.location) {
          const { start } = error.location;
          if (start?.line) {
            errorMsg += ` at line ${start.line}`;
            if (start.column) {
              errorMsg += `:${start.column}`;
            }
          }
        }
      }
      
      return { 
        status: 'error', 
        message: errorMsg
      };
    }
  }, []); // No dependencies - validateQuery is stable

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
    if (error) return '#EF4444';
    switch (validation.status) {
      case 'valid': return '#10B981';
      case 'warning': return '#F59E0B';
      case 'error': return '#EF4444';
      default: return 'rgba(59, 130, 246, 0.3)';
    }
  };

  const getValidationIcon = () => {
    switch (validation.status) {
      case 'validating': return <CircularProgress size={14} sx={{ color: '#3B82F6' }} />;
      case 'valid': return <CheckIcon size={16} color="#10B981" />;
      case 'warning': return <WarningIcon size={16} color="#F59E0B" />;
      case 'error': return <ErrorIcon size={16} color="#EF4444" />;
      default: return null;
    }
  };

  const getValidationColor = () => {
    switch (validation.status) {
      case 'validating': return { bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.3)', text: '#3B82F6' };
      case 'valid': return { bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)', text: '#10B981' };
      case 'warning': return { bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.3)', text: '#F59E0B' };
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
        placeholder="SELECT * FROM table_name LIMIT 10"
        sx={{
          '& textarea': { 
            fontFamily: '"Fira Code", monospace', 
            fontSize: '0.875rem', 
            lineHeight: 1.6 
          },
          '& .MuiOutlinedInput-root': {
            bgcolor: 'rgba(0, 0, 0, 0.3)',
            backdropFilter: 'blur(10px)',
            borderRadius: '12px',
            '& fieldset': { 
              borderColor: getBorderColor(),
              borderWidth: validation.status !== 'idle' ? '2px' : '1px'
            },
            '&:hover': { 
              bgcolor: 'rgba(0, 0, 0, 0.4)' 
            },
            '&:hover fieldset': { 
              borderColor: validation.status !== 'idle' ? getBorderColor() : 'rgba(59, 130, 246, 0.5)' 
            },
            '&.Mui-focused': { 
              bgcolor: 'rgba(0, 0, 0, 0.5)' 
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
