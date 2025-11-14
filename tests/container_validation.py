#!/usr/bin/env python3
"""
Container Validation Suite

Runs INSIDE the Docker container after launch to validate:
- All file paths exist and are accessible
- Claude Code is installed and configured
- Schema injection hook is working
- Credentials system is functional
- All tools are executable via execution_hub
- System settings registry is valid
- Critical data directories have correct permissions

Usage (inside container):
    python3 /opt/orchestrate-core-runtime/tests/container_validation.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ContainerValidator:
    def __init__(self):
        self.runtime_dir = Path("/opt/orchestrate-core-runtime")
        self.data_dir = self.runtime_dir / "data"
        self.tools_dir = self.runtime_dir / "tools"
        self.claude_dir = Path.home() / ".claude"
        self.results = []

    def test_critical_paths(self) -> List[Dict[str, Any]]:
        """Validate all critical paths exist"""
        print(f"\n{Colors.BOLD}Testing Critical Paths{Colors.END}")

        critical_paths = [
            # Runtime directories
            (self.runtime_dir, "dir", "Runtime root"),
            (self.data_dir, "dir", "Data directory"),
            (self.tools_dir, "dir", "Tools directory"),

            # Core files
            (self.runtime_dir / "jarvis.py", "file", "FastAPI server"),
            (self.runtime_dir / "execution_hub.py", "file", "Execution hub"),
            (self.runtime_dir / "system_settings.ndjson", "file", "System registry"),

            # Critical data files
            (self.data_dir / "working_memory.json", "file", "Working memory"),
            (self.data_dir / "automation_rules.json", "file", "Automation rules"),
            (self.data_dir / "thread_state.json", "file", "Thread state"),

            # Claude Code
            (Path.home() / ".local/bin/claude", "file", "Claude Code CLI"),
            (self.claude_dir, "dir", "Claude config directory"),
            (self.claude_dir / "CLAUDE.md", "file", "Claude instructions"),
            (self.claude_dir / "settings.json", "file", "Claude settings"),
            (self.claude_dir / "hooks/inject_schemas.py", "file", "Schema injection hook"),
        ]

        results = []
        for path, path_type, description in critical_paths:
            test = {
                'test': f'path_{path.name}',
                'path': str(path),
                'description': description,
                'status': 'FAIL',
                'error': None
            }

            try:
                if not path.exists():
                    test['error'] = f"{path_type.upper()} does not exist"
                    print(f"  {Colors.RED}✗{Colors.END} {description}: NOT FOUND")
                elif path_type == "dir" and not path.is_dir():
                    test['error'] = "Path exists but is not a directory"
                    print(f"  {Colors.RED}✗{Colors.END} {description}: NOT A DIR")
                elif path_type == "file" and not path.is_file():
                    test['error'] = "Path exists but is not a file"
                    print(f"  {Colors.RED}✗{Colors.END} {description}: NOT A FILE")
                else:
                    test['status'] = 'PASS'
                    print(f"  {Colors.GREEN}✓{Colors.END} {description}")

            except Exception as e:
                test['error'] = str(e)
                print(f"  {Colors.RED}✗{Colors.END} {description}: {e}")

            results.append(test)

        return results

    def test_file_permissions(self) -> List[Dict[str, Any]]:
        """Check file permissions for critical files"""
        print(f"\n{Colors.BOLD}Testing File Permissions{Colors.END}")

        writable_paths = [
            self.data_dir / "working_memory.json",
            self.data_dir / "automation_rules.json",
            self.data_dir / "thread_state.json",
            self.data_dir / "claude_task_queue.json",
            self.data_dir / "claude_task_results.json",
        ]

        results = []
        for path in writable_paths:
            test = {
                'test': f'perms_{path.name}',
                'path': str(path),
                'status': 'FAIL',
                'error': None
            }

            try:
                if not path.exists():
                    test['status'] = 'SKIP'
                    print(f"  {Colors.YELLOW}⊘{Colors.END} {path.name}: Does not exist (will be created)")
                elif os.access(path, os.R_OK) and os.access(path, os.W_OK):
                    test['status'] = 'PASS'
                    print(f"  {Colors.GREEN}✓{Colors.END} {path.name}: Readable & Writable")
                else:
                    test['error'] = "Not readable/writable"
                    print(f"  {Colors.RED}✗{Colors.END} {path.name}: Permission denied")

            except Exception as e:
                test['error'] = str(e)
                print(f"  {Colors.RED}✗{Colors.END} {path.name}: {e}")

            results.append(test)

        return results

    def test_claude_code_install(self) -> List[Dict[str, Any]]:
        """Validate Claude Code installation"""
        print(f"\n{Colors.BOLD}Testing Claude Code Installation{Colors.END}")

        results = []

        # Test 1: CLI exists and is executable
        test = {
            'test': 'claude_cli_executable',
            'status': 'FAIL',
            'error': None
        }

        claude_cli = Path.home() / ".local/bin/claude"
        try:
            if claude_cli.exists() and os.access(claude_cli, os.X_OK):
                test['status'] = 'PASS'
                print(f"  {Colors.GREEN}✓{Colors.END} Claude CLI is executable")
            else:
                test['error'] = "CLI not executable"
                print(f"  {Colors.RED}✗{Colors.END} Claude CLI not executable")
        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        # Test 2: Get version
        test = {
            'test': 'claude_version',
            'status': 'FAIL',
            'error': None,
            'version': None
        }

        try:
            result = subprocess.run(
                [str(claude_cli), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                test['status'] = 'PASS'
                test['version'] = result.stdout.strip()
                print(f"  {Colors.GREEN}✓{Colors.END} Claude Code version: {test['version']}")
            else:
                test['error'] = result.stderr
                print(f"  {Colors.RED}✗{Colors.END} Version check failed")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        return results

    def test_claude_configuration(self) -> List[Dict[str, Any]]:
        """Validate Claude Code configuration"""
        print(f"\n{Colors.BOLD}Testing Claude Code Configuration{Colors.END}")

        results = []

        # Test settings.json
        test = {
            'test': 'claude_settings_valid',
            'status': 'FAIL',
            'error': None
        }

        settings_path = self.claude_dir / "settings.json"
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)

            # Check for critical settings
            if 'userPromptSubmitHook' in settings:
                test['status'] = 'PASS'
                print(f"  {Colors.GREEN}✓{Colors.END} settings.json valid with hooks configured")
            else:
                test['error'] = "Missing userPromptSubmitHook"
                print(f"  {Colors.RED}✗{Colors.END} settings.json missing hook config")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        # Test inject_schemas.py
        test = {
            'test': 'schema_injection_hook',
            'status': 'FAIL',
            'error': None
        }

        hook_path = self.claude_dir / "hooks/inject_schemas.py"
        try:
            if hook_path.exists() and os.access(hook_path, os.X_OK):
                # Try importing it
                import importlib.util
                spec = importlib.util.spec_from_file_location("inject_schemas", hook_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                test['status'] = 'PASS'
                print(f"  {Colors.GREEN}✓{Colors.END} Schema injection hook is valid")
            else:
                test['error'] = "Hook not executable"
                print(f"  {Colors.RED}✗{Colors.END} Hook not executable")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        return results

    def test_system_registry(self) -> List[Dict[str, Any]]:
        """Validate system_settings.ndjson"""
        print(f"\n{Colors.BOLD}Testing System Registry{Colors.END}")

        results = []

        test = {
            'test': 'system_registry_valid',
            'status': 'FAIL',
            'error': None,
            'tools_count': 0
        }

        registry_path = self.runtime_dir / "system_settings.ndjson"
        try:
            tools = set()
            with open(registry_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        if entry.get('action') == '__tool__':
                            tools.add(entry['tool'])
                    except json.JSONDecodeError as e:
                        test['error'] = f"Invalid JSON on line {line_num}"
                        print(f"  {Colors.RED}✗{Colors.END} Line {line_num}: Invalid JSON")
                        break

            if test['error'] is None:
                test['status'] = 'PASS'
                test['tools_count'] = len(tools)
                print(f"  {Colors.GREEN}✓{Colors.END} System registry valid with {len(tools)} tools")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        return results

    def test_execution_hub(self) -> List[Dict[str, Any]]:
        """Test execution_hub.py functionality"""
        print(f"\n{Colors.BOLD}Testing Execution Hub{Colors.END}")

        results = []

        # Test simple noop action
        test = {
            'test': 'execution_hub_basic',
            'status': 'FAIL',
            'error': None
        }

        try:
            result = subprocess.run(
                [
                    'python3',
                    str(self.runtime_dir / 'execution_hub.py'),
                    'execute_task',
                    '--params',
                    json.dumps({
                        'tool_name': 'system_settings',
                        'action': 'list_tools',
                        'params': {}
                    })
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    if 'tools' in output:
                        test['status'] = 'PASS'
                        print(f"  {Colors.GREEN}✓{Colors.END} execution_hub.py working")
                    else:
                        test['error'] = "Unexpected output format"
                        print(f"  {Colors.RED}✗{Colors.END} Unexpected output")
                except json.JSONDecodeError:
                    test['error'] = "Output not valid JSON"
                    print(f"  {Colors.RED}✗{Colors.END} Invalid JSON output")
            else:
                test['error'] = result.stderr
                print(f"  {Colors.RED}✗{Colors.END} Execution failed: {result.stderr[:100]}")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        return results

    def test_credentials_system(self) -> List[Dict[str, Any]]:
        """Test credentials.json handling"""
        print(f"\n{Colors.BOLD}Testing Credentials System{Colors.END}")

        results = []

        test = {
            'test': 'credentials_file',
            'status': 'FAIL',
            'error': None
        }

        creds_path = self.tools_dir / "credentials.json"
        try:
            if creds_path.exists():
                with open(creds_path, 'r') as f:
                    creds = json.load(f)

                test['status'] = 'PASS'
                print(f"  {Colors.GREEN}✓{Colors.END} credentials.json exists and is valid JSON")
            else:
                # File doesn't exist yet - that's ok, it will be created
                test['status'] = 'SKIP'
                print(f"  {Colors.YELLOW}⊘{Colors.END} credentials.json doesn't exist yet (will be created)")

        except Exception as e:
            test['error'] = str(e)
            print(f"  {Colors.RED}✗{Colors.END} {e}")

        results.append(test)

        return results

    def test_tool_scripts(self) -> List[Dict[str, Any]]:
        """Validate all tool scripts are importable"""
        print(f"\n{Colors.BOLD}Testing Tool Scripts{Colors.END}")

        results = []
        tool_count = 0
        failed_count = 0

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            tool_count += 1
            test = {
                'test': f'tool_{tool_file.stem}',
                'file': str(tool_file),
                'status': 'FAIL',
                'error': None
            }

            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(tool_file.stem, tool_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                test['status'] = 'PASS'

            except Exception as e:
                test['error'] = str(e)
                failed_count += 1
                print(f"  {Colors.RED}✗{Colors.END} {tool_file.name}: {e}")

            results.append(test)

        print(f"  {Colors.GREEN}✓{Colors.END} {tool_count - failed_count}/{tool_count} tools importable")

        return results

    def run_all_tests(self) -> int:
        """Run all container validation tests"""
        print(f"{Colors.BOLD}Container Validation Suite{Colors.END}")
        print(f"Runtime: {self.runtime_dir}\n")

        all_results = []

        # Run test suites
        all_results.extend(self.test_critical_paths())
        all_results.extend(self.test_file_permissions())
        all_results.extend(self.test_claude_code_install())
        all_results.extend(self.test_claude_configuration())
        all_results.extend(self.test_system_registry())
        all_results.extend(self.test_credentials_system())
        all_results.extend(self.test_execution_hub())
        all_results.extend(self.test_tool_scripts())

        # Summary
        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.END}")
        print(f"{'='*60}\n")

        total = len(all_results)
        passed = sum(1 for r in all_results if r['status'] == 'PASS')
        failed = sum(1 for r in all_results if r['status'] == 'FAIL')
        skipped = sum(1 for r in all_results if r['status'] == 'SKIP')

        print(f"Total Tests:    {total}")
        print(f"{Colors.GREEN}Passed:         {passed}{Colors.END}")
        print(f"{Colors.RED}Failed:         {failed}{Colors.END}")
        print(f"Skipped:        {skipped}")

        if failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ CONTAINER VALIDATION FAILED{Colors.END}")
            print(f"\nFailed tests:")
            for r in all_results:
                if r['status'] == 'FAIL':
                    print(f"  {Colors.RED}✗{Colors.END} {r['test']}")
                    if r.get('error'):
                        print(f"    {r['error']}")
            return 1
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ CONTAINER VALIDATED - READY FOR USE{Colors.END}")
            return 0


def main():
    validator = ContainerValidator()
    exit_code = validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
