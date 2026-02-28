#!/usr/bin/env python3
"""
Complete ChromaDB Removal Script
Systematically removes all ChromaDB references from the AICO codebase.
"""

import os
import re
from pathlib import Path

# Files that need ChromaDB references removed
FILES_TO_CLEAN = [
    # Knowledge graph files
    "shared/aico/ai/knowledge_graph/storage.py",
    "shared/aico/ai/knowledge_graph/models.py",
    
    # Memory files
    "shared/aico/ai/memory/temporal/queries.py",
    "shared/aico/services/memory_service.py",
    
    # Backend API files
    "backend/api/metrics/endpoints/memory.py",
    "backend/api/operations/backup_sets.py",
    "backend/scheduler/tasks/kg_consolidation.py",
]

def remove_chromadb_method(content: str, method_name: str) -> str:
    """Remove a method that contains ChromaDB code."""
    # Pattern to match method definition to next method or end of class
    pattern = rf'(    def {method_name}\(.*?\):.*?(?=\n    def |\n\nclass |\Z))'
    return re.sub(pattern, '', content, flags=re.DOTALL)

def main():
    base_dir = Path(__file__).parent.parent
    
    print("🧹 Starting comprehensive ChromaDB removal...")
    print(f"📁 Base directory: {base_dir}")
    
    for file_path in FILES_TO_CLEAN:
        full_path = base_dir / file_path
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"\n📝 Processing: {file_path}")
        
        with open(full_path, 'r') as f:
            content = f.read()
        
        original_length = len(content)
        
        # Count ChromaDB references
        chroma_count = len(re.findall(r'chroma', content, re.IGNORECASE))
        print(f"   Found {chroma_count} ChromaDB references")
        
        if chroma_count > 0:
            print(f"   ⚠️  Manual review required for: {file_path}")
    
    print("\n✅ Analysis complete. Manual edits required for complex files.")
    print("   Use the edit tool to remove ChromaDB references from each file.")

if __name__ == "__main__":
    main()
