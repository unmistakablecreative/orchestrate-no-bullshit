#!/usr/bin/env python3
"""
Claude Assistant - Minimal Core Version
6 core functions only, no advanced features
"""

import sys
import json
import os
import subprocess
import time
import requests
from datetime import datetime


def assign_task(params):
    """
    GPT assigns a task to Claude Code queue.

    Required:
    - task_id: unique identifier
    - description: what Claude should do

    Optional:
    - priority: high/medium/low (default: medium)
    - context: extra info for Claude (default: {})
    - create_output_doc: if true, Claude will create an outline doc (default: false)
    """
    task_id = params.get("task_id")
    description = params.get("description")
    priority = params.get("priority", "medium")
    create_output_doc = params.get("create_output_doc", False)

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}
    if not description:
        return {"status": "error", "message": "❌ Missing required field: description"}

    # Reset thread score to 100 at start of each task
    try:
        subprocess.run(
            ["python3", "execution_hub.py", "load_orchestrate_os"],
            capture_output=True,
            timeout=10,
            cwd=os.getcwd()
        )
    except Exception:
        pass  # Non-critical, continue

    # Default context - includes both instructions AND project memory
    memory_file = os.path.join(os.getcwd(), ".claude/CLAUDE.md")
    memory_instructions = ""
    if os.path.exists(memory_file):
        memory_instructions = f" Also read {memory_file} for project-specific doc IDs, file paths, and patterns."

    default_context = {
        "instructions": f"Read /Users/srinivas/Orchestrate Github/orchestrate-jarvis/data/claude_instructions.md before starting.{memory_instructions}"
    }

    context = params.get("context", {})
    if not context:
        context = default_context
    elif "instructions" not in context:
        context["instructions"] = default_context["instructions"]

    # Only load working_context if explicitly requested
    include_working_context = params.get("include_working_context", False)
    if include_working_context:
        working_context_file = os.path.join(os.getcwd(), "data/working_context.json")
        if os.path.exists(working_context_file):
            try:
                with open(working_context_file, 'r', encoding='utf-8') as f:
                    working_context = json.load(f)
                context["working_context"] = working_context
            except Exception:
                pass

    context["create_output_doc"] = create_output_doc

    # If create_output_doc is true, add hint for Claude to use outline_editor
    if create_output_doc:
        context["hint"] = "Create an outline document for this task using execution_hub.py with outline_editor.create_doc"

    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")
    os.makedirs(os.path.dirname(queue_file), exist_ok=True)

    # Load queue
    if os.path.exists(queue_file):
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    else:
        queue = {"tasks": {}}

    # Add task
    queue["tasks"][task_id] = {
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "assigned_by": "GPT",
        "priority": priority,
        "description": description,
        "context": context
    }

    # Save queue
    with open(queue_file, 'w', encoding='utf-8') as f:
        json.dump(queue, f, indent=2)

    # Auto-execute if not inside Claude Code
    auto_execute = params.get("auto_execute", True)  # Default to auto-execute

    if auto_execute and not os.environ.get("CLAUDECODE"):
        # Spawn Claude session to process this task immediately
        execute_result = execute_queue({})
        return {
            "status": "success",
            "message": f"✅ Task '{task_id}' assigned and execution started",
            "task_id": task_id,
            "execution": execute_result
        }

    return {
        "status": "success",
        "message": f"✅ Task '{task_id}' assigned to Claude Code queue",
        "task_id": task_id,
        "next_step": "Call execute_queue to trigger processing" if not auto_execute else "Task will be processed in current session"
    }


def assign_demo_task(params):
    """
    Assigns a task with guaranteed 'demo_' prefix for demo recordings.

    Required:
    - task_id: unique identifier (will auto-prepend 'demo_' if missing)
    - description: what Claude should do

    Optional:
    - priority: high/medium/low (default: medium)
    - context: extra info for Claude (default: {})
    - create_output_doc: if true, Claude will create an outline doc (default: false)
    - auto_execute: same behavior as assign_task (default: true)

    Note: Only adds 'demo_' prefix - all other behavior identical to assign_task
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    # Force demo_ prefix
    if not task_id.startswith("demo_"):
        task_id = f"demo_{task_id}"

    # Update params with modified task_id (preserve all other params including auto_execute)
    modified_params = params.copy()
    modified_params["task_id"] = task_id

    # Call assign_task with modified params
    result = assign_task(modified_params)

    # Add demo-specific message
    if result.get("status") == "success":
        result["message"] = f"✅ Demo task '{task_id}' assigned and will execute autonomously"

    return result


def check_task_status(params):
    """
    Check status of a task.

    Required:
    - task_id: the task to check

    Returns status: queued, pending, done, error
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    # Check queue
    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")
    if os.path.exists(queue_file):
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
            if task_id in queue.get("tasks", {}):
                task_data = queue["tasks"][task_id]
                return {
                    "status": "success",
                    "task_id": task_id,
                    "task_status": task_data["status"],
                    "created_at": task_data.get("created_at"),
                    "description": task_data.get("description")
                }

    # Check results
    results_file = os.path.join(os.getcwd(), "data/claude_task_results.json")
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            if task_id in results.get("results", {}):
                result_data = results["results"][task_id]
                return {
                    "status": "success",
                    "task_id": task_id,
                    "task_status": "done",
                    "completed_at": result_data.get("completed_at"),
                    "execution_time_seconds": result_data.get("execution_time_seconds"),
                    "output": result_data.get("output")
                }
        except Exception as e:
            return {"status": "error", "message": f"❌ Error reading results: {str(e)}"}

    return {
        "status": "error",
        "message": f"❌ Task '{task_id}' not found in queue or results"
    }


def get_task_result(params):
    """
    Get full result data from a completed task.

    Required:
    - task_id: the completed task

    Returns full completion report
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    results_file = os.path.join(os.getcwd(), "data/claude_task_results.json")

    if not os.path.exists(results_file):
        return {
            "status": "error",
            "message": f"❌ No results file found. Task '{task_id}' may not be complete yet."
        }

    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading results: {str(e)}"}

    if task_id not in results.get("results", {}):
        return {
            "status": "error",
            "message": f"❌ No result found for task '{task_id}'. Check if task is complete with check_task_status."
        }

    return {
        "status": "success",
        "task_id": task_id,
        "result": results["results"][task_id]
    }


def get_all_results(params):
    """
    Get all task results without needing individual task IDs.

    GPT calls this to see all completed tasks at once.

    No parameters needed.
    """
    results_file = os.path.join(os.getcwd(), "data/claude_task_results.json")

    if not os.path.exists(results_file):
        return {
            "status": "success",
            "message": "✅ No task results yet",
            "results": {},
            "task_count": 0
        }

    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading results: {str(e)}"}

    all_results = results.get("results", {})

    return {
        "status": "success",
        "message": f"Found {len(all_results)} completed task(s)",
        "results": all_results,
        "task_count": len(all_results)
    }


def ask_claude(params):
    """
    Quick Q&A - GPT asks Claude a simple question, Claude answers.

    No task queue, no logging. Just direct question/answer.
    Use this for quick lookups like "what did you use for X?" or "did that work?"

    Required:
    - question: the question to ask Claude

    Returns:
    - answer: Claude's response

    Note: This returns a placeholder. The actual answer comes from Claude
    reading this function call and responding in the session.
    """
    question = params.get("question")

    if not question:
        return {"status": "error", "message": "❌ Missing required field: question"}

    return {
        "status": "ready",
        "message": "📝 Question received - Claude will respond in current session",
        "question": question,
        "note": "Claude sees this and will answer directly without task queue"
    }


def cancel_task(params):
    """
    Cancel a queued or in_progress task.

    Required:
    - task_id: the task to cancel

    Returns success if task was cancelled.
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")

    if not os.path.exists(queue_file):
        return {"status": "error", "message": "❌ No task queue found"}

    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading queue: {str(e)}"}

    if task_id not in queue.get("tasks", {}):
        return {"status": "error", "message": f"❌ Task '{task_id}' not found in queue"}

    task = queue["tasks"][task_id]
    current_status = task.get("status")

    if current_status in ["done", "error"]:
        return {"status": "error", "message": f"❌ Cannot cancel task that is already {current_status}"}

    # Mark as cancelled
    queue["tasks"][task_id]["status"] = "cancelled"
    queue["tasks"][task_id]["cancelled_at"] = datetime.now().isoformat()

    try:
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error writing queue: {str(e)}"}

    return {
        "status": "success",
        "message": f"✅ Task '{task_id}' cancelled",
        "task_id": task_id,
        "previous_status": current_status
    }


def update_task(params):
    """
    Update a queued task's description, priority, or context.

    Required:
    - task_id: the task to update

    Optional (at least one required):
    - description: new description
    - priority: new priority (high/medium/low)
    - context: new or updated context fields

    Can only update tasks with status 'queued'.
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    new_description = params.get("description")
    new_priority = params.get("priority")
    new_context = params.get("context")

    if not any([new_description, new_priority, new_context]):
        return {"status": "error", "message": "❌ Must provide at least one field to update (description, priority, or context)"}

    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")

    if not os.path.exists(queue_file):
        return {"status": "error", "message": "❌ No task queue found"}

    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading queue: {str(e)}"}

    if task_id not in queue.get("tasks", {}):
        return {"status": "error", "message": f"❌ Task '{task_id}' not found in queue"}

    task = queue["tasks"][task_id]

    if task.get("status") != "queued":
        return {"status": "error", "message": f"❌ Can only update tasks with status 'queued' (current: {task.get('status')})"}

    # Apply updates
    updated_fields = []

    if new_description:
        queue["tasks"][task_id]["description"] = new_description
        updated_fields.append("description")

    if new_priority:
        queue["tasks"][task_id]["priority"] = new_priority
        updated_fields.append("priority")

    if new_context:
        # Merge context instead of replacing
        current_context = queue["tasks"][task_id].get("context", {})
        current_context.update(new_context)
        queue["tasks"][task_id]["context"] = current_context
        updated_fields.append("context")

    queue["tasks"][task_id]["updated_at"] = datetime.now().isoformat()

    try:
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error writing queue: {str(e)}"}

    return {
        "status": "success",
        "message": f"✅ Task '{task_id}' updated",
        "task_id": task_id,
        "updated_fields": updated_fields
    }


def process_queue(params):
    """
    Claude calls this to get all queued tasks.

    Returns list of tasks for Claude to process.
    Claude will then:
    1. Call mark_task_in_progress when starting a task
    2. Execute each task
    3. Call log_task_completion when done
    """
    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")

    if not os.path.exists(queue_file):
        return {
            "status": "success",
            "message": "✅ No tasks in queue",
            "pending_tasks": [],
            "task_count": 0
        }

    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading queue: {str(e)}"}

    # Get queued tasks (not yet started)
    pending = [
        {
            "task_id": task_id,
            "description": task_data["description"],
            "context": task_data.get("context", {}),
            "priority": task_data.get("priority", "medium"),
            "created_at": task_data.get("created_at")
        }
        for task_id, task_data in queue.get("tasks", {}).items()
        if task_data.get("status") == "queued"
    ]

    if not pending:
        return {
            "status": "success",
            "message": "✅ No pending tasks",
            "pending_tasks": [],
            "task_count": 0
        }

    return {
        "status": "success",
        "message": f"Found {len(pending)} pending task(s)",
        "pending_tasks": pending,
        "task_count": len(pending)
    }


def mark_task_in_progress(params):
    """
    Mark a queued task as in_progress.

    Claude calls this when starting work on a task.

    Required:
    - task_id: the task to mark as in_progress
    """
    task_id = params.get("task_id")

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}

    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")

    if not os.path.exists(queue_file):
        return {"status": "error", "message": "❌ No task queue found"}

    try:
        with open(queue_file, 'r', encoding='utf-8') as f:
            queue = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading queue: {str(e)}"}

    if task_id not in queue.get("tasks", {}):
        return {"status": "error", "message": f"❌ Task '{task_id}' not found in queue"}

    task = queue["tasks"][task_id]
    if task["status"] not in ["queued", "in_progress"]:
        return {
            "status": "error",
            "message": f"❌ Task '{task_id}' cannot be marked in_progress (current status: {task['status']})"
        }

    queue["tasks"][task_id]["status"] = "in_progress"
    if "started_at" not in queue["tasks"][task_id]:
        queue["tasks"][task_id]["started_at"] = datetime.now().isoformat()

    try:
        with open(queue_file, 'w', encoding='utf-8') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error writing queue: {str(e)}"}

    return {
        "status": "success",
        "message": f"✅ Task '{task_id}' marked as in_progress"
    }


def execute_queue(params):
    """
    Spawns a Claude Code session to process all queued tasks in the background.

    Returns immediately after spawning the process. The background process will:
    - Process all queued tasks
    - Write results to claude_task_results.json when complete
    - Continue running even if parent process exits

    Claude Code has access to:
    - Bash commands
    - All Orchestrate tools via execution_hub.py
    - File operations (Read, Write, Edit)

    One session processes all tasks. No per-task spawning.
    """
    # CRITICAL: Check if we're already inside Claude Code
    if os.environ.get("CLAUDECODE"):
        return {
            "status": "error",
            "message": "❌ Cannot spawn nested Claude Code session. You're already inside Claude Code. Process tasks directly in the current session instead.",
            "hint": "Read tasks from data/claude_task_queue.json and process them here"
        }

    result = process_queue(params)

    if result.get("task_count", 0) == 0:
        return result

    # Spawn Claude Code session to process queue
    try:
        # Inherit full environment to pass subscription auth
        env = os.environ.copy()

        # CRITICAL: Remove API key to force subscription auth (free) instead of API tokens (costs money)
        env.pop('ANTHROPIC_API_KEY', None)

        # Fetch tool schema from endpoint and inject into prompt
        schema_text = ""
        try:
            schema_response = requests.get('http://localhost:5001/get_supported_actions', timeout=5)
            schema = schema_response.json()
            schema_text = f"""
COMPLETE TOOL SCHEMA (use this for all tool calls):
{json.dumps(schema, indent=2)}

"""
        except Exception as e:
            # Fallback: read system_settings.ndjson directly
            try:
                with open('system_settings.ndjson', 'r') as f:
                    settings = [json.loads(line) for line in f if line.strip()]
                    schema_text = f"""
TOOL SCHEMA (from system_settings.ndjson):
{json.dumps(settings, indent=2)}

"""
            except:
                schema_text = "⚠️ Schema unavailable - read system_settings.ndjson manually if needed.\n\n"

        prompt = f"""{schema_text}Process all tasks in data/claude_task_queue.json. Read data/claude_instructions.md first."""

        # Use -p flag to pass prompt directly (no PTY needed)
        # Start new session so process continues even if parent exits
        process = subprocess.Popen([
            "claude",
            "-p", prompt,
            "--permission-mode", "acceptEdits",
            "--allowedTools", "Bash,Read,Write,Edit"
        ],
        env=env,
        cwd=os.getcwd(),
        stdout=subprocess.DEVNULL,  # Discard output since we're not waiting
        stderr=subprocess.DEVNULL,  # Discard errors since we're not waiting
        start_new_session=True  # Detach from parent process
        )

        # Return immediately with task_started status
        return {
            "status": "task_started",
            "message": f"✅ Claude Code session started in background to process {result['task_count']} task(s)",
            "task_count": result['task_count'],
            "pid": process.pid,
            "note": "Process is running in background. Check results with get_all_results or check_task_status."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to spawn Claude Code session: {str(e)}"
        }


def log_task_completion(params):
    """
    Claude calls this when a task is complete.

    Required:
    - task_id: the task that was completed
    - status: "done" or "error"
    - actions_taken: list of what Claude did

    Optional:
    - output: any data produced
    - output_summary: human-readable summary
    - errors: if status is "error", what went wrong
    - execution_time_seconds: how long it took
    """
    task_id = params.get("task_id")
    status = params.get("status")
    actions_taken = params.get("actions_taken", [])
    output = params.get("output", {})
    output_summary = params.get("output_summary")
    errors = params.get("errors")
    execution_time = params.get("execution_time_seconds", 0)

    if not task_id:
        return {"status": "error", "message": "❌ Missing required field: task_id"}
    if not status:
        return {"status": "error", "message": "❌ Missing required field: status"}

    # Update queue status
    queue_file = os.path.join(os.getcwd(), "data/claude_task_queue.json")
    if os.path.exists(queue_file):
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)

            if task_id in queue.get("tasks", {}):
                queue["tasks"][task_id]["status"] = status
                queue["tasks"][task_id]["completed_at"] = datetime.now().isoformat()

                with open(queue_file, 'w', encoding='utf-8') as f:
                    json.dump(queue, f, indent=2)
        except Exception as e:
            # Non-critical, continue
            print(f"Warning: Could not update queue: {e}", file=sys.stderr)

    # Write result
    results_file = os.path.join(os.getcwd(), "data/claude_task_results.json")

    # Load existing results
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read results file: {e}", file=sys.stderr)
            results = {"results": {}}
    else:
        results = {"results": {}}

    # Generate output_summary if not provided
    if not output_summary:
        output_summary = "Task completed" if status == "done" else "Task failed"

    # Add result
    results["results"][task_id] = {
        "status": status,
        "completed_at": datetime.now().isoformat(),
        "execution_time_seconds": execution_time,
        "actions_taken": actions_taken,
        "output": output,
        "output_summary": output_summary,
        "errors": errors
    }

    # Save results
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error writing results: {str(e)}"}

    return {
        "status": "success",
        "message": f"✅ Task '{task_id}' completion logged with status: {status}",
        "output_summary": output_summary
    }



def batch_assign_tasks(params):
    """
    Assign multiple tasks at once.

    GPT calls this with a list of tasks to assign them all in one go.
    Each task is independently validated and dispatched.

    Required:
    - tasks: list of task dicts, each with task_id, description, priority (optional), context (optional)

    Returns:
    - success_count: how many tasks were successfully added
    - failed_count: how many failed
    - details: per-task results with errors if any
    - summary: human-readable summary

    Example:
    {
        "tasks": [
            {"task_id": "task_1", "description": "Do thing 1", "priority": "high"},
            {"task_id": "task_2", "description": "Do thing 2", "context": {"extra": "info"}}
        ]
    }
    """
    tasks = params.get("tasks")

    if not tasks:
        return {"status": "error", "message": "❌ Missing required field: tasks (must be a list)"}

    if not isinstance(tasks, list):
        return {"status": "error", "message": "❌ tasks must be a list of task dictionaries"}

    if len(tasks) == 0:
        return {"status": "error", "message": "❌ tasks list is empty"}

    results = []
    success_count = 0
    failed_count = 0

    for i, task in enumerate(tasks):
        task_id = task.get("task_id")

        # Validate task structure
        if not isinstance(task, dict):
            results.append({
                "index": i,
                "task_id": None,
                "status": "error",
                "message": "❌ Task must be a dictionary"
            })
            failed_count += 1
            continue

        if not task_id:
            results.append({
                "index": i,
                "task_id": None,
                "status": "error",
                "message": "❌ Task missing required field: task_id"
            })
            failed_count += 1
            continue

        # Use auto_execute=False to prevent spawning for each task
        task_params = task.copy()
        task_params["auto_execute"] = False

        # Call assign_task for each task
        try:
            result = assign_task(task_params)
            if result.get("status") == "success":
                success_count += 1
                results.append({
                    "index": i,
                    "task_id": task_id,
                    "status": "success",
                    "message": f"✅ Task {task_id} queued"
                })
            else:
                failed_count += 1
                results.append({
                    "index": i,
                    "task_id": task_id,
                    "status": "error",
                    "message": result.get("message", "Unknown error")
                })
        except Exception as e:
            failed_count += 1
            results.append({
                "index": i,
                "task_id": task_id,
                "status": "error",
                "message": f"❌ Exception: {str(e)}"
            })

    # Generate summary
    summary = f"Assigned {success_count}/{len(tasks)} tasks successfully"
    if failed_count > 0:
        summary += f" ({failed_count} failed)"

    return {
        "status": "success" if success_count > 0 else "error",
        "message": f"✅ {summary}" if success_count > 0 else f"❌ {summary}",
        "success_count": success_count,
        "failed_count": failed_count,
        "total_tasks": len(tasks),
        "details": results,
        "summary": summary
    }

def get_task_results(params):
    """
    Get recent task execution data with optional markdown table formatting.

    Follows jarvis.py pattern: offload rendering to script, not AI.

    Optional:
    - format: "table" for markdown table + session stats, "json" for raw data (default: json)
    - limit: number of recent tasks to show (default: 10)

    Returns:
    - If format="table": pre-formatted markdown with execution data and session stats
    - If format="json": raw results data for programmatic access
    """
    output_format = params.get("format", "json")
    limit = params.get("limit", 10)

    results_file = os.path.join(os.getcwd(), "data/claude_task_results.json")

    if not os.path.exists(results_file):
        if output_format == "table":
            return {
                "status": "success",
                "formatted_output": "## Recent Execution Data\n\nNo task results yet."
            }
        else:
            return {
                "status": "success",
                "results": {},
                "task_count": 0
            }

    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"❌ Error reading results: {str(e)}"}

    all_results = results.get("results", {})

    if output_format == "json":
        # Return raw data
        return {
            "status": "success",
            "results": all_results,
            "task_count": len(all_results)
        }

    # Format as markdown table
    if not all_results:
        return {
            "status": "success",
            "formatted_output": "## Recent Execution Data\n\nNo completed tasks found."
        }

    # Sort by completion time (most recent first) and limit
    sorted_tasks = sorted(
        all_results.items(),
        key=lambda x: x[1].get("completed_at", ""),
        reverse=True
    )[:limit]

    # Build markdown table
    markdown_lines = ["## Recent Execution Data\n"]
    markdown_lines.append("| Task ID | Status | Execution Time | Human Equivalent | Speed Multiplier |")
    markdown_lines.append("|---------|--------|----------------|------------------|------------------|")

    total_time = 0
    success_count = 0
    total_human_time = 0

    for task_id, task_data in sorted_tasks:
        status = task_data.get("status", "unknown")
        exec_time = task_data.get("execution_time_seconds", 0)

        # Format execution time
        if exec_time >= 60:
            time_str = f"{int(exec_time // 60)}m {int(exec_time % 60)}s"
        else:
            time_str = f"{int(exec_time)}s"

        # Estimate human equivalent (conservative: 15x multiplier for most tasks)
        human_hours = exec_time * 15 / 3600
        if human_hours < 1:
            human_str = f"~{int(human_hours * 60)}min"
        else:
            human_str = f"~{human_hours:.1f}h"

        # Calculate speed multiplier
        speed_mult = "15x"

        # Track stats
        total_time += exec_time
        total_human_time += exec_time * 15
        if status == "done":
            success_count += 1

        # Add row
        markdown_lines.append(f"| {task_id[:30]} | {status} | {time_str} | {human_str} | {speed_mult} |")

    # Add session stats
    markdown_lines.append("\n**Session Stats:**")
    markdown_lines.append(f"- Tasks completed: {success_count}/{len(sorted_tasks)}")

    avg_time = total_time / len(sorted_tasks) if sorted_tasks else 0
    if avg_time >= 60:
        avg_str = f"{int(avg_time // 60)}m {int(avg_time % 60)}s"
    else:
        avg_str = f"{int(avg_time)}s"
    markdown_lines.append(f"- Average execution time: {avg_str}")

    success_rate = (success_count / len(sorted_tasks) * 100) if sorted_tasks else 0
    markdown_lines.append(f"- Success rate: {success_rate:.0f}%")

    # Total time saved
    time_saved_hours = (total_human_time - total_time) / 3600
    markdown_lines.append(f"- Total time saved: ~{time_saved_hours:.1f} hours")

    # Cost analysis
    markdown_lines.append("\n**Cost Analysis:**")
    session_cost = len(sorted_tasks) * 0.02
    api_cost_low = len(sorted_tasks) * 2
    api_cost_high = len(sorted_tasks) * 5
    savings_mult = api_cost_low / session_cost if session_cost > 0 else 0

    markdown_lines.append(f"- Session cost: ${session_cost:.2f}")
    markdown_lines.append(f"- API equivalent: ${api_cost_low:.2f}-${api_cost_high:.2f}")
    markdown_lines.append(f"- Savings: {savings_mult:.0f}x")

    formatted_output = "\n".join(markdown_lines)

    return {
        "status": "success",
        "formatted_output": formatted_output,
        "task_count": len(sorted_tasks)
    }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('action')
    parser.add_argument('--params')
    args = parser.parse_args()

    params = json.loads(args.params) if args.params else {}

    # Route to correct function
    actions = {
        'assign_task': assign_task,
        'assign_demo_task': assign_demo_task,
        'batch_assign_tasks': batch_assign_tasks,
        'check_task_status': check_task_status,
        'get_task_result': get_task_result,
        'get_task_results': get_task_results,
        'get_all_results': get_all_results,
        'ask_claude': ask_claude,
        'cancel_task': cancel_task,
        'update_task': update_task,
        'process_queue': process_queue,
        'execute_queue': execute_queue,
        'mark_task_in_progress': mark_task_in_progress,
        'log_task_completion': log_task_completion
    }

    if args.action in actions:
        result = actions[args.action](params)
    else:
        result = {
            'status': 'error',
            'message': f'Unknown action: {args.action}',
            'available_actions': list(actions.keys())
        }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
