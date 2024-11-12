FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Simplified command using threading
CMD exec gunicorn --workers 1 --threads 8 --timeout 0 --bind :$PORT main:app