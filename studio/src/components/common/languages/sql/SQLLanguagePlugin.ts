/**
 * SQL Language Plugin
 * 
 * Provides SQL-specific autocomplete, validation, and schema integration
 */

import type * as monacoType from 'monaco-editor';
import {
  LanguagePlugin,
  CompletionContext,
  CompletionItem,
  CompletionSchema,
  ValidationError,
} from '../LanguagePlugin';
import { SQL_KEYWORDS, SQL_FUNCTIONS, SQL_FORBIDDEN_OPERATIONS } from './sqlKeywords';

interface SQLSchema {
  tables: string[];
  columns: Record<string, string[]>;
}

export class SQLLanguagePlugin implements LanguagePlugin {
  readonly languageId = 'sql';
  readonly triggerCharacters = ['.', ' '];

  transformSchema(rawSchema: any): CompletionSchema {
    return {
      tables: rawSchema.tables || [],
      columns: rawSchema.columns || {},
    } as SQLSchema;
  }

  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[] {
    const completionItems: CompletionItem[] = [];
    const sqlSchema = schema as SQLSchema | null;

    const range = {
      startLineNumber: context.position.lineNumber,
      endLineNumber: context.position.lineNumber,
      startColumn: context.word.startColumn,
      endColumn: context.word.endColumn,
    };

    // Add SQL keywords
    SQL_KEYWORDS.forEach((keyword) => {
      completionItems.push({
        label: keyword,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: keyword,
        detail: 'keyword',
        documentation: `SQL keyword: ${keyword}`,
        sortText: '0' + keyword,
      });
    });

    // Add SQL functions
    SQL_FUNCTIONS.forEach((func) => {
      completionItems.push({
        label: func,
        kind: monaco.languages.CompletionItemKind.Function,
        insertText: `${func}()`,
        detail: 'function',
        documentation: `SQL function: ${func}`,
        sortText: '1' + func,
      });
    });

    // Add table names from schema
    if (sqlSchema?.tables) {
      sqlSchema.tables.forEach((table) => {
        completionItems.push({
          label: table,
          kind: monaco.languages.CompletionItemKind.Class,
          insertText: table,
          detail: 'table',
          documentation: `Database table: ${table}`,
          sortText: '2' + table,
        });

        // Add columns for this table
        if (sqlSchema.columns?.[table]) {
          sqlSchema.columns[table].forEach((column) => {
            completionItems.push({
              label: `${table}.${column}`,
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: `${table}.${column}`,
              detail: 'column',
              documentation: `Column ${column} in table ${table}`,
              sortText: '3' + column,
            });
          });
        }
      });
    }

    return completionItems;
  }

  validateCode(
    code: string,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): ValidationError[] {
    const errors: ValidationError[] = [];

    if (!code.trim()) {
      return errors;
    }

    // Check for forbidden operations
    SQL_FORBIDDEN_OPERATIONS.forEach((op) => {
      const regex = new RegExp(`\\b${op}\\b`, 'gi');
      let match;
      while ((match = regex.exec(code)) !== null) {
        const lines = code.substring(0, match.index).split('\n');
        const line = lines.length;
        const column = lines[lines.length - 1].length + 1;

        errors.push({
          severity: 'error',
          startLine: line,
          startColumn: column,
          endLine: line,
          endColumn: column + op.length,
          message: `Forbidden operation: ${op}`,
        });
      }
    });

    // Check for incomplete SELECT
    if (/\bSELECT\b/i.test(code) && !/\bFROM\b/i.test(code) && !/\bSELECT\s+\d+/i.test(code)) {
      const match = /\bSELECT\b/i.exec(code);
      if (match) {
        const lines = code.substring(0, match.index).split('\n');
        const line = lines.length;
        const column = lines[lines.length - 1].length + 1;

        errors.push({
          severity: 'warning',
          startLine: line,
          startColumn: column,
          endLine: line,
          endColumn: column + 6,
          message: 'SELECT query should include FROM clause',
        });
      }
    }

    return errors;
  }
}
