FROM python:3.9.19-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --timeout=1000 --retries=5 -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
