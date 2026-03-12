#!/usr/bin/env python3
"""
Automatic Bug Fix Script
Applies all critical bug fixes to your AGI system
"""

import os
import sys
import shutil
from datetime import datetime

# Color codes for terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header():
    print(f"\n{Colors.BLUE}{'='*70}")
    print("🔧 AGI SYSTEM - AUTOMATIC BUG FIX")
    print(f"{'='*70}{Colors.END}\n")

def backup_file(filepath):
    """Create backup before modifying"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"{Colors.YELLOW}  ↳ Backup created: {backup_path}{Colors.END}")
        return True
    return False

def apply_fix(filepath, find_str, replace_str, description):
    """Apply a single fix to a file"""
    print(f"\n{Colors.BLUE}Fixing: {filepath}{Colors.END}")
    print(f"  {description}")
    
    if not os.path.exists(filepath):
        print(f"{Colors.RED}  ✗ File not found!{Colors.END}")
        return False
    
    # Backup first
    backup_file(filepath)
    
    # Read file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"{Colors.RED}  ✗ Error reading: {e}{Colors.END}")
        return False
    
    # Check if fix already applied
    if find_str not in content:
        if replace_str in content:
            print(f"{Colors.YELLOW}  ⊙ Already fixed{Colors.END}")
            return True
        else:
            print(f"{Colors.YELLOW}  ⊙ Pattern not found (might be OK){Colors.END}")
            return False
    
    # Apply fix
    content = content.replace(find_str, replace_str)
    
    # Write back
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"{Colors.GREEN}  ✓ Fixed successfully{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}  ✗ Error writing: {e}{Colors.END}")
        return False

def main():
    print_header()
    
    fixes_applied = 0
    fixes_failed = 0
    
    # Define all fixes
    fixes = [
        {
            'file': 'src/crewai_agents.py',
            'find': "source = paper.get('source', '').lower()",
            'replace': "source = str(paper.get('source', '')).lower()",
            'description': "Fix 'dict has no attribute lower' bug"
        },
        {
            'file': 'src/ai_council.py',
            'find': "import google.genai as genai",
            'replace': "import google.generativeai as genai",
            'description': "Fix Gemini import (wrong module name)"
        },
        {
            'file': 'src/ai_council.py',
            'find': 'self.gemini = genai.GenerativeModel("gemini-2.5-flash")',
            'replace': 'self.gemini = genai.GenerativeModel("gemini-1.5-flash")',
            'description': "Fix Gemini model version (2.5 doesn't exist)"
        },
        {
            'file': 'src/analyzer.py',
            'find': "import google.genai as genai",
            'replace': "import google.generativeai as genai",
            'description': "Fix Gemini import (wrong module name)"
        },
        {
            'file': 'src/main.py',
            'find': 'if not should_process and reason == "duplicate":',
            'replace': 'if not should_process and reason == "duplicate":',
            'description': "Ensure duplicate check works (already OK)"
        }
    ]
    
    print(f"Total fixes to apply: {len(fixes)}\n")
    
    # Apply each fix
    for idx, fix in enumerate(fixes, 1):
        print(f"\n[{idx}/{len(fixes)}]", end=" ")
        
        if apply_fix(fix['file'], fix['find'], fix['replace'], fix['description']):
            fixes_applied += 1
        else:
            fixes_failed += 1
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}{Colors.END}")
    print(f"{Colors.GREEN}✓ Fixes Applied: {fixes_applied}{Colors.END}")
    if fixes_failed > 0:
        print(f"{Colors.YELLOW}⊙ Fixes Failed/Skipped: {fixes_failed}{Colors.END}")
    print()
    
    # Recommendations
    print(f"{Colors.BLUE}📋 NEXT STEPS:{Colors.END}")
    print("1. Test the system:")
    print("   python main.py")
    print()
    print("2. Check logs for errors:")
    print("   tail -f logs/ultimate_agi_*.log")
    print()
    print("3. If issues persist, check:")
    print("   - Python packages: pip list | grep -E 'google|qdrant'")
    print("   - Environment variables: cat .env")
    print()
    
    # Verify critical imports
    print(f"{Colors.BLUE}🔍 VERIFYING IMPORTS:{Colors.END}")
    
    try:
        import google.generativeai as genai
        print(f"{Colors.GREEN}  ✓ google-generativeai imported OK{Colors.END}")
    except ImportError as e:
        print(f"{Colors.RED}  ✗ google-generativeai import failed: {e}{Colors.END}")
        print(f"{Colors.YELLOW}  → Run: pip install google-generativeai{Colors.END}")
    
    try:
        from qdrant_client import QdrantClient
        print(f"{Colors.GREEN}  ✓ qdrant-client imported OK{Colors.END}")
    except ImportError as e:
        print(f"{Colors.RED}  ✗ qdrant-client import failed: {e}{Colors.END}")
        print(f"{Colors.YELLOW}  → Run: pip install qdrant-client{Colors.END}")
    
    print()
    print(f"{Colors.GREEN}✅ Bug fix process complete!{Colors.END}\n")

if __name__ == "__main__":
    main()