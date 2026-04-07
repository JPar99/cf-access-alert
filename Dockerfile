FROM python:3.13-alpine

# Build argument: version string injected by CI from the git tag.
# When not provided (e.g. local `make dev` builds), the env var below
# stays empty and banner.py falls through to reading the VERSION file.
ARG VERSION=""

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
COPY --chown=appuser:appgroup VERSION /app/VERSION
RUN chmod 500 /app/run.py

USER appuser
WORKDIR /app

ENV PYTHONUNBUFFERED=1
# Stamp the image with the build-arg version when CI provided one.
# Empty value means banner.py reads the VERSION file inside the image instead.
ENV CF_ACCESS_ALERT_VERSION=${VERSION}

# Health check — no HTTP port, just checks state file freshness
HEALTHCHECK --interval=60s --timeout=5s --start-period=120s --retries=3 \
    CMD ["python3", "/app/cf_access_alert/healthcheck.py"]

ENTRYPOINT ["python3", "/app/run.py"]