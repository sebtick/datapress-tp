# ===== Stage 1: build =====
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /app/site-packages

COPY main.py /app

# ===== Stage 2: runtime (non-root) =====
FROM python:3.12-slim

# Création d'un utilisateur non-root
RUN useradd -m datapress
USER datapress

WORKDIR /app

# Copier uniquement ce qui est nécessaire
COPY --from=builder /app/site-packages /app/site-packages
COPY --from=builder /app/main.py /app

ENV PYTHONPATH=/app/site-packages
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
