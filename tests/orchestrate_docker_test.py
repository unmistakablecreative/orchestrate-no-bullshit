#!/usr/bin/env python3
"""
OrchestrateOS Docker Installation Test Suite

Automated end-to-end testing for Docker container installations.
Runs all tests autonomously and reports results.

Usage:
    python3 orchestrate_docker_test.py
    python3 orchestrate_docker_test.py --tests-file custom_tests.json
    python3 orchestrate_docker_test.py --quick  # Run only critical tests
"""

import json
import sys
import requests
import argparse
from datetime import datetime
from typing import Dict, List, Any


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestRunner:
    def __init__(self, tests_file: str, quick_mode: bool = False):
        self.tests_file = tests_file
        self.quick_mode = quick_mode
        self.results = []
        self.ngrok_url = None
        self.start_time = None
        self.end_time = None

    def load_tests(self) -> Dict[str, Any]:
        """Load test configuration from JSON file"""
        try:
            with open(self.tests_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to load tests file: {e}{Colors.END}")
            sys.exit(1)

    def run_test(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test"""
        test_name = test['name']
        description = test['description']
        endpoint = test['endpoint']
        payload = test['payload']

        print(f"\n{Colors.BLUE}▶ Running: {test_name}{Colors.END}")
        print(f"  {description}")

        result = {
            'name': test_name,
            'description': description,
            'status': 'FAIL',
            'message': '',
            'critical': test.get('critical', False),
            'duration': 0
        }

        try:
            start = datetime.now()

            # Make request to ngrok endpoint
            url = f"{self.ngrok_url}{endpoint}"
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            end = datetime.now()
            result['duration'] = (end - start).total_seconds()

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {'raw': response.text}

            # Check status
            expected_status = test.get('expected_status', 'success')
            actual_status = response_data.get('status', 'unknown')

            if actual_status == expected_status:
                # Check for expected content if specified
                if 'expected_contains' in test:
                    response_str = json.dumps(response_data)
                    if test['expected_contains'] in response_str:
                        result['status'] = 'PASS'
                        result['message'] = f"Status: {actual_status}, contains expected content"
                    else:
                        result['message'] = f"Status ok, but missing expected content: {test['expected_contains']}"
                else:
                    result['status'] = 'PASS'
                    result['message'] = f"Status: {actual_status}"
            else:
                result['message'] = f"Expected status '{expected_status}', got '{actual_status}'"

            result['response'] = response_data

        except requests.exceptions.RequestException as e:
            result['message'] = f"Request failed: {str(e)}"
        except Exception as e:
            result['message'] = f"Test execution failed: {str(e)}"

        # Print result
        if result['status'] == 'PASS':
            print(f"  {Colors.GREEN}✓ PASS{Colors.END} ({result['duration']:.2f}s)")
        else:
            status_color = Colors.RED if result['critical'] else Colors.YELLOW
            critical_marker = " [CRITICAL]" if result['critical'] else ""
            print(f"  {status_color}✗ FAIL{critical_marker}{Colors.END} - {result['message']}")

        return result

    def run_cleanup(self, cleanup_tasks: List[Dict[str, Any]]):
        """Run cleanup tasks"""
        if not cleanup_tasks:
            return

        print(f"\n{Colors.BLUE}🧹 Running cleanup...{Colors.END}")
        for task in cleanup_tasks:
            try:
                url = f"{self.ngrok_url}{task['endpoint']}"
                requests.post(url, json=task['payload'], timeout=10)
            except:
                pass  # Ignore cleanup errors

    def generate_report(self):
        """Generate and print test report"""
        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}TEST RESULTS SUMMARY{Colors.END}")
        print(f"{'='*60}")

        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        critical_failed = sum(1 for r in self.results if r['status'] == 'FAIL' and r['critical'])

        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\nTotal Tests:    {total}")
        print(f"{Colors.GREEN}Passed:         {passed}{Colors.END}")
        print(f"{Colors.RED}Failed:         {failed}{Colors.END}")
        print(f"{Colors.RED}Critical Fails: {critical_failed}{Colors.END}")
        print(f"Duration:       {duration:.2f}s")

    def verify_claude_auth(self) -> Dict[str, Any]:
        """Verify Claude Code authentication in Docker container"""
        print(f"\n{Colors.BLUE}▶ Verifying Claude Code authentication...{Colors.END}")

        result = {
            'status': 'FAIL',
            'message': '',
            'authenticated': False
        }

        try:
            # Check if Claude is authenticated via docker exec
            url = f"{self.ngrok_url}/execute_task"
            payload = {
                "tool_name": "unlock_tool",
                "action": "check_claude_auth",
                "params": {}
            }

            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response_data = response.json()

            if response_data.get('status') == 'success' and response_data.get('authenticated'):
                result['status'] = 'PASS'
                result['authenticated'] = True
                result['message'] = "Claude Code is authenticated"
                print(f"  {Colors.GREEN}✓ Claude Code authenticated{Colors.END}")
            else:
                result['message'] = "Claude Code not authenticated"
                print(f"  {Colors.RED}✗ Claude Code not authenticated{Colors.END}")

        except Exception as e:
            result['message'] = f"Auth check failed: {str(e)}"
            print(f"  {Colors.RED}✗ {result['message']}{Colors.END}")

        return result

    def run_claude_tests(self) -> List[Dict[str, Any]]:
        """Run Claude assistant test suite from claude_tests.json"""
        print(f"\n{Colors.BOLD}Running Claude Assistant Tests{Colors.END}")

        claude_results = []

        try:
            # Load claude_tests.json
            with open('tests/claude_tests.json', 'r') as f:
                claude_test_config = json.load(f)

            tests = claude_test_config.get('tests', [])
            print(f"  Found {len(tests)} Claude tests")

            # Run each test
            for test in tests:
                result = self.run_test(test)
                claude_results.append(result)

        except FileNotFoundError:
            print(f"{Colors.RED}✗ claude_tests.json not found{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to run Claude tests: {e}{Colors.END}")

        return claude_results

        # Detailed failures
        if failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for result in self.results:
                if result['status'] == 'FAIL':
                    critical = " [CRITICAL]" if result['critical'] else ""
                    print(f"  ✗ {result['name']}{critical}")
                    print(f"    {result['message']}")

        # Overall status
        print(f"\n{'='*60}")
        if critical_failed > 0:
            print(f"{Colors.RED}{Colors.BOLD}❌ CRITICAL FAILURES - INSTALLATION BROKEN{Colors.END}")
            return 1
        elif failed > 0:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  SOME TESTS FAILED - CHECK RESULTS{Colors.END}")
            return 1
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED - INSTALLATION VERIFIED{Colors.END}")
            return 0

    def run(self) -> int:
        """Run all tests and return exit code"""
        print(f"{Colors.BOLD}OrchestrateOS Docker Installation Test Suite{Colors.END}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        self.start_time = datetime.now()

        # Load tests
        config = self.load_tests()
        self.ngrok_url = config['ngrok_url']
        tests = config['tests']

        # Filter to critical tests only if quick mode
        if self.quick_mode:
            tests = [t for t in tests if t.get('critical', False)]
            print(f"{Colors.YELLOW}Quick mode: Running {len(tests)} critical tests only{Colors.END}\n")

        print(f"Testing endpoint: {self.ngrok_url}")
        print(f"Total tests: {len(tests)}\n")

        # Run tests
        for test in tests:
            result = self.run_test(test)
            self.results.append(result)

            # Stop on critical failure if in quick mode
            if self.quick_mode and result['critical'] and result['status'] == 'FAIL':
                print(f"\n{Colors.RED}Critical test failed - stopping execution{Colors.END}")
                break

        # Cleanup
        if 'cleanup' in config:
            self.run_cleanup(config['cleanup'])

        self.end_time = datetime.now()

        # Generate report
        return self.generate_report()


def main():
    parser = argparse.ArgumentParser(
        description='OrchestrateOS Docker Installation Test Suite'
    )
    parser.add_argument(
        '--tests-file',
        default='orchestrate_docker_tests.json',
        help='Path to tests JSON file'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run only critical tests'
    )

    args = parser.parse_args()

    runner = TestRunner(args.tests_file, args.quick)
    exit_code = runner.run()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
