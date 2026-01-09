#!/usr/bin/env node

/**
 * Copy Monaco Editor files to public directory
 * This script runs automatically during:
 * - npm install (postinstall)
 * - npm start (prestart)
 * - npm run build (prebuild)
 * 
 * Ensures Monaco Editor works completely offline without CDN dependencies.
 */

const fs = require('fs');
const path = require('path');

const sourceDir = path.join(__dirname, '../node_modules/monaco-editor/min');
const targetDir = path.join(__dirname, '../public/monaco-editor/min');

console.log('\n🔧 Monaco Editor Setup');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

// Check if source exists
if (!fs.existsSync(sourceDir)) {
  console.error('❌ ERROR: monaco-editor not found in node_modules');
  console.error('   Run: npm install monaco-editor @monaco-editor/react');
  process.exit(1);
}

// Check if already copied and up to date
if (fs.existsSync(targetDir)) {
  const sourceStats = fs.statSync(sourceDir);
  const targetStats = fs.statSync(targetDir);
  
  // If target is newer than source, skip copy
  if (targetStats.mtime >= sourceStats.mtime) {
    console.log('✓ Monaco Editor files already up to date');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    process.exit(0);
  }
  
  console.log('🗑️  Removing outdated Monaco Editor files...');
  fs.rmSync(path.dirname(targetDir), { recursive: true, force: true });
}

// Create target directory
console.log('📁 Creating target directory...');
fs.mkdirSync(targetDir, { recursive: true });

// Copy files
console.log('📦 Copying Monaco Editor files from node_modules...');
const startTime = Date.now();
copyRecursiveSync(sourceDir, targetDir);
const duration = Date.now() - startTime;

console.log(`✓ Monaco Editor files copied successfully (${duration}ms)`);
console.log('  Location: public/monaco-editor/min/');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

function copyRecursiveSync(src, dest) {
  const exists = fs.existsSync(src);
  const stats = exists && fs.statSync(src);
  const isDirectory = exists && stats.isDirectory();
  
  if (isDirectory) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest);
    }
    fs.readdirSync(src).forEach(childItemName => {
      copyRecursiveSync(
        path.join(src, childItemName),
        path.join(dest, childItemName)
      );
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}
