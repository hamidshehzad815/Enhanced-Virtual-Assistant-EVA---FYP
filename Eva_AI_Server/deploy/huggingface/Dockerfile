# Hugging Face Docker Space — models from HF Hub; Duckling runs in-container on :8000
FROM rasa/duckling:latest AS duckling

FROM python:3.11-slim-bookworm

RUN useradd -m -u 1000 user
ENV PATH="/home/user/.local/bin:$PATH" \
    HF_HOME=/tmp/hf \
    TRANSFORMERS_CACHE=/tmp/hf \
    TORCH_HOME=/tmp/torch \
    PORT=7860 \
    DUCKLING_URL=http://127.0.0.1:8000

WORKDIR /app

# Duckling binary deps (bookworm has OpenSSL 3; duckling binary needs OpenSSL 1.1 from rasa/duckling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgmp10 libpcre3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=duckling /usr/local/bin/duckling-example-exe /usr/local/bin/duckling-example-exe
COPY --from=duckling /usr/lib/x86_64-linux-gnu/libssl.so.1.1 /usr/lib/x86_64-linux-gnu/libssl.so.1.1
COPY --from=duckling /usr/lib/x86_64-linux-gnu/libcrypto.so.1.1 /usr/lib/x86_64-linux-gnu/libcrypto.so.1.1

COPY requirements-hf.txt requirements-hf.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements-hf.txt

COPY --chown=user . /app

ARG HF_MODEL_REPO=hamidshehzad/eva-models
RUN huggingface-cli download "${HF_MODEL_REPO}" --local-dir /app/models && \
    chown -R user:user /app/models

COPY --chown=user start.sh /app/start.sh
RUN chmod +x /app/start.sh

USER user

EXPOSE 7860

CMD ["/app/start.sh"]
