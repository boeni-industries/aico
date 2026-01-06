import React, { useRef, useEffect } from 'react';
import { Box, Paper } from '@mui/material';
import Editor, { Monaco, loader } from '@monaco-editor/react';
import * as monacoType from 'monaco-editor';

// Configure Monaco to load from local public directory instead of CDN
// This makes the editor work completely offline
loader.config({ 
  paths: { 
    vs: '/monaco-editor/min/vs' 
  } 
});

export type EditorLanguage = 'sql' | 'graphql' | 'json' | 'yaml' | 'javascript' | 'typescript';

export interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language: EditorLanguage;
  height?: string | number;
  placeholder?: string;
  readOnly?: boolean;
  showLineNumbers?: boolean;
  minimap?: boolean;
  suggestions?: {
    tables?: string[];
    columns?: Record<string, string[]>;
    keywords?: string[];
  };
  onValidate?: (markers: monacoType.editor.IMarker[]) => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  language,
  height = 200,
  placeholder = 'Start typing...',
  readOnly = false,
  showLineNumbers = true,
  minimap = false,
  suggestions,
  onValidate,
}) => {
  const editorRef = useRef<monacoType.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);

  const handleEditorDidMount = (editor: monacoType.editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
  };

  // Register completion provider when suggestions change
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current || language !== 'sql' || !suggestions) {
      return;
    }

    const editor = editorRef.current;
    const monaco = monacoRef.current;

    const disposable = monaco.languages.registerCompletionItemProvider('sql', {
        triggerCharacters: ['.', ' '],
        provideCompletionItems: (model, position) => {
          const word = model.getWordUntilPosition(position);
          const range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endColumn: word.endColumn,
          };

          const completionItems: monacoType.languages.CompletionItem[] = [];
          
          // Get text before cursor to provide context-aware suggestions
          const textBeforeCursor = model.getValueInRange({
            startLineNumber: position.lineNumber,
            startColumn: 1,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
          });

          // Add SQL keywords
          const sqlKeywords = [
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
            'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
            'AS', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'INSERT', 'UPDATE',
            'DELETE', 'CREATE', 'DROP', 'ALTER', 'TABLE', 'INDEX', 'VIEW',
          ];

          sqlKeywords.forEach((keyword) => {
            completionItems.push({
              label: keyword,
              kind: monaco.languages.CompletionItemKind.Keyword,
              insertText: keyword,
              range,
              detail: 'keyword',
              documentation: `SQL keyword: ${keyword}`,
              sortText: '0' + keyword,
            });
          });

          // Add table names
          if (suggestions.tables) {
            suggestions.tables.forEach((table) => {
              completionItems.push({
                label: table,
                kind: monaco.languages.CompletionItemKind.Class,
                insertText: table,
                range,
                detail: 'table',
                documentation: `Database table: ${table}`,
                sortText: '1' + table,
              });

              // Add columns for this table
              if (suggestions.columns && suggestions.columns[table]) {
                suggestions.columns[table].forEach((column) => {
                  completionItems.push({
                    label: `${table}.${column}`,
                    kind: monaco.languages.CompletionItemKind.Field,
                    insertText: `${table}.${column}`,
                    range,
                    detail: 'column',
                    documentation: `Column ${column} in table ${table}`,
                    sortText: '2' + column,
                  });
                });
              }
            });
          }

          // Add custom keywords
          if (suggestions.keywords) {
            suggestions.keywords.forEach((keyword) => {
              completionItems.push({
                label: keyword,
                kind: monacoType.languages.CompletionItemKind.Keyword,
                insertText: keyword,
                range,
                detail: 'Custom Keyword',
              });
            });
          }

          return { suggestions: completionItems };
        },
      });

    // Add SQL validation
    const validateSQL = () => {
        const model = editor.getModel();
        if (!model) return;
        
        const value = model.getValue();
        const markers: monacoType.editor.IMarkerData[] = [];
        
        // Basic SQL validation
        if (value.trim()) {
          // Check for forbidden operations
          const forbidden = ['DROP', 'TRUNCATE', 'ALTER'];
          forbidden.forEach(op => {
            const regex = new RegExp(`\\b${op}\\b`, 'gi');
            let match;
            while ((match = regex.exec(value)) !== null) {
              const pos = model.getPositionAt(match.index);
              markers.push({
                severity: monaco.MarkerSeverity.Error,
                startLineNumber: pos.lineNumber,
                startColumn: pos.column,
                endLineNumber: pos.lineNumber,
                endColumn: pos.column + op.length,
                message: `Forbidden operation: ${op}`,
              });
            }
          });
          
          // Check for incomplete SELECT
          if (/\bSELECT\b/i.test(value) && !/\bFROM\b/i.test(value) && !/\bSELECT\s+\d+/i.test(value)) {
            const match = /\bSELECT\b/i.exec(value);
            if (match) {
              const pos = model.getPositionAt(match.index);
              markers.push({
                severity: monaco.MarkerSeverity.Warning,
                startLineNumber: pos.lineNumber,
                startColumn: pos.column,
                endLineNumber: pos.lineNumber,
                endColumn: pos.column + 6,
                message: 'SELECT query should include FROM clause',
              });
            }
          }
        }
        
        monaco.editor.setModelMarkers(model, 'sql', markers);
      };
      
    // Validate on content change
    const changeDisposable = editor.onDidChangeModelContent(() => {
      validateSQL();
    });
    
    // Initial validation
    validateSQL();
    
    // Cleanup on unmount or when suggestions change
    return () => {
      disposable.dispose();
      changeDisposable.dispose();
    };
  }, [language, suggestions]);

  useEffect(() => {
    if (editorRef.current && onValidate) {
      const model = editorRef.current.getModel();
      if (model) {
        const markers = monacoRef.current?.editor.getModelMarkers({ resource: model.uri }) || [];
        onValidate(markers);
      }
    }
  }, [value, onValidate]);

  return (
    <Paper
      sx={{
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        bgcolor: 'rgba(0, 0, 0, 0.4)',
      }}
    >
      <Editor
        height={height}
        language={language}
        value={value}
        onChange={(newValue) => onChange(newValue || '')}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        loading={<Box sx={{ p: 2, color: 'rgba(255,255,255,0.7)' }}>Loading editor...</Box>}
        options={{
          readOnly,
          minimap: { enabled: minimap },
          lineNumbers: showLineNumbers ? 'on' : 'off',
          fontSize: 14,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          padding: { top: 16, bottom: 16 },
          // Enhanced autocomplete settings
          suggestOnTriggerCharacters: true,
          quickSuggestions: {
            other: true,
            comments: false,
            strings: false,
          },
          acceptSuggestionOnCommitCharacter: true,
          acceptSuggestionOnEnter: 'on',
          wordBasedSuggestions: 'off', // Use our custom suggestions only
          suggest: {
            showKeywords: true,
            showSnippets: true,
            showClasses: true,
            showFields: true,
            showFunctions: true,
            insertMode: 'replace',
            filterGraceful: true,
            snippetsPreventQuickSuggestions: false,
            preview: true,
            showIcons: true,
            showStatusBar: true,
          },
          // Fix suggestion widget overflow
          fixedOverflowWidgets: true,
          placeholder: placeholder,
          bracketPairColorization: {
            enabled: true,
          },
          renderLineHighlight: 'all',
          cursorBlinking: 'smooth',
          smoothScrolling: true,
          // Disable features that require web workers
          'semanticHighlighting.enabled': false,
        }}
      />
    </Paper>
  );
};
