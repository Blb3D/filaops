# FilaOps Backend - Python FastAPI
# Multi-stage build for smaller final image

# ===================
# Stage 1: Build
# ===================
# Pin to bookworm to ensure Microsoft ODBC compatibility
FROM python:3.11-slim-bookworm as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver for SQL Server
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql17 \
        unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies to /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===================
# Stage 2: Runtime
# ===================
FROM python:3.11-slim-bookworm

# Build arguments for version injection
ARG VERSION=dev
ARG COMMIT=unknown
ARG BUILD_DATE

# Set environment variables for version tracking
ENV FILAOPS_VERSION=${VERSION}
ENV FILAOPS_COMMIT=${COMMIT}
ENV FILAOPS_BUILD_DATE=${BUILD_DATE}

# Create non-root user first
RUN useradd --create-home --shell /bin/bash filaops

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver (runtime only)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql17 \
        libodbc1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder to system location (accessible by all users)
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=filaops:filaops . .

# Create uploads and logs directories with proper permissions
RUN mkdir -p /app/uploads/quotes /app/logs && chown -R filaops:filaops /app/uploads /app/logs

# Switch to non-root user
USER filaops

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
