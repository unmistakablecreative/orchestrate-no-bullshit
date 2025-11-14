import os
import sys
import json
import subprocess
import pdfplumber
import docx
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIRECTORIES = [
    "/orchestrate_user/dropzone",
    "/opt/orchestrate-core-runtime/system_docs"
]

def find_file(filename_fragment):
    matches = []

    for base_path in BASE_DIRECTORIES:
        result = subprocess.run(
            ['find', base_path, '-iname', f'*{filename_fragment}*'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout:
            lines = result.stdout.strip().splitlines()
            matches.extend(lines)

    if matches:
        return {
            "match_count": len(matches),
            "matches": matches,
            "selected": matches[0]
        }
    else:
        return {
            "error": f"No file matching '{filename_fragment}' found in known directories."
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

def read_file(filename_fragment):
    match = find_file(filename_fragment)
    path = match.get("selected")
    if not path:
        return {"error": "No matching file found to read."}

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
        "filename": os.path.basename(path),
        "extension": ext,
        "content": content
    }

def main():
    try:
        action = sys.argv[1]
        params = {}

        if "--params" in sys.argv:
            idx = sys.argv.index("--params")
            raw = sys.argv[idx + 1]
            params = json.loads(raw)

        filename = params.get("filename")
        destination_dir = params.get("destination_dir")
        new_name = params.get("new_name")

        if action == "find_file":
            print(json.dumps(find_file(filename)))
        elif action == "read_file":
            print(json.dumps(read_file(filename)))
        elif action == "rename_file":
            print(json.dumps(rename_file(filename, new_name)))
        elif action == "move_file":
            print(json.dumps(move_file(filename, destination_dir)))
        else:
            print(json.dumps({"error": f"Unknown action '{action}'"}))

    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()

