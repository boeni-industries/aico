# GQL Query Template Management

## Overview

GQL query templates provide pre-built Cypher queries for common knowledge graph operations. This document describes the complete lifecycle of template management from development to runtime, including editing capabilities in Studio.

## Architecture

### File Locations

```
Repository (Version Control):
├── backend/data/gql_query_templates.json          # Source of truth - default templates
└── backend/data/gql_query_templates.schema.json   # Template validation schema (future)

Runtime (OS-Specific, User-Editable):
└── ~/Library/Application Support/aico/data/gql_query_templates.json  # macOS
└── ~/.local/share/aico/data/gql_query_templates.json                 # Linux
└── %APPDATA%/aico/data/gql_query_templates.json                      # Windows
```

### Design Principles

1. **Version-controlled defaults**: Repository contains default templates that ship with AICO
2. **User customization**: Runtime templates can be edited via Studio UI or CLI
3. **Deployment safety**: Fresh deployments automatically get latest templates
4. **Update flexibility**: Users can sync new templates while preserving customizations

## Template Lifecycle

### Phase 1: Development Time

**Who**: Developers  
**Where**: `backend/data/gql_query_templates.json` in repository  
**Actions**:
- Edit default templates
- Add new templates
- Commit changes to version control
- Templates ship with next release

### Phase 2: Deployment/Setup Time

**Who**: System administrators, end users  
**Where**: CLI commands  
**Actions**:

#### Initial Setup
```bash
# Initialize AICO configuration (includes templates)
aico config init

# This copies templates from repo to OS-specific directory:
# backend/data/gql_query_templates.json → ~/Library/Application Support/aico/data/
```

#### Update Existing Installation
```bash
# Merge new templates, preserve user customizations (default)
aico config sync-templates

# Force overwrite with repo defaults (loses customizations)
aico config sync-templates --force

# Only copy if templates don't exist
aico config sync-templates --no-merge
```

**Behavior**:
- `aico config init`: Copies templates only if they don't exist (preserves user edits)
- `aico config init --force`: Overwrites everything including templates
- `aico config sync-templates`: Intelligent merge - adds new templates, keeps user edits
- `aico config sync-templates --force`: Complete overwrite with repo defaults

### Phase 3: Runtime

**Who**: Backend API  
**Where**: `GET /kg/query-templates` endpoint  
**Actions**:
- Reads templates from OS-specific directory
- Returns templates to Studio UI
- No fallback to repo defaults (requires explicit initialization)

**Error Handling**:
If templates not found:
```json
{
  "status": 503,
  "detail": "Query templates not initialized. Run 'aico config init' to set up templates."
}
```

### Phase 4: User Customization (Studio)

**Who**: End users via Studio UI  
**Where**: Studio template editor (future), `PUT /kg/query-templates` endpoint  
**Actions**:
- Users can edit templates in Studio UI
- Changes persist to OS-specific directory
- Edits survive backend restarts
- User customizations preserved during `sync-templates` (unless `--force`)

## API Endpoints

### GET /kg/query-templates

Retrieve current query templates.

**Response**:
```json
{
  "templates": [
    {
      "id": "all-nodes",
      "title": "All Nodes",
      "description": "Show all nodes with ALL their properties",
      "category": "exploration",
      "query": "MATCH (n)\nRETURN n.id, n.label, n.name\nLIMIT 100",
      "tags": ["basic", "exploration"]
    }
  ]
}
```

### PUT /kg/query-templates

Update query templates (Studio editor).

**Request**:
```json
{
  "templates": [
    {
      "id": "custom-query",
      "title": "My Custom Query",
      "description": "Custom query description",
      "category": "exploration",
      "query": "MATCH (n) RETURN n LIMIT 10",
      "tags": ["custom"]
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "message": "Updated 1 query templates",
  "templates_count": 1,
  "path": "/Users/username/Library/Application Support/aico/data/gql_query_templates.json"
}
```

**Validation**:
- All templates must have required fields: `id`, `title`, `description`, `category`, `query`, `tags`
- `templates` must be an array
- Each template must be a valid object

## CLI Commands

### aico config init

Initialize AICO configuration including templates.

```bash
# First-time setup
aico config init

# Force overwrite existing templates
aico config init --force
```

**Behavior**:
- Creates OS-specific data directory
- Copies default templates from repo if they don't exist
- With `--force`: Overwrites existing templates

### aico config sync-templates

Sync templates from repository defaults.

```bash
# Default: Merge new templates, preserve user edits
aico config sync-templates

# Force complete overwrite (loses customizations)
aico config sync-templates --force

# Only initialize if missing
aico config sync-templates --no-merge
```

**Merge Logic** (default):
1. Load templates from repo (source)
2. Load templates from OS directory (target)
3. For each repo template:
   - If template ID doesn't exist in target: **Add it**
   - If template ID exists in target: **Preserve user version**
4. Write merged templates back to OS directory

**Output Example**:
```
✨ Syncing GQL Query Templates

✓ Merged templates successfully
  • Added: 2 new templates
  • Preserved: 8 existing templates
  • Total: 10 templates

• Template location: ~/Library/Application Support/aico/data/gql_query_templates.json
```

## Template Structure

### Required Fields

```typescript
interface QueryTemplate {
  id: string;              // Unique identifier (kebab-case)
  title: string;           // Display name
  description: string;     // User-facing description
  category: string;        // "exploration" | "analysis" | "temporal" | "relationships"
  query: string;           // Cypher query (multiline supported)
  tags: string[];          // Search/filter tags
}
```

### Example Template

```json
{
  "id": "recent-changes",
  "title": "Recent Changes",
  "description": "Show nodes created or updated in the last 7 days",
  "category": "temporal",
  "query": "MATCH (n)\nWHERE n.created_at > \"2024-12-24\"\n   OR n.updated_at > \"2024-12-24\"\nRETURN n.label, n.name, n.created_at, n.updated_at\nORDER BY n.updated_at DESC\nLIMIT 20",
  "tags": ["temporal", "recent", "activity"]
}
```

## Workflows

### Fresh Deployment

```bash
# 1. Clone repository
git clone <repo>

# 2. Initialize AICO
aico config init

# 3. Start backend
aico backend start

# 4. Templates available at runtime
curl http://localhost:8770/kg/query-templates
```

### Update Templates After Repo Changes

```bash
# 1. Pull latest changes
git pull

# 2. Sync templates (merge mode)
aico config sync-templates

# Output shows what was added vs preserved
# User customizations are kept
```

### Reset to Defaults

```bash
# Overwrite all customizations with repo defaults
aico config sync-templates --force
```

### Studio Template Editing (Future)

1. User opens Studio → Knowledge Graph → Query Templates
2. Clicks "Edit Template" on existing template
3. Modifies query, description, etc.
4. Clicks "Save"
5. Frontend calls `PUT /kg/query-templates`
6. Backend validates and persists to OS directory
7. Changes immediately available (no backend restart needed)

## Best Practices

### For Developers

1. **Always test templates** with GrandCypher before committing
2. **Use descriptive IDs** (kebab-case): `recent-changes`, `skill-gaps`
3. **Add helpful descriptions** explaining what the query does
4. **Tag appropriately** for better discoverability
5. **Keep queries simple** - avoid unsupported Cypher features

### For System Administrators

1. **Run `aico config init`** during deployment setup
2. **Use `sync-templates`** to get updates without losing customizations
3. **Backup custom templates** before using `--force`
4. **Document custom templates** for team members

### For End Users

1. **Customize freely** - your edits are preserved during updates
2. **Use Studio editor** (when available) for safe editing
3. **Test queries** before saving
4. **Sync periodically** to get new templates from updates

## Troubleshooting

### Templates Not Found (503 Error)

**Symptom**: API returns "Query templates not initialized"

**Solution**:
```bash
aico config init
```

### Templates Reset After Update

**Cause**: Used `aico config init --force` or `sync-templates --force`

**Solution**: Restore from backup or re-create customizations

### Invalid Template JSON

**Symptom**: API returns "Query templates file is malformed"

**Solution**:
```bash
# Reset to defaults
aico config sync-templates --force

# Or manually fix JSON at:
# ~/Library/Application Support/aico/data/gql_query_templates.json
```

### New Templates Not Appearing

**Symptom**: Repo has new templates but they don't show in Studio

**Solution**:
```bash
# Merge new templates
aico config sync-templates
```

## Future Enhancements

1. **Template Validation Schema**: JSON schema for template structure validation
2. **Studio Template Editor**: Visual editor for creating/editing templates
3. **Template Sharing**: Export/import templates between users
4. **Template Versioning**: Track template changes over time
5. **Template Testing**: Built-in query validator in Studio
6. **Template Categories**: Better organization and filtering
7. **Template Permissions**: Role-based access to certain templates
