import React, { useRef, useEffect, useState } from 'react';
import { Box, Paper } from '@mui/material';
import Editor, { Monaco, loader } from '@monaco-editor/react';
import * as monacoType from 'monaco-editor';
import { getLanguagePlugin, CompletionSchema } from './languages';
import { httpJson } from '../../api/http';

// Configure Monaco to load from local public directory instead of CDN
// This makes the editor work completely offline
loader.config({ 
  paths: { 
    vs: '/monaco-editor/min/vs' 
  } 
});

export type EditorLanguage = 'sql' | 'cypher' | 'graphql' | 'json' | 'yaml' | 'javascript' | 'typescript';

export interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language: EditorLanguage;
  height?: string | number;
  placeholder?: string;
  readOnly?: boolean;
  showLineNumbers?: boolean;
  minimap?: boolean;
  schemaEndpoint?: string; // API endpoint to fetch schema from
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
  schemaEndpoint,
  onValidate,
}) => {
  const editorRef = useRef<monacoType.editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const [schema, setSchema] = useState<CompletionSchema | null>(null);

  const handleEditorDidMount = (editor: monacoType.editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
  };

  // Fetch schema from endpoint if provided
  useEffect(() => {
    if (!schemaEndpoint) return;

    const fetchSchema = async () => {
      try {
        const rawSchema = await httpJson<any>({
          method: 'GET',
          path: schemaEndpoint,
        });
        
        const plugin = getLanguagePlugin(language);
        if (plugin) {
          const transformedSchema = plugin.transformSchema(rawSchema);
          setSchema(transformedSchema);
        }
      } catch (error) {
        console.error(`[CodeEditor] Failed to fetch schema from ${schemaEndpoint}:`, error);
      }
    };

    fetchSchema();
  }, [schemaEndpoint, language]);

  // Register completion provider using language plugin
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;

    const plugin = getLanguagePlugin(language);
    if (!plugin) return;

    const editor = editorRef.current;
    const monaco = monacoRef.current;

    const disposable = monaco.languages.registerCompletionItemProvider(plugin.languageId, {
        triggerCharacters: plugin.triggerCharacters,
        provideCompletionItems: (model, position) => {
          const word = model.getWordUntilPosition(position);
          const textBeforeCursor = model.getValueInRange({
            startLineNumber: position.lineNumber,
            startColumn: 1,
            endLineNumber: position.lineNumber,
            endColumn: position.column,
          });
          const textAfterCursor = model.getValueInRange({
            startLineNumber: position.lineNumber,
            startColumn: position.column,
            endLineNumber: position.lineNumber,
            endColumn: model.getLineMaxColumn(position.lineNumber),
          });

          const context = {
            model,
            position,
            word,
            textBeforeCursor,
            textAfterCursor,
            fullText: model.getValue(), // Add full document text
          };

          const completionItems = plugin.provideCompletions(context, schema, monaco as any);

          // Deduplicate suggestions by label to prevent Monaco from showing duplicates
          const seen = new Set<string>();
          const uniqueSuggestions = completionItems
            .filter(item => {
              if (seen.has(item.label)) {
                return false;
              }
              seen.add(item.label);
              return true;
            })
            .map(item => ({
              ...item,
              range: {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn,
              },
            }));

          return {
            suggestions: uniqueSuggestions,
          };
        },
      });

    // Add validation using language plugin
    const validateCode = () => {
        const model = editor.getModel();
        if (!model) return;
        
        const code = model.getValue();
        const errors = plugin.validateCode(code, schema, monaco as any);
        
        const markers: monacoType.editor.IMarkerData[] = errors.map(error => ({
          severity: error.severity === 'error' 
            ? monaco.MarkerSeverity.Error 
            : error.severity === 'warning'
            ? monaco.MarkerSeverity.Warning
            : monaco.MarkerSeverity.Info,
          startLineNumber: error.startLine,
          startColumn: error.startColumn,
          endLineNumber: error.endLine,
          endColumn: error.endColumn,
          message: error.message,
        }));
        
        monaco.editor.setModelMarkers(model, plugin.languageId, markers);
      };
      
    // Validate on content change
    const changeDisposable = editor.onDidChangeModelContent(() => {
      validateCode();
    });
    
    // Initial validation
    validateCode();
    
    // Cleanup on unmount or when schema/language changes
    return () => {
      disposable.dispose();
      changeDisposable.dispose();
    };
  }, [language, schema]);

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
        overflow: 'visible', // Allow suggest widget to overflow
        border: '1px solid rgba(59, 130, 246, 0.3)',
        bgcolor: 'rgba(0, 0, 0, 0.4)',
        position: 'relative',
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
            localityBonus: true,
          },
          // Allow suggestion widget to overflow container bounds
          fixedOverflowWidgets: false,
          scrollbar: {
            alwaysConsumeMouseWheel: false,
          },
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
