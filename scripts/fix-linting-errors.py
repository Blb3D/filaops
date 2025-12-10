#!/usr/bin/env python3
"""
Script to fix common ruff linting errors automatically.

Fixes:
- E712: Boolean comparisons (== True/False -> .is_(True)/.is_(False))
- F401: Unused imports (comments them out with # noqa: F401 for review)
- F541: f-strings without placeholders
- E741: Ambiguous variable names (l -> line, e -> err)

Run from project root: python scripts/fix-linting-errors.py
"""
import re
import sys
from pathlib import Path

# Patterns to fix
PATTERNS = [
    # Boolean comparisons in SQLAlchemy filters
    (r'(\w+)\.active == True', r'\1.active.is_(True)'),
    (r'(\w+)\.is_active == True', r'\1.is_active.is_(True)'),
    (r'(\w+)\.revoked == False', r'\1.revoked.is_(False)'),
    (r'(\w+)\.revoked == True', r'\1.revoked.is_(True)'),
    (r'(\w+)\.is_template == True', r'\1.is_template.is_(True)'),
    (r'(\w+)\.is_raw_material == True', r'\1.is_raw_material.is_(True)'),
    (r'(\w+)\.is_customer_visible == True', r'\1.is_customer_visible.is_(True)'),
]

def fix_file(filepath: Path) -> int:
    """Fix linting errors in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return 0
    
    original_content = content
    fixes = 0
    
    # Apply pattern replacements
    for pattern, replacement in PATTERNS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            fixes += count
    
    # Only write if changes were made
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return fixes
        except Exception as e:
            print(f"Error writing {filepath}: {e}", file=sys.stderr)
            return 0
    
    return 0

def main():
    """Main function."""
    backend_path = Path('backend/app')
    if not backend_path.exists():
        print(f"Error: {backend_path} does not exist. Run from project root.", file=sys.stderr)
        sys.exit(1)
    
    total_fixes = 0
    files_fixed = 0
    
    # Find all Python files
    for py_file in backend_path.rglob('*.py'):
        fixes = fix_file(py_file)
        if fixes > 0:
            files_fixed += 1
            total_fixes += fixes
            try:
                rel_path = py_file.relative_to(Path.cwd())
            except ValueError:
                rel_path = py_file
            print(f"Fixed {fixes} issues in {rel_path}")
    
    print(f"\n[OK] Fixed {total_fixes} issues across {files_fixed} files")
    print("\n⚠️  Note: This script only fixes boolean comparisons.")
    print("   You still need to manually fix:")
    print("   - Unused imports (F401)")
    print("   - Bare except clauses (E722)")
    print("   - Module-level imports (E402)")

if __name__ == '__main__':
    main()

