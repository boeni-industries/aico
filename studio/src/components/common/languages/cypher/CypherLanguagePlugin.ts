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
  nodeProperties: string[];
  relationshipProperties: string[];
}

// Static cache shared across all instances to prevent duplicates
const completionCache = {
  key: '',
  items: [] as CompletionItem[]
};

export class CypherLanguagePlugin implements LanguagePlugin {
  readonly languageId = 'cypher';
  readonly triggerCharacters = [':', '.', ' ', '(', '['];

  transformSchema(rawSchema: any): CompletionSchema {
    return {
      nodeLabels: rawSchema.nodeLabels || rawSchema.nodes || [],
      relationshipTypes: rawSchema.relationshipTypes || rawSchema.relationships || [],
      nodeProperties: rawSchema.nodeProperties || [],
      relationshipProperties: rawSchema.relationshipProperties || [],
    } as CypherSchema;
  }

  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[] {
    // Create a unique key for this completion request
    const completionKey = `${context.position.lineNumber}:${context.position.column}:${context.textBeforeCursor}`;
    
    // Return cached results if this is a duplicate call
    if (completionKey === completionCache.key && completionCache.items.length > 0) {
      return completionCache.items;
    }
    
    const completionItems: CompletionItem[] = [];
    const cypherSchema = schema as CypherSchema | null;

    // Check if we're completing after a dot (property access)
    const isDotCompletion = context.textBeforeCursor.trim().endsWith('.');
    
    if (isDotCompletion && cypherSchema) {
      // Extract variable name before the dot (e.g., "n" from "n.")
      const match = context.textBeforeCursor.match(/(\w+)\.\s*$/);
      if (match) {
        const varName = match[1];
        
        // Determine if this is a node or relationship variable
        // Use fullText to see the entire query, not just the current line
        const fullText = context.fullText;
        
        // Check if variable is defined in a relationship pattern [varName:TYPE] or [varName]
        const relPattern = new RegExp(`\\[\\s*${varName}\\s*(?::\\s*[\\w_]+)?\\s*\\]`, 'i');
        const isRelVar = relPattern.test(fullText);
        
        // Check if variable is defined in a node pattern (varName:LABEL) or (varName)
        const nodePattern = new RegExp(`\\(\\s*${varName}\\s*(?::\\s*[\\w_]+)?\\s*\\)`, 'i');
        const isNodeVar = !isRelVar && nodePattern.test(fullText);
        
        // Add ONLY the appropriate properties based on variable type
        if (isRelVar && cypherSchema.relationshipProperties) {
          // Relationship variable - show only relationship properties
          const seen = new Set<string>();
          cypherSchema.relationshipProperties.forEach((prop) => {
            if (!seen.has(prop)) {
              seen.add(prop);
              completionItems.push({
                label: prop,
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: prop,
                detail: 'relationship property',
                documentation: `Relationship property: ${prop}`,
                sortText: '0' + prop,
              });
            }
          });
          // Cache and return
          completionCache.key = completionKey;
          completionCache.items = completionItems;
          return completionItems;
        }
        
        if (isNodeVar && cypherSchema.nodeProperties) {
          // Node variable - show only node properties
          const seen = new Set<string>();
          cypherSchema.nodeProperties.forEach((prop) => {
            if (!seen.has(prop)) {
              seen.add(prop);
              completionItems.push({
                label: prop,
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: prop,
                detail: 'node property',
                documentation: `Node property: ${prop}`,
                sortText: '0' + prop,
              });
            }
          });
          // Cache and return
          completionCache.key = completionKey;
          completionCache.items = completionItems;
          return completionItems;
        }
        
        // If we can't determine type, show node properties as fallback
        if (cypherSchema.nodeProperties) {
          const seen = new Set<string>();
          cypherSchema.nodeProperties.forEach((prop) => {
            if (!seen.has(prop)) {
              seen.add(prop);
              completionItems.push({
                label: prop,
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: prop,
                detail: 'property',
                documentation: `Property: ${prop}`,
                sortText: '0' + prop,
              });
            }
          });
        }
        
        // Cache and return
        completionCache.key = completionKey;
        completionCache.items = completionItems;
        return completionItems;
      }
    }

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

    // Cache and return
    completionCache.key = completionKey;
    completionCache.items = completionItems;
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
