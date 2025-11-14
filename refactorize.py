#!/usr/bin/env python3
"""
refactorize.py - Automated Tool Standardization System

Refactors Orchestrate tools to match the gold standard structure from outline_editor.py
Ensures execution_hub compatibility and eliminates common bugs.

Usage:
    python refactorize.py tools/system_settings.py
    python refactorize.py tools/system_settings.py --validate-only
    python refactorize.py tools/*.py
"""

import ast
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ToolRefactorizer:
    def __init__(self, gold_standard_path: str, repo_root: str):
        self.gold_standard_path = Path(gold_standard_path)
        self.repo_root = Path(repo_root)
        self.gold_standard_main = None
        self._extract_gold_standard()

    def _extract_gold_standard(self):
        """Extract the main() function structure from gold standard"""
        with open(self.gold_standard_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'main':
                self.gold_standard_main = ast.get_source_segment(content, node)
                break

    def parse_tool(self, tool_path: Path) -> Dict[str, Any]:
        """Parse tool and extract structure"""
        with open(tool_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)

        # Extract imports
        imports = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.get_source_segment(content, node))

        # Extract action functions (public functions, not main, not execute_action)
        actions = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Skip private functions, main, and execute_action
                if node.name.startswith('_'):
                    continue
                if node.name in ['main', 'execute_action']:
                    continue

                # Extract function source
                func_source = ast.get_source_segment(content, node)
                actions[node.name] = {
                    'source': func_source,
                    'params': [arg.arg for arg in node.args.args],
                    'has_docstring': ast.get_docstring(node) is not None
                }

        # Extract ACTIONS dict if exists
        actions_dict = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'ACTIONS':
                        try:
                            actions_dict_source = ast.get_source_segment(content, node)
                            # Parse the keys
                            if isinstance(node.value, ast.Dict):
                                actions_dict = [k.s if isinstance(k, ast.Str) else k.value
                                              for k in node.value.keys if k]
                        except:
                            pass

        # Extract module-level constants/globals
        globals_code = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                # Extract path constants like BASE_DIR, CREDENTIALS_FILE
                # Skip ACTIONS dict - refactored main() replaces it
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == 'ACTIONS':
                            continue  # Skip ACTIONS dict
                        if target.id.isupper() or target.id.endswith('_DIR') or target.id.endswith('_FILE'):
                            globals_code.append(ast.get_source_segment(content, node))

        return {
            'imports': imports,
            'actions': actions,
            'actions_dict': actions_dict,
            'globals': globals_code,
            'content': content
        }

    def load_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Load tool schema from system_settings.ndjson"""
        schema_file = self.repo_root / "system_settings.ndjson"

        if not schema_file.exists():
            return None

        with open(schema_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get('tool') == tool_name:
                    return entry

        return None

    def validate_tool(self, tool_path: Path, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool against schema and structural requirements"""
        tool_name = tool_path.stem
        schema = self.load_schema(tool_name)

        issues = {
            'missing_in_code': [],
            'missing_in_schema': [],
            'structural': [],
            'path_issues': []
        }

        # Check schema alignment
        if schema and 'actions' in schema:
            schema_actions = set(schema['actions'].keys())
            code_actions = set(parsed['actions'].keys())

            issues['missing_in_code'] = list(schema_actions - code_actions)
            issues['missing_in_schema'] = list(code_actions - schema_actions)

        # Check for structural issues
        if not parsed['actions']:
            issues['structural'].append("No action functions found")

        # Check for path bugs in globals
        for global_line in parsed['globals']:
            if 'os.path.join(BASE_DIR, "tools")' in global_line:
                issues['path_issues'].append("Potential double /tools/tools nesting in path")
            if 'TOOLS_DIR' in global_line and 'credentials.json' in global_line:
                issues['path_issues'].append("credentials.json may use incorrect path")

        # Check main() function
        has_main = 'def main():' in parsed['content']
        if not has_main:
            issues['structural'].append("Missing main() function")

        return issues

    def generate_refactored_code(self, tool_path: Path, parsed: Dict[str, Any]) -> str:
        """Generate refactored tool code using gold standard structure"""
        tool_name = tool_path.stem

        # Build refactored code
        lines = []

        # Shebang
        lines.append("#!/usr/bin/env python3")

        # Module docstring
        lines.append(f'"""')
        lines.append(f'{tool_name.replace("_", " ").title()}')
        lines.append("")
        lines.append("Auto-refactored by refactorize.py to match gold standard structure.")
        lines.append('"""')
        lines.append("")

        # Imports (standardized)
        stdlib_imports = []
        thirdparty_imports = []
        local_imports = []

        for imp in parsed['imports']:
            if any(x in imp for x in ['json', 'sys', 'os', 'argparse', 'pathlib', 'subprocess']):
                stdlib_imports.append(imp)
            elif 'from system_settings import' in imp or 'from .' in imp:
                local_imports.append(imp)
            else:
                thirdparty_imports.append(imp)

        # Ensure required imports
        required = ['import json', 'import sys', 'import os']
        for req in required:
            if not any(req in imp for imp in stdlib_imports):
                stdlib_imports.insert(0, req)

        for imp in stdlib_imports:
            lines.append(imp)
        if thirdparty_imports:
            lines.append("")
            for imp in thirdparty_imports:
                lines.append(imp)
        if local_imports:
            lines.append("")
            for imp in local_imports:
                lines.append(imp)

        lines.append("")
        lines.append("")

        # Globals/constants - FIX PATH BUGS AUTOMATICALLY
        if parsed['globals']:
            for global_line in parsed['globals']:
                # Fix double tools nesting
                if 'TOOLS_DIR = os.path.join(BASE_DIR, "tools")' in global_line:
                    lines.append('TOOLS_DIR = BASE_DIR  # Fixed: was creating /tools/tools')
                elif 'CREDENTIALS_FILE = os.path.join(TOOLS_DIR, "credentials.json")' in global_line:
                    lines.append('CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")  # Fixed path')
                else:
                    lines.append(global_line)
            lines.append("")
            lines.append("")

        # Action functions
        for action_name, action_data in parsed['actions'].items():
            lines.append(action_data['source'])
            lines.append("")
            lines.append("")

        # Generate standardized main() function
        lines.append("def main():")
        lines.append("    import argparse")
        lines.append("    import json")
        lines.append("")
        lines.append("    parser = argparse.ArgumentParser()")
        lines.append("    parser.add_argument('action')")
        lines.append("    parser.add_argument('--params')")
        lines.append("    args = parser.parse_args()")
        lines.append("    params = json.loads(args.params) if args.params else {}")
        lines.append("")

        # Build if/elif chain
        action_names = sorted(parsed['actions'].keys())
        for i, action_name in enumerate(action_names):
            action_data = parsed['actions'][action_name]

            # Determine how to call the function
            if len(action_data['params']) == 1 and action_data['params'][0] == 'params':
                call = f"{action_name}(params)"
            elif len(action_data['params']) == 0:
                call = f"{action_name}()"
            else:
                # Unpack params as kwargs
                call = f"{action_name}(**params)"

            if i == 0:
                lines.append(f"    if args.action == '{action_name}':")
            else:
                lines.append(f"    elif args.action == '{action_name}':")
            lines.append(f"        result = {call}")

        # Else clause
        lines.append("    else:")
        lines.append("        result = {'status': 'error', 'message': f'Unknown action {args.action}'}")
        lines.append("")
        lines.append("    print(json.dumps(result, indent=2))")
        lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    main()")

        return '\n'.join(lines)

    def refactor_tool(self, tool_path: Path, validate_only: bool = False) -> Dict[str, Any]:
        """Refactor a single tool"""
        print(f"\n{Colors.BLUE}Refactoring: {tool_path.name}{Colors.END}")

        # Parse
        parsed = self.parse_tool(tool_path)
        print(f"  Found {len(parsed['actions'])} action functions")

        # Validate
        issues = self.validate_tool(tool_path, parsed)

        if issues['missing_in_code']:
            print(f"  {Colors.YELLOW}⚠ Missing implementations:{Colors.END} {', '.join(issues['missing_in_code'])}")
        if issues['missing_in_schema']:
            print(f"  {Colors.YELLOW}⚠ Undocumented actions:{Colors.END} {', '.join(issues['missing_in_schema'])}")
        if issues['path_issues']:
            for issue in issues['path_issues']:
                print(f"  {Colors.RED}✗ Path bug:{Colors.END} {issue}")
        if issues['structural']:
            for issue in issues['structural']:
                print(f"  {Colors.RED}✗ Structural:{Colors.END} {issue}")

        if validate_only:
            return {'status': 'validated', 'issues': issues}

        # Generate refactored code
        refactored_code = self.generate_refactored_code(tool_path, parsed)

        # Write to _refactored.py
        output_path = tool_path.parent / f"{tool_path.stem}_refactored.py"
        with open(output_path, 'w') as f:
            f.write(refactored_code)

        print(f"  {Colors.GREEN}✓ Written to:{Colors.END} {output_path}")

        return {
            'status': 'success',
            'output': str(output_path),
            'issues': issues,
            'actions_count': len(parsed['actions'])
        }


def main():
    parser = argparse.ArgumentParser(description='Refactorize Orchestrate tools to gold standard')
    parser.add_argument('tools', nargs='+', help='Tool files to refactor')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not generate output')
    parser.add_argument('--gold-standard',
                       default='/Users/srinivas/Orchestrate Github/orchestrate-jarvis/tools/outline_editor.py',
                       help='Path to gold standard tool')
    parser.add_argument('--repo',
                       default='/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit',
                       help='Repo root path')

    args = parser.parse_args()

    refactorizer = ToolRefactorizer(args.gold_standard, args.repo)

    print(f"{Colors.BOLD}Tool Refactorization System{Colors.END}")
    print(f"Gold Standard: {args.gold_standard}")
    print(f"Repo: {args.repo}\n")

    results = []
    for tool_pattern in args.tools:
        # Handle glob patterns
        from glob import glob
        tool_files = glob(tool_pattern)

        for tool_file in tool_files:
            tool_path = Path(tool_file)
            if not tool_path.exists():
                print(f"{Colors.RED}✗ Not found:{Colors.END} {tool_file}")
                continue

            if tool_path.name.startswith('_'):
                continue

            result = refactorizer.refactor_tool(tool_path, args.validate_only)
            results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"{Colors.BOLD}REFACTORIZATION SUMMARY{Colors.END}")
    print(f"{'='*60}\n")

    total = len(results)
    success = sum(1 for r in results if r['status'] == 'success')

    print(f"Total Tools:    {total}")
    print(f"{Colors.GREEN}Refactored:     {success}{Colors.END}")

    if not args.validate_only:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ REFACTORIZATION COMPLETE{Colors.END}")
        print(f"\nReview *_refactored.py files, then:")
        print(f"  mv tools/system_settings_refactored.py tools/system_settings.py")


if __name__ == '__main__':
    main()
