# CodeEditor Plugin Architecture

## Overview

The `CodeEditor` component uses a plugin-based architecture to support multiple query languages (SQL, Cypher, etc.) with minimal code duplication. Each language implements the `LanguagePlugin` interface to provide custom autocomplete, validation, and schema integration.

## Architecture

```
studio/src/components/common/
├── CodeEditor.tsx                    # Core editor component
├── languages/
│   ├── LanguagePlugin.ts            # Plugin interface
│   ├── index.ts                     # Plugin registry
│   ├── sql/
│   │   ├── SQLLanguagePlugin.ts     # SQL implementation
│   │   └── sqlKeywords.ts           # SQL keywords
│   └── cypher/
│       ├── CypherLanguagePlugin.ts  # Cypher implementation
│       └── cypherKeywords.ts        # Cypher keywords
```

## Usage

### SQL Query Editor

```typescript
<CodeEditor
  language="sql"
  value={query}
  onChange={setQuery}
  height={300}
  schemaEndpoint="http://localhost:8771/api/v1/operations/databases/libsql/schema"
/>
```

### Cypher Query Editor

```typescript
<CodeEditor
  language="cypher"
  value={query}
  onChange={setQuery}
  height={300}
  schemaEndpoint="http://localhost:8771/api/v1/knowledge-graph/schema"
/>
```

## How It Works

### 1. Schema Fetching

When `schemaEndpoint` is provided:
1. CodeEditor fetches raw schema from the endpoint
2. Language plugin transforms it into a typed schema
3. Schema is used for autocomplete and validation

### 2. Autocomplete

When user types:
1. Monaco triggers completion provider
2. Plugin receives context (cursor position, text, etc.)
3. Plugin returns completion items:
   - **Static**: Keywords, functions (from plugin)
   - **Dynamic**: Tables, columns, nodes, relationships (from schema)

### 3. Validation

On every code change:
1. Plugin validates the code
2. Returns errors/warnings with positions
3. Monaco displays squiggly lines and error messages

## Plugin Interface

```typescript
interface LanguagePlugin {
  readonly languageId: string;
  readonly triggerCharacters: string[];
  
  transformSchema(rawSchema: any): CompletionSchema;
  
  provideCompletions(
    context: CompletionContext,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): CompletionItem[];
  
  validateCode(
    code: string,
    schema: CompletionSchema | null,
    monaco: typeof monacoType
  ): ValidationError[];
}
```

## Adding a New Language

1. **Create plugin file**: `languages/mylang/MyLangLanguagePlugin.ts`
2. **Implement interface**: Extend `LanguagePlugin`
3. **Register plugin**: Add to `languages/index.ts`
4. **Use in component**: `<CodeEditor language="mylang" ... />`

Example:

```typescript
export class MyLangLanguagePlugin implements LanguagePlugin {
  readonly languageId = 'mylang';
  readonly triggerCharacters = ['.', ' '];

  transformSchema(rawSchema: any): CompletionSchema {
    // Transform API response into your schema format
    return { ... };
  }

  provideCompletions(context, schema, monaco): CompletionItem[] {
    // Return keywords + schema-based completions
    return [...];
  }

  validateCode(code, schema, monaco): ValidationError[] {
    // Validate syntax and semantics
    return [...];
  }
}
```

## Benefits

✅ **Zero code duplication** - Language logic is isolated in plugins  
✅ **Easy to extend** - Add new languages without modifying core editor  
✅ **Clean separation** - Editor UI vs language-specific logic  
✅ **Type-safe** - TypeScript interfaces ensure consistency  
✅ **Testable** - Each plugin can be unit tested independently  
✅ **Reusable** - Same editor component for all query languages

## Current Plugins

### SQL Plugin
- **Keywords**: SELECT, FROM, WHERE, JOIN, etc.
- **Functions**: COUNT, SUM, AVG, etc.
- **Schema**: Tables and columns from LibSQL database
- **Validation**: Forbidden operations (DROP, TRUNCATE), incomplete queries

### Cypher Plugin
- **Keywords**: MATCH, CREATE, RETURN, WHERE, etc.
- **Functions**: count, collect, toString, etc.
- **Schema**: Node labels, relationship types, properties
- **Validation**: Forbidden operations, incomplete queries, unbalanced parentheses

## Monaco Configuration

The editor is configured for offline use:
- Monaco assets loaded from `/public/monaco-editor/`
- No CDN dependencies
- Automatic asset copying via npm scripts
- See `MONACO_SETUP.md` for details
