FROM python:3.10-slim

# Install system dependencies cleanly
RUN apt-get update && apt-get install -y \
    build-essential gcc python3-dev libffi-dev libc-dev \
    curl jq unzip gettext git nodejs npm \
    && apt-get clean

# Install ngrok safely
RUN curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list \
    && apt-get update && apt-get install -y ngrok \
    && apt-get clean

# Isolated Netlify install (no root config pollution)
RUN npm config set prefix /usr/local && npm install -g netlify-cli

# Upgrade pip + Python packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir \
    watchdog fastapi uvicorn pydantic requests \
    beautifulsoup4 python-dotenv pyyaml python-multipart \
    astor oauthlib requests-oauthlib pdfplumber python-docx \
    pandas lxml

# Install Claude Code CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Create working dir
RUN mkdir -p /opt/orchestrate-core-runtime
WORKDIR /opt/orchestrate-core-runtime

# Copy all files from repo into container
COPY . /opt/orchestrate-core-runtime/

# Entry handled externally
ENTRYPOINT ["/bin/bash", "/opt/orchestrate-core-runtime/entrypoint.sh"]
