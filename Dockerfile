FROM python:3.13-alpine

# tzdata needed for TZ env var to work in Alpine
RUN apk add --no-cache tzdata

# Run as non-root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Create data directory for state persistence
RUN mkdir -p /data && chown appuser:appgroup /data
VOLUME /data

# Copy application
RUN mkdir -p /app && chown appuser:appgroup /app
COPY --chown=appuser:appgroup run.py /app/run.py
COPY --chown=appuser:appgroup cf_access_alert/ /app/cf_access_alert/
RUN chmod 500 /app/run.py

USER appuser
WORKDIR /app

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python3", "/app/run.py"]