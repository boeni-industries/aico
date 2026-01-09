/**
 * Language Plugin Registry
 * 
 * Central registry for all language plugins
 */

import { LanguagePlugin } from './LanguagePlugin';
import { SQLLanguagePlugin } from './sql/SQLLanguagePlugin';
import { CypherLanguagePlugin } from './cypher/CypherLanguagePlugin';

const plugins = new Map<string, LanguagePlugin>();

// Register available plugins
plugins.set('sql', new SQLLanguagePlugin());
plugins.set('cypher', new CypherLanguagePlugin());

/**
 * Get language plugin by language ID
 */
export function getLanguagePlugin(languageId: string): LanguagePlugin | undefined {
  return plugins.get(languageId);
}

/**
 * Check if a language is supported
 */
export function isLanguageSupported(languageId: string): boolean {
  return plugins.has(languageId);
}

/**
 * Get all supported language IDs
 */
export function getSupportedLanguages(): string[] {
  return Array.from(plugins.keys());
}

// Export types and plugins
export type { LanguagePlugin, CompletionContext, CompletionItem, CompletionSchema, ValidationError } from './LanguagePlugin';
export { SQLLanguagePlugin } from './sql/SQLLanguagePlugin';
export { CypherLanguagePlugin } from './cypher/CypherLanguagePlugin';
