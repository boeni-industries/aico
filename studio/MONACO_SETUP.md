# Monaco Editor Setup

## Overview

This project uses Monaco Editor (the editor that powers VS Code) for the SQL Query Interface and other code editing features. Monaco is configured to run **completely offline** without any CDN dependencies.

## How It Works

Monaco Editor files are **automatically copied** from `node_modules` to `public/monaco-editor/` during:

1. **After `npm install`** - via `postinstall` script
2. **Before `npm start`** - via `prestart` script  
3. **Before `npm run build`** - via `prebuild` script

This ensures Monaco files are **always available** regardless of how the project is set up.

## Deployment Checklist

When deploying to a new environment:

```bash
# 1. Clone the repository
git clone <repo-url>
cd aico/studio

# 2. Install dependencies (Monaco files are copied automatically)
npm install

# 3. Start development server (Monaco files are verified/copied)
npm start

# OR build for production (Monaco files are verified/copied)
npm run build
```

## Troubleshooting

### Monaco Editor not loading?

Run the copy script manually:

```bash
cd studio
node scripts/copy-monaco.js
```

### Monaco files missing after git clone?

This is **normal** - Monaco files are in `.gitignore` and generated during `npm install`.

Just run:
```bash
npm install
```

### Want to verify Monaco is set up correctly?

Check that this directory exists and has files:
```bash
ls -la studio/public/monaco-editor/min/vs/
```

You should see files like `loader.js`, `editor/`, `base/`, etc.

## Technical Details

- **Source**: `node_modules/monaco-editor/min/`
- **Destination**: `public/monaco-editor/min/`
- **Copy Script**: `scripts/copy-monaco.js`
- **Loader Config**: `src/components/common/CodeEditor.tsx`

Monaco files are **NOT versioned** in git (they're build artifacts, not source code).

## Why This Approach?

1. **Offline-first**: No CDN dependencies, works without internet
2. **Automatic**: No manual setup steps required
3. **Deployment-safe**: Works in CI/CD, Docker, and all environments
4. **Clean git**: Monaco files (~10MB) not in version control
