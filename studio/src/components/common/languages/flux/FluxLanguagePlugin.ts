/**
 * Flux Language Plugin
 * 
 * Provides Flux-specific autocomplete, validation, and schema integration for InfluxDB
 */

import type * as monacoType from 'monaco-editor';
import {
  LanguagePlugin,
  CompletionContext,
  CompletionItem,
  CompletionSchema,
  ValidationError,
} from '../LanguagePlugin';
import {
  FLUX_KEYWORDS,
  FLUX_FUNCTIONS,
  FLUX_FILTER_PREDICATES,
  FLUX_SNIPPETS,
} from './fluxKeywords';

interface FluxSchema {
  measurements?: string[];
  fields?: string[];
  tags?: string[];
}

export class FluxLanguagePlugin implements LanguagePlugin {
  readonly languageId = 'sql'; // Use 'sql' since Monaco doesn't have native Flux support
  readonly triggerCharacters = ['.', ' ', '(', '|', '>', '"', ':'];

  transformSchema(rawSchema: any): CompletionSchema {
    return {
      measurements: rawSchema.measurements || [],
      fields: rawSchema.fields || [],
      tags: rawSchema.tags || [],
    } as FluxSchema;
  }

  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[] {
    const completionItems: CompletionItem[] = [];
    const fluxSchema = schema as FluxSchema | null;
    const textBefore = context.textBeforeCursor.toLowerCase();
    const fullText = context.fullText.toLowerCase();

    console.log('[FluxPlugin] provideCompletions called:', {
      textBefore,
      textBeforeRaw: context.textBeforeCursor,
      cursorPosition: context.position,
    });

    // Detect if we're inside a function parameter context
    // More flexible patterns that handle various whitespace
    const insideBucketParam = /from\s*\(\s*bucket\s*:\s*[^)]*$/.test(textBefore) || 
                              /bucket\s*:\s*[^),]*$/.test(textBefore);
    const insideRangeParam = /range\s*\(\s*start\s*:\s*[^)]*$/.test(textBefore) ||
                             /start\s*:\s*[^),]*$/.test(textBefore);
    const insideFilterMeasurement = /r\._measurement\s*==\s*[^)]*$/.test(textBefore);
    const insideFilterField = /r\._field\s*==\s*[^)]*$/.test(textBefore);
    const afterPipe = /\|\>\s*$/.test(textBefore);

    console.log('[FluxPlugin] Context detection:', {
      insideBucketParam,
      insideRangeParam,
      insideFilterMeasurement,
      insideFilterField,
      afterPipe,
    });

    // Context-aware completions (prioritize these)
    if (insideBucketParam) {
      // Suggest common bucket names when inside bucket parameter
      ['aico_telemetry', 'metrics', 'logs'].forEach((bucket) => {
        completionItems.push({
          label: bucket,
          kind: monaco.languages.CompletionItemKind.Value,
          insertText: `"${bucket}"`,
          detail: 'bucket name',
          documentation: `InfluxDB bucket: ${bucket}`,
          sortText: '0' + bucket,
        });
      });
      return completionItems; // Return early with only bucket suggestions
    }

    if (insideRangeParam) {
      // Suggest common time ranges when inside range parameter
      ['-1h', '-6h', '-24h', '-7d', '-30d', '-90d'].forEach((range) => {
        completionItems.push({
          label: range,
          kind: monaco.languages.CompletionItemKind.Value,
          insertText: range,
          detail: 'time range',
          documentation: `Relative time: ${range}`,
          sortText: '0' + range,
        });
      });
      return completionItems; // Return early with only time range suggestions
    }

    if (insideFilterMeasurement) {
      // Suggest measurements when filtering by measurement
      if (fluxSchema?.measurements) {
        fluxSchema.measurements.forEach((measurement) => {
          completionItems.push({
            label: measurement,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: `"${measurement}"`,
            detail: 'measurement',
            documentation: `Measurement: ${measurement}`,
            sortText: '0' + measurement,
          });
        });
      } else {
        ['logs', 'api_request', 'model_inference', 'system_metrics'].forEach((measurement) => {
          completionItems.push({
            label: measurement,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: `"${measurement}"`,
            detail: 'measurement',
            documentation: `Measurement: ${measurement}`,
            sortText: '0' + measurement,
          });
        });
      }
      return completionItems;
    }

    if (insideFilterField) {
      // Suggest fields when filtering by field
      if (fluxSchema?.fields) {
        fluxSchema.fields.forEach((field) => {
          completionItems.push({
            label: field,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: `"${field}"`,
            detail: 'field',
            documentation: `Field: ${field}`,
            sortText: '0' + field,
          });
        });
      } else {
        ['cpu_percent', 'memory_percent', 'duration_ms', 'status_code'].forEach((field) => {
          completionItems.push({
            label: field,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: `"${field}"`,
            detail: 'field',
            documentation: `Field: ${field}`,
            sortText: '0' + field,
          });
        });
      }
      return completionItems;
    }

    // After pipe operator, prioritize common next functions
    if (afterPipe) {
      ['filter', 'map', 'group', 'aggregateWindow', 'limit', 'sort', 'yield'].forEach((func) => {
        completionItems.push({
          label: func,
          kind: monaco.languages.CompletionItemKind.Function,
          insertText: `${func}()`,
          detail: 'function',
          documentation: `Flux function: ${func}`,
          sortText: '0' + func,
        });
      });
    }

    // Add Flux keywords
    FLUX_KEYWORDS.forEach((keyword) => {
      completionItems.push({
        label: keyword,
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: keyword,
        detail: 'keyword',
        documentation: `Flux keyword: ${keyword}`,
        sortText: '1' + keyword,
      });
    });

    // Add Flux functions
    FLUX_FUNCTIONS.forEach((func) => {
      completionItems.push({
        label: func,
        kind: monaco.languages.CompletionItemKind.Function,
        insertText: `${func}()`,
        detail: 'function',
        documentation: `Flux function: ${func}`,
        sortText: '2' + func,
      });
    });

    // Add filter predicates (r._measurement, r._field, etc.)
    FLUX_FILTER_PREDICATES.forEach((predicate) => {
      completionItems.push({
        label: predicate,
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: predicate,
        detail: 'predicate',
        documentation: `Flux predicate: ${predicate}`,
        sortText: '3' + predicate,
      });
    });

    // Add snippets
    FLUX_SNIPPETS.forEach((snippet) => {
      completionItems.push({
        label: snippet.label,
        kind: monaco.languages.CompletionItemKind.Snippet,
        insertText: snippet.insertText,
        detail: snippet.detail,
        documentation: snippet.documentation,
        sortText: '4' + snippet.label,
      });
    });

    console.log('[FluxPlugin] Returning completion items:', completionItems.length);
    return completionItems;
  }

  validateCode(
    code: string,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): ValidationError[] {
    const errors: ValidationError[] = [];
    const lines = code.split('\n');

    lines.forEach((line, lineIndex) => {
      const lineNumber = lineIndex + 1;

      // Check for common Flux syntax errors
      
      // Missing pipe operator before function call
      if (/^\s*\w+\(/.test(line) && lineNumber > 1 && !lines[lineIndex - 1].includes('|>')) {
        const prevLine = lines[lineIndex - 1].trim();
        if (prevLine && !prevLine.startsWith('import') && !prevLine.includes('=')) {
          errors.push({
            severity: 'warning',
            startLine: lineNumber,
            startColumn: 1,
            endLine: lineNumber,
            endColumn: line.length + 1,
            message: 'Consider using pipe operator |> before this function',
          });
        }
      }

      // Unclosed parentheses
      const openParens = (line.match(/\(/g) || []).length;
      const closeParens = (line.match(/\)/g) || []).length;
      if (openParens > closeParens) {
        errors.push({
          severity: 'error',
          startLine: lineNumber,
          startColumn: 1,
          endLine: lineNumber,
          endColumn: line.length + 1,
          message: 'Unclosed parenthesis',
        });
      }

      // Missing quotes in filter predicates
      if (line.includes('r._measurement ==') || line.includes('r._field ==')) {
        const afterEquals = line.split('==')[1];
        if (afterEquals && !afterEquals.includes('"') && !afterEquals.includes("'")) {
          errors.push({
            severity: 'warning',
            startLine: lineNumber,
            startColumn: 1,
            endLine: lineNumber,
            endColumn: line.length + 1,
            message: 'String values should be quoted',
          });
        }
      }
    });

    return errors;
  }
}
