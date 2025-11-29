# Stage 1: builder
FROM python:3.11-slim as builder
WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
 && python -m pip install --upgrade pip \
 && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels \
 && apt-get remove -y build-essential gcc \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Stage 2: runtime
FROM python:3.11-slim
ENV TZ=UTC
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps: cron, tzdata
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cron tzdata \
 && ln -fs /usr/share/zoneinfo/UTC /etc/localtime \
 && dpkg-reconfigure -f noninteractive tzdata || true \
 && rm -rf /var/lib/apt/lists/*

# copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# copy app code and keys
COPY . /app

# ensure directories and permissions
RUN mkdir -p /data /cron \
 && chown -R root:root /app \
 && chmod -R 755 /app/scripts \
 && chmod 600 /app/student_private.pem || true

# install cron file (use crontab)
RUN chmod 0644 /app/cron/2fa-cron \
 && crontab /app/cron/2fa-cron

EXPOSE 8080

# Entrypoint: start cron then start uvicorn
CMD service cron start && \
    touch /cron/last_code.txt && chmod 644 /cron/last_code.txt && \
    uvicorn app:app --host 0.0.0.0 --port 8080
