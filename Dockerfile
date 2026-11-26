FROM python:3.12-slim

LABEL maintainer="Guy Sheffer <guysoft@gmail.com>"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=80

# unzip is used by pyunpack to extract Beat Saber map archives
RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /powerbeatsvr

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY setup.py README.md ./
COPY src/powerbeatsvr ./src/powerbeatsvr
RUN pip install --no-cache-dir .

COPY src/app /app
RUN mkdir -p /app/uploads /app/static/downloads \
    && chmod 777 /app/uploads /app/static/downloads

WORKDIR /app
EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "--timeout", "600", "--access-logfile", "-", "main:app"]
