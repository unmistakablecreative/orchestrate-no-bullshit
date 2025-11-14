import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import inspect
import argparse
import importlib


def main(params):
    load_result = load_actions(params)
    if load_result['status'] != 'success':
        return load_result
    batch = load_result['data']
    if batch.get('status') != 'ready':
        return {'status': 'error', 'message': '❌ Batch not ready.'}
    results = []
    touched_files = set()
    for i, action in enumerate(batch['actions']):
        if i > 0:
            action['params']['_prev_results'] = results
        dispatch_result = dispatch_action(action)
        results.append(dispatch_result)
        try:
            filename = action['params']['filename']
            touched_files.add(filename)
        except KeyError:
            pass
    print('\n--- Real File Outputs ---')
    for filename in touched_files:
        file_result = read_file(filename)
        print(f'\n📂 {filename}:')
        print(json.dumps(file_result.get('content', {}), indent=4))
    return {'status': 'success', 'results': results}


def dispatch_action(params):
    try:
        tool_name = params['tool_name']
        action_name = params['action']
        action_params = params['params']
        tool_module = importlib.import_module(f'tools.{tool_name}')
        action_func = getattr(tool_module, action_name)
        result = action_func(action_params)
        return result
    except Exception as e:
        return {'status': 'error', 'message': f'❌ Dispatch failed: {str(e)}'}


DEFAULT_TEMPLATE_DIR = (
    '/Users/srinivas/Orchestrate Github/orchestrate-jarvis/compositions/')


def load_actions(params):
    filename = params.get('filename')
    folder_path = params.get('template_dir', os.path.join(os.getcwd(),
        'compositions'))
    try:
        if filename:
            filepath = os.path.join(folder_path, filename)
            if not os.path.exists(filepath):
                return {'status': 'error', 'message':
                    f'❌ File not found: {filepath}'}
            with open(filepath, 'r') as f:
                data = json.load(f)
            if 'entries' in data and 'status' in data['entries']:
                data = data['entries']
            return {'status': 'success', 'data': data}
        for filename in os.listdir(folder_path):
            if filename.endswith('.json'):
                filepath = os.path.join(folder_path, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                if 'entries' in data and 'status' in data['entries']:
                    data = data['entries']
                if data.get('status') == 'ready':
                    return {'status': 'success', 'data': data}
        return {'status': 'error', 'message': '❌ No ready file found.'}
    except Exception as e:
        return {'status': 'error', 'message':
            f'❌ Failed to load actions: {str(e)}'}


def read_file(filename):
    filepath = os.path.join(DEFAULT_TEMPLATE_DIR, filename)
    if not os.path.exists(filepath):
        return {'status': 'error', 'message': f'❌ File not found: {filename}'}
    if os.path.getsize(filepath) == 0:
        return {'status': 'error', 'message': f'⚠️ File is empty: {filename}'}
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            content = json.load(f)
            return {'status': 'success', 'content': content}
        except json.JSONDecodeError as e:
            return {'status': 'error', 'message':
                f'❌ JSON decode error in {filename}: {str(e)}'}


def cli_main():
    parser = argparse.ArgumentParser(description='Orchestrate Dispatcher CLI')
    parser.add_argument('action', help='Action to perform')
    parser.add_argument('--params', type=str, required=False, help=
        'JSON-encoded parameters for the action')
    args = parser.parse_args()
    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError:
        print(json.dumps({'status': 'error', 'message':
            '❌ Invalid JSON format.'}, indent=4))
        return
    if args.action == 'dispatch_batch':
        result = main(params)
    else:
        result = {'status': 'error', 'message':
            f'❌ Unknown action: {args.action}'}
    print(json.dumps(result, indent=4))


if __name__ == '__main__':
    cli_main()
