import os
import json
import argparse
import pdfplumber
import docx
import pandas as pd
from bs4 import BeautifulSoup

ALLOWED_DIRS = {
    'dropzone': '/orchestrate_user/dropzone',
    'system_docs': '/opt/orchestrate-core-runtime/system_docs'
}

def extract_pdf(path):
    try:
        with pdfplumber.open(path) as pdf:
            return '\n'.join(page.extract_text() or '' for page in pdf.pages)
    except Exception as e:
        return f"❌ PDF read error: {str(e)}"

def extract_docx(path):
    try:
        doc = docx.Document(path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"❌ DOCX read error: {str(e)}"

def extract_csv(path):
    try:
        df = pd.read_csv(path)
        return df.to_string(index=False)
    except Exception as e:
        return f"❌ CSV read error: {str(e)}"

def extract_html(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            return soup.get_text()
    except Exception as e:
        return f"❌ HTML read error: {str(e)}"

def extract_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"❌ Text read error: {str(e)}"

def read_file(params):
    folder = params.get('folder', 'dropzone')
    filename = params.get('filename')

    if folder not in ALLOWED_DIRS:
        return {'status': 'error', 'message': f'❌ Unknown folder: {folder}'}

    dir_path = ALLOWED_DIRS[folder]

    if not os.path.isdir(dir_path):
        return {'status': 'error', 'message': f'❌ Folder path does not exist: {dir_path}'}

    if filename:
        safe_name = os.path.basename(filename)
        path = os.path.join(dir_path, safe_name)
        if not os.path.isfile(path):
            return {'status': 'error', 'message': f'❌ File not found: {safe_name} in {folder}'}
    else:
        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        if not files:
            return {'status': 'error', 'message': f'❌ No files found in {folder}'}
        files.sort(key=lambda f: os.path.getmtime(os.path.join(dir_path, f)), reverse=True)
        path = os.path.join(dir_path, files[0])

    ext = os.path.splitext(path)[1].lower()

    if ext == '.pdf':
        content = extract_pdf(path)
    elif ext == '.docx':
        content = extract_docx(path)
    elif ext in ['.csv', '.tsv']:
        content = extract_csv(path)
    elif ext == '.html':
        content = extract_html(path)
    else:
        content = extract_text(path)

    return {
        'status': 'success',
        'filename': os.path.basename(path),
        'data': content
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action')
    parser.add_argument('--params', type=str)
    args = parser.parse_args()

    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError:
        print(json.dumps({'status': 'error', 'message': '❌ Invalid JSON.'}, indent=4))
        return

    if args.action == 'read_file':
        result = read_file(params)
    else:
        result = {'status': 'error', 'message': f'❌ Unknown action: {args.action}'}

    print(json.dumps(result, indent=4))

if __name__ == '__main__':
    main()
