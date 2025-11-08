#!/usr/bin/env python3
"""
Claude Code Queue Watcher - Host Side

Monitors ~/Documents/Orchestrate/claude_task_queue.json for new tasks.
When detected, spawns Claude Code session on host machine.
Results written back to claude_task_results.json.

This runs ON THE HOST, not in the Docker container.
Container writes tasks → Host spawns Claude sessions → Results go back.

Usage:
    python3 claude_queue_watcher.py

Background:
    nohup python3 ~/Documents/Orchestrate/claude_queue_watcher.py > ~/Documents/Orchestrate/watcher.log 2>&1 &
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class ClaudeQueueHandler(FileSystemEventHandler):
    """Handles Claude task queue changes"""

    def __init__(self, queue_file, results_file):
        self.queue_file = queue_file
        self.results_file = results_file
        self.processing = False
        self.processed_tasks = set()

        # Load already processed tasks
        self._load_processed_tasks()

    def _load_processed_tasks(self):
        """Load list of already processed task IDs"""
        try:
            with open(self.results_file, 'r') as f:
                results = json.load(f)
                self.processed_tasks = set(results.keys())
                log(f"✅ Loaded {len(self.processed_tasks)} completed tasks")
        except:
            log("📝 No previous results found - starting fresh")

    def on_modified(self, event):
        """Triggered when queue file changes"""
        if event.src_path != self.queue_file:
            return

        if self.processing:
            return

        self._check_for_new_tasks()

    def _check_for_new_tasks(self):
        """Check queue for new tasks and spawn Claude sessions"""
        try:
            with open(self.queue_file, 'r') as f:
                queue = json.load(f)

            # Find pending tasks not yet processed
            # Queue structure: {"tasks": {task_id: task_data}}
            pending = []
            tasks = queue.get("tasks", {})
            for task_id, task_data in tasks.items():
                if not isinstance(task_data, dict):
                    continue  # Skip malformed entries
                status = task_data.get('status', 'queued')
                if status == 'queued' and task_id not in self.processed_tasks:
                    pending.append((task_id, task_data))

            if not pending:
                return

            log(f"🆕 Found {len(pending)} new task(s)")

            for task_id, task_data in pending:
                self._spawn_claude_session(task_id, task_data)

        except json.JSONDecodeError:
            # File might be mid-write, try again
            pass
        except Exception as e:
            log(f"❌ Error checking queue: {e}")

    def _spawn_claude_session(self, task_id, task_data):
        """Spawn Claude Code session for a task"""
        self.processing = True

        try:
            description = task_data.get('description', 'No description')
            log(f"🚀 Spawning Claude session for: {task_id}")
            log(f"   Description: {description}")

            # Update task status to in_progress
            self._update_task_status(task_id, 'in_progress')

            # Spawn Claude Code session with proper prompt
            prompt = f"{description}\n\nYou can use tools via API at http://localhost:8000/execute_task"
            cmd = [
                'claude',
                '-p', prompt,
                '--permission-mode', 'acceptEdits',
                '--allowedTools', 'Bash,Read,Write,Edit'
            ]

            # Run in background with subscription auth (no API key)
            import os
            env = os.environ.copy()
            env.pop('ANTHROPIC_API_KEY', None)  # Use subscription auth, not API

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            log(f"✅ Claude session started (PID: {process.pid})")

            # Mark as processed (even if running, don't spawn twice)
            self.processed_tasks.add(task_id)

            # Note: Results will be written by Claude session when complete
            # We don't wait here - it runs autonomously

        except FileNotFoundError:
            log(f"❌ Claude Code not found! Install with: brew install claude-code")
            self._update_task_status(task_id, 'error', error='Claude Code not installed')
        except Exception as e:
            log(f"❌ Error spawning Claude: {e}")
            self._update_task_status(task_id, 'error', error=str(e))
        finally:
            self.processing = False

    def _update_task_status(self, task_id, status, **kwargs):
        """Update task status in queue file"""
        try:
            with open(self.queue_file, 'r') as f:
                queue = json.load(f)

            tasks = queue.get("tasks", {})
            if task_id in tasks:
                tasks[task_id]['status'] = status
                tasks[task_id].update(kwargs)
                queue["tasks"] = tasks

                with open(self.queue_file, 'w') as f:
                    json.dump(queue, f, indent=2)

        except Exception as e:
            log(f"⚠️  Couldn't update status: {e}")


def main():
    """Main watcher loop"""
    # Paths
    orchestrate_dir = os.path.expanduser("~/Documents/Orchestrate")
    queue_file = os.path.join(orchestrate_dir, "claude_task_queue.json")
    results_file = os.path.join(orchestrate_dir, "claude_task_results.json")

    # Ensure directory exists
    os.makedirs(orchestrate_dir, exist_ok=True)

    # Ensure files exist
    if not os.path.exists(queue_file):
        with open(queue_file, 'w') as f:
            json.dump({}, f)
        log("📝 Created empty queue file")

    if not os.path.exists(results_file):
        with open(results_file, 'w') as f:
            json.dump({}, f)
        log("📝 Created empty results file")

    log("⚡ Claude Code Queue Watcher Started")
    log(f"📁 Watching: {queue_file}")
    log("💡 Container writes tasks → Host spawns Claude sessions")
    log("🛑 Press Ctrl+C to stop")
    log("")

    # Set up file system observer
    event_handler = ClaudeQueueHandler(queue_file, results_file)
    observer = Observer()
    observer.schedule(event_handler, orchestrate_dir, recursive=False)
    observer.start()

    # Also check for existing tasks on startup
    event_handler._check_for_new_tasks()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("")
        log("🛑 Stopping watcher...")
        observer.stop()

    observer.join()
    log("✅ Watcher stopped")


if __name__ == "__main__":
    main()
