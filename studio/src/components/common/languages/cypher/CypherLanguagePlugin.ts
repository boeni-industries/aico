/**
 * Cypher/GQL Language Plugin
 * 
 * Provides Cypher-specific autocomplete, validation, and schema integration
 * for knowledge graph queries
 */

import type * as monacoType from 'monaco-editor';
import {
  LanguagePlugin,
  CompletionContext,
  CompletionItem,
  CompletionSchema,
  ValidationError,
} from '../LanguagePlugin';
import { CYPHER_KEYWORDS, CYPHER_FUNCTIONS, CYPHER_FORBIDDEN_OPERATIONS } from './cypherKeywords';

interface CypherSchema {
  nodeLabels: string[];
  relationshipTypes: string[];
  properties: Record<string, string[]>;
}

export class CypherLanguagePlugin implements LanguagePlugin {
  readonly languageId = 'cypher';
  readonly triggerCharacters = [':', '.', ' ', '(', '['];

  transformSchema(rawSchema: any): CompletionSchema {
    return {
      nodeLabels: rawSchema.nodeLabels || rawSchema.nodes || [],
      relationshipTypes: rawSchema.relationshipTypes || rawSchema.relationships || [],
      properties: rawSchema.properties || {},
    } as CypherSchema;
  }

  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[] {
    const completionItems: CompletionItem[] = [];
    const cypherSchema = schema as CypherSchema | null;

    // Add Cypher keywords
    CYPHER_KEYWORDS.forEach((keyword) => {
      completionItems.push({
        label: keyword,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: keyword,
        detail: 'keyword',
        documentation: `Cypher keyword: ${keyword}`,
        sortText: '0' + keyword,
      });
    });

    // Add Cypher functions
    CYPHER_FUNCTIONS.forEach((func) => {
      completionItems.push({
        label: func,
        kind: monaco.languages.CompletionItemKind.Function,
        insertText: `${func}()`,
        detail: 'function',
        documentation: `Cypher function: ${func}`,
        sortText: '1' + func,
      });
    });

    // Add node labels from schema
    if (cypherSchema?.nodeLabels) {
      cypherSchema.nodeLabels.forEach((label) => {
        completionItems.push({
          label: label,
          kind: monaco.languages.CompletionItemKind.Class,
          insertText: label,
          detail: 'node label',
          documentation: `Node label: ${label}`,
          sortText: '2' + label,
        });

        // Add properties for this node label
        if (cypherSchema.properties?.[label]) {
          cypherSchema.properties[label].forEach((prop) => {
            completionItems.push({
              label: `${label}.${prop}`,
              kind: monaco.languages.CompletionItemKind.Property,
              insertText: prop,
              detail: 'property',
              documentation: `Property ${prop} on ${label}`,
              sortText: '4' + prop,
            });
          });
        }
      });
    }

    // Add relationship types from schema
    if (cypherSchema?.relationshipTypes) {
      cypherSchema.relationshipTypes.forEach((relType) => {
        completionItems.push({
          label: relType,
          kind: monaco.languages.CompletionItemKind.Reference,
          insertText: relType,
          detail: 'relationship',
          documentation: `Relationship type: ${relType}`,
          sortText: '3' + relType,
        });
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
    CYPHER_FORBIDDEN_OPERATIONS.forEach((op) => {
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

    // Check for MATCH without RETURN
    if (/\bMATCH\b/i.test(code) && !/\bRETURN\b/i.test(code) && !/\bWITH\b/i.test(code)) {
      const match = /\bMATCH\b/i.exec(code);
      if (match) {
        const lines = code.substring(0, match.index).split('\n');
        const line = lines.length;
        const column = lines[lines.length - 1].length + 1;

        errors.push({
          severity: 'warning',
          startLine: line,
          startColumn: column,
          endLine: line,
          endColumn: column + 5,
          message: 'MATCH query should include RETURN or WITH clause',
        });
      }
    }

    // Check for unbalanced parentheses
    const openParens = (code.match(/\(/g) || []).length;
    const closeParens = (code.match(/\)/g) || []).length;
    if (openParens !== closeParens) {
      errors.push({
        severity: 'error',
        startLine: 1,
        startColumn: 1,
        endLine: 1,
        endColumn: 1,
        message: `Unbalanced parentheses: ${openParens} open, ${closeParens} close`,
      });
    }

    return errors;
  }
}
