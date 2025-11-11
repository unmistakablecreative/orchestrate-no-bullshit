#!/usr/bin/env python3
"""
Claude Code Queue Processor - Container Side

Monitors data/claude_task_queue.json for new tasks.
When detected, spawns Claude Code session inside container.
Results written back to claude_task_results.json.

This runs INSIDE THE DOCKER CONTAINER as a background thread.
No host-side dependencies needed.
"""

import os
import sys
import time
import json
import subprocess
import threading
from datetime import datetime


def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[QUEUE] [{timestamp}] {message}", file=sys.stderr, flush=True)


class ClaudeQueueProcessor:
    """Processes Claude task queue inside container"""

    def __init__(self, queue_file="data/claude_task_queue.json", results_file="data/claude_task_results.json"):
        self.queue_file = queue_file
        self.results_file = results_file
        self.processed_tasks = set()
        self.running = False
        self.poll_interval = 5  # seconds

        # Load already processed tasks
        self._load_processed_tasks()

    def _load_processed_tasks(self):
        """Load list of already processed task IDs"""
        try:
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r') as f:
                    results = json.load(f)
                    self.processed_tasks = set(results.get("results", {}).keys())
                    log(f"✅ Loaded {len(self.processed_tasks)} completed tasks")
        except Exception as e:
            log(f"📝 No previous results found - starting fresh: {e}")

    def _check_for_new_tasks(self):
        """Check queue for new tasks and spawn Claude sessions"""
        try:
            if not os.path.exists(self.queue_file):
                return

            with open(self.queue_file, 'r') as f:
                queue = json.load(f)

            # Find pending tasks not yet processed
            pending = []
            for task_id, task_data in queue.get("tasks", {}).items():
                status = task_data.get('status', 'queued')
                if status == 'queued' and task_id not in self.processed_tasks:
                    pending.append((task_id, task_data))

            if not pending:
                return

            log(f"🆕 Found {len(pending)} new task(s)")

            for task_id, task_data in pending:
                self._spawn_claude_session(task_id, task_data)

        except json.JSONDecodeError:
            # File might be mid-write, try again next poll
            pass
        except Exception as e:
            log(f"❌ Error checking queue: {e}")

    def _spawn_claude_session(self, task_id, task_data):
        """Spawn Claude Code session for a task"""
        try:
            description = task_data.get('description', 'No description')
            log(f"🚀 Spawning Claude session for: {task_id}")
            log(f"   Description: {description}")

            # Update task status to in_progress
            self._update_task_status(task_id, 'in_progress')

            # Find Claude binary
            claude_path = os.path.expanduser("~/.local/bin/claude")

            if not os.path.exists(claude_path):
                log("❌ Claude Code not installed! Run unlock_tool first.")
                self._update_task_status(task_id, 'error', error='Claude Code not installed')
                return

            # Build command
            cmd = [
                claude_path,
                '-p',
                '--dangerously-skip-permissions',
                description
            ]

            # Set PATH to include ~/.local/bin
            env = os.environ.copy()
            env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"

            # Run in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            log(f"✅ Claude session started (PID: {process.pid})")

            # Mark as processed (even if running, don't spawn twice)
            self.processed_tasks.add(task_id)

            # Wait for completion in background thread
            def wait_for_completion():
                stdout, stderr = process.communicate()
                exit_code = process.returncode

                if exit_code == 0:
                    log(f"✅ Task {task_id} completed successfully")
                    self._update_task_status(task_id, 'completed', output=stdout)
                    self._save_result(task_id, {
                        "status": "completed",
                        "completed_at": datetime.now().isoformat(),
                        "output": stdout
                    })
                else:
                    log(f"❌ Task {task_id} failed with exit code {exit_code}")
                    log(f"   stderr: {stderr[:200]}")
                    self._update_task_status(task_id, 'error', error=f"Exit code {exit_code}", stderr=stderr)
                    self._save_result(task_id, {
                        "status": "error",
                        "completed_at": datetime.now().isoformat(),
                        "error": f"Exit code {exit_code}",
                        "stderr": stderr
                    })

            # Start monitoring thread
            threading.Thread(target=wait_for_completion, daemon=True).start()

        except FileNotFoundError:
            log(f"❌ Claude Code not found! Install with unlock_tool")
            self._update_task_status(task_id, 'error', error='Claude Code not installed')
        except Exception as e:
            log(f"❌ Error spawning Claude: {e}")
            self._update_task_status(task_id, 'error', error=str(e))

    def _update_task_status(self, task_id, status, **kwargs):
        """Update task status in queue file"""
        try:
            if not os.path.exists(self.queue_file):
                return

            with open(self.queue_file, 'r') as f:
                queue = json.load(f)

            if task_id in queue.get("tasks", {}):
                queue["tasks"][task_id]['status'] = status
                queue["tasks"][task_id].update(kwargs)

                if status == 'in_progress':
                    queue["tasks"][task_id]['started_at'] = datetime.now().isoformat()
                elif status in ['completed', 'error']:
                    queue["tasks"][task_id]['completed_at'] = datetime.now().isoformat()

                with open(self.queue_file, 'w') as f:
                    json.dump(queue, f, indent=2)

        except Exception as e:
            log(f"⚠️  Couldn't update status: {e}")

    def _save_result(self, task_id, result_data):
        """Save task result to results file"""
        try:
            results = {"results": {}}

            if os.path.exists(self.results_file):
                with open(self.results_file, 'r') as f:
                    results = json.load(f)

            if "results" not in results:
                results["results"] = {}

            results["results"][task_id] = result_data

            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2)

        except Exception as e:
            log(f"⚠️  Couldn't save result: {e}")

    def start(self):
        """Start the queue processor"""
        self.running = True
        log("⚡ Claude Code Queue Processor Started")
        log(f"📁 Watching: {self.queue_file}")
        log(f"⏱️  Poll interval: {self.poll_interval}s")
        log("")

        # Initial check for existing tasks
        try:
            self._check_for_new_tasks()
        except Exception as e:
            log(f"❌ Error in initial check: {e}")

        # Poll loop
        while self.running:
            try:
                time.sleep(self.poll_interval)
                log("🔍 Polling for new tasks...")
                self._check_for_new_tasks()
            except Exception as e:
                log(f"❌ Error in poll loop: {e}")
                import traceback
                log(f"Traceback: {traceback.format_exc()}")

    def stop(self):
        """Stop the queue processor"""
        self.running = False
        log("🛑 Queue processor stopped")

    def start_background(self):
        """Start processor in background thread"""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        log("🔄 Queue processor running in background")
        return thread


def main():
    """Main entrypoint for standalone execution"""
    processor = ClaudeQueueProcessor()

    try:
        processor.start()
    except KeyboardInterrupt:
        log("")
        log("🛑 Stopping processor...")
        processor.stop()


if __name__ == "__main__":
    main()
