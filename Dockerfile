FROM python:3.11-slim

WORKDIR /app

# Install runtime tools used for healthchecks and ad-hoc debugging from
# inside the container (the slim base image ships neither).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
# CA-021: model is downloaded from HuggingFace Hub at build time.
# No integrity hash is checked here — the sentence-transformers package version
# in requirements.txt pins the library; the model weights are fetched from the
# hub on each fresh build.  For a fully reproducible build, pre-download the
# model and COPY it in, then set SENTENCE_TRANSFORMERS_HOME=/app/models.
ENV SENTENCE_TRANSFORMERS_HOME=/app/models
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy app
COPY . .

EXPOSE 8000

# Marks the container "healthy" only once /status answers 200. Long
# start_period covers FAISS bootstrap + clause seed on first boot.
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/status > /dev/null || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
