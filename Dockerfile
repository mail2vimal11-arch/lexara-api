FROM python:3.11-slim

WORKDIR /app

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
