# Synthetic test runtime recipe. Build was NOT performed in OpenCode.
# Pin base image digest and OS package versions before a repeatable deployment.
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver ca-certificates fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 11001 --create-home browser-test \
    && python -m venv /opt/test-venv
ENV PATH="/opt/test-venv/bin:$PATH" \
    CHROME_BINARY="/usr/bin/chromium" \
    CHROMEDRIVER="/usr/bin/chromedriver"
WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY --chown=11001:11001 . /app
RUN mkdir -p /app/artifacts && chown 11001:11001 /app /app/artifacts
USER 11001:11001
CMD ["python", "browser_probe.py", "--run", "--output", "artifacts/browser"]
