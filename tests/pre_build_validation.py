#!/usr/bin/env python3
"""
Pre-Build Validation Suite

Tests all core tools in the repo BEFORE building Docker image.
Catches bugs like:
- Undefined variables (action vs args.action)
- Wrong file paths (double /tools/tools)
- Missing ACTIONS registry entries
- Invalid JSON in ACTIONS

Run this before every Docker build to prevent shipping broken tools.

Usage:
    python3 tests/pre_build_validation.py
    python3 tests/pre_build_validation.py --tool system_settings
"""

import os
import sys
import json
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Any


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class PreBuildValidator:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.tools_dir = self.repo_root / "tools"
        self.results = []

    def test_tool_imports(self) -> List[Dict[str, Any]]:
        """Test that all tool files can be imported without errors"""
        print(f"\n{Colors.BOLD}Testing Tool Imports{Colors.END}")
        results = []

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            test = {
                'test': f'import_{tool_file.stem}',
                'file': str(tool_file),
                'status': 'FAIL',
                'error': None
            }

            try:
                spec = importlib.util.spec_from_file_location(tool_file.stem, tool_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                test['status'] = 'PASS'
                print(f"  {Colors.GREEN}✓{Colors.END} {tool_file.name}")

            except Exception as e:
                test['error'] = str(e)
                print(f"  {Colors.RED}✗{Colors.END} {tool_file.name}: {e}")

            results.append(test)

        return results

    def test_action_registries(self) -> List[Dict[str, Any]]:
        """Test that all tools have valid ACTIONS dictionaries"""
        print(f"\n{Colors.BOLD}Testing ACTIONS Registries{Colors.END}")
        results = []

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            test = {
                'test': f'actions_{tool_file.stem}',
                'file': str(tool_file),
                'status': 'FAIL',
                'error': None,
                'actions_count': 0
            }

            try:
                spec = importlib.util.spec_from_file_location(tool_file.stem, tool_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, 'ACTIONS'):
                    actions = module.ACTIONS
                    if isinstance(actions, dict):
                        test['actions_count'] = len(actions)
                        test['status'] = 'PASS'
                        print(f"  {Colors.GREEN}✓{Colors.END} {tool_file.name}: {len(actions)} actions")
                    else:
                        test['error'] = "ACTIONS is not a dict"
                        print(f"  {Colors.RED}✗{Colors.END} {tool_file.name}: ACTIONS not a dict")
                else:
                    test['status'] = 'SKIP'
                    print(f"  {Colors.YELLOW}⊘{Colors.END} {tool_file.name}: No ACTIONS dict")

            except Exception as e:
                test['error'] = str(e)
                print(f"  {Colors.RED}✗{Colors.END} {tool_file.name}: {e}")

            results.append(test)

        return results

    def test_cli_execution(self) -> List[Dict[str, Any]]:
        """Test that tools can be executed via CLI without crashes"""
        print(f"\n{Colors.BOLD}Testing CLI Execution{Colors.END}")
        results = []

        # Test tools with known safe actions
        test_cases = [
            {
                'tool': 'system_settings.py',
                'action': 'list_tools',
                'params': '{}'
            },
            {
                'tool': 'json_manager.py',
                'action': 'list_json_files',
                'params': '{}'
            },
        ]

        for case in test_cases:
            test = {
                'test': f"cli_{case['tool']}_{case['action']}",
                'tool': case['tool'],
                'action': case['action'],
                'status': 'FAIL',
                'error': None
            }

            tool_path = self.tools_dir / case['tool']

            try:
                result = subprocess.run(
                    ['python3', str(tool_path), case['action'], '--params', case['params']],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    # Try to parse output as JSON
                    try:
                        output = json.loads(result.stdout)
                        test['status'] = 'PASS'
                        print(f"  {Colors.GREEN}✓{Colors.END} {case['tool']} {case['action']}")
                    except json.JSONDecodeError:
                        test['error'] = "Output not valid JSON"
                        print(f"  {Colors.RED}✗{Colors.END} {case['tool']}: Invalid JSON output")
                else:
                    test['error'] = result.stderr
                    print(f"  {Colors.RED}✗{Colors.END} {case['tool']}: {result.stderr[:100]}")

            except subprocess.TimeoutExpired:
                test['error'] = "Timeout"
                print(f"  {Colors.RED}✗{Colors.END} {case['tool']}: Timeout")
            except Exception as e:
                test['error'] = str(e)
                print(f"  {Colors.RED}✗{Colors.END} {case['tool']}: {e}")

            results.append(test)

        return results

    def test_path_bugs(self) -> List[Dict[str, Any]]:
        """Check for common path bugs like double nesting"""
        print(f"\n{Colors.BOLD}Testing Path Definitions{Colors.END}")
        results = []

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            test = {
                'test': f'paths_{tool_file.stem}',
                'file': str(tool_file),
                'status': 'PASS',
                'issues': []
            }

            with open(tool_file, 'r') as f:
                content = f.read()

            # Check for common path bugs
            if 'os.path.join(BASE_DIR, "tools")' in content and tool_file.parent.name == 'tools':
                test['status'] = 'WARN'
                test['issues'].append("Potential double /tools/tools nesting")

            if 'os.path.join(TOOLS_DIR, "credentials.json")' in content:
                if 'TOOLS_DIR = os.path.join(BASE_DIR, "tools")' in content:
                    test['status'] = 'WARN'
                    test['issues'].append("credentials.json path may be nested incorrectly")

            if test['status'] == 'WARN':
                print(f"  {Colors.YELLOW}⚠{Colors.END} {tool_file.name}: {', '.join(test['issues'])}")
            else:
                print(f"  {Colors.GREEN}✓{Colors.END} {tool_file.name}")

            results.append(test)

        return results

    def test_variable_references(self) -> List[Dict[str, Any]]:
        """Check for undefined variable bugs like 'action' vs 'args.action'"""
        print(f"\n{Colors.BOLD}Testing Variable References{Colors.END}")
        results = []

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            test = {
                'test': f'vars_{tool_file.stem}',
                'file': str(tool_file),
                'status': 'PASS',
                'issues': []
            }

            with open(tool_file, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Check for ACTIONS[action] when args.action exists
                if 'ACTIONS[action]' in line and 'args.action' in ''.join(lines):
                    test['status'] = 'FAIL'
                    test['issues'].append(f"Line {i}: Using 'action' instead of 'args.action'")

            if test['status'] == 'FAIL':
                print(f"  {Colors.RED}✗{Colors.END} {tool_file.name}:")
                for issue in test['issues']:
                    print(f"    {issue}")
            else:
                print(f"  {Colors.GREEN}✓{Colors.END} {tool_file.name}")

            results.append(test)

        return results

    def run_all_tests(self) -> int:
        """Run all validation tests"""
        print(f"{Colors.BOLD}Pre-Build Validation Suite{Colors.END}")
        print(f"Repo: {self.repo_root}\n")

        all_results = []

        # Run test suites
        all_results.extend(self.test_tool_imports())
        all_results.extend(self.test_action_registries())
        all_results.extend(self.test_path_bugs())
        all_results.extend(self.test_variable_references())
        all_results.extend(self.test_cli_execution())

        # Summary
        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.END}")
        print(f"{'='*60}\n")

        total = len(all_results)
        passed = sum(1 for r in all_results if r['status'] == 'PASS')
        failed = sum(1 for r in all_results if r['status'] == 'FAIL')
        warnings = sum(1 for r in all_results if r['status'] == 'WARN')
        skipped = sum(1 for r in all_results if r['status'] == 'SKIP')

        print(f"Total Tests:    {total}")
        print(f"{Colors.GREEN}Passed:         {passed}{Colors.END}")
        print(f"{Colors.RED}Failed:         {failed}{Colors.END}")
        print(f"{Colors.YELLOW}Warnings:       {warnings}{Colors.END}")
        print(f"Skipped:        {skipped}")

        if failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ VALIDATION FAILED - DO NOT BUILD DOCKER IMAGE{Colors.END}")
            print(f"\nFailed tests:")
            for r in all_results:
                if r['status'] == 'FAIL':
                    print(f"  {Colors.RED}✗{Colors.END} {r['test']}")
                    if r.get('error'):
                        print(f"    {r['error']}")
                    if r.get('issues'):
                        for issue in r['issues']:
                            print(f"    {issue}")
            return 1
        elif warnings > 0:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  WARNINGS FOUND - REVIEW BEFORE BUILD{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ALL VALIDATION PASSED - SAFE TO BUILD{Colors.END}")
            return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Pre-build validation for OrchestrateOS tools')
    parser.add_argument('--repo', default='/Users/srinivas/Orchestrate Github/orchestrate-no-bullshit',
                       help='Path to repo root')

    args = parser.parse_args()

    validator = PreBuildValidator(args.repo)
    exit_code = validator.run_all_tests()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
