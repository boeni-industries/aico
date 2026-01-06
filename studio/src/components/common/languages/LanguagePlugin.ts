/**
 * Language Plugin Interface
 * 
 * Defines the contract for language-specific features in the CodeEditor.
 * Each language (SQL, Cypher, etc.) implements this interface to provide
 * custom autocomplete, validation, and schema integration.
 */

import type * as monacoType from 'monaco-editor';

export interface CompletionContext {
  model: monacoType.editor.ITextModel;
  position: monacoType.Position;
  word: monacoType.editor.IWordAtPosition;
  textBeforeCursor: string;
  textAfterCursor: string;
}

export interface ValidationError {
  severity: 'error' | 'warning' | 'info';
  startLine: number;
  startColumn: number;
  endLine: number;
  endColumn: number;
  message: string;
}

export interface CompletionItem {
  label: string;
  kind: monacoType.languages.CompletionItemKind;
  insertText: string;
  detail: string;
  documentation?: string;
  sortText: string;
}

/**
 * Generic schema structure that plugins can transform into
 */
export interface CompletionSchema {
  [key: string]: any;
}

/**
 * Language Plugin Interface
 */
export interface LanguagePlugin {
  /**
   * Language identifier (e.g., 'sql', 'cypher')
   */
  readonly languageId: string;

  /**
   * Characters that trigger autocomplete
   */
  readonly triggerCharacters: string[];

  /**
   * Transform raw schema data from API into plugin-specific format
   */
  transformSchema(rawSchema: any): CompletionSchema;

  /**
   * Provide completion items based on context and schema
   */
  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[];

  /**
   * Validate code and return errors/warnings
   */
  validateCode(
    code: string,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): ValidationError[];
}
