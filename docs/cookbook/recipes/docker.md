# Docker Integration

Use FlavorPack packages in Docker containers for minimal, secure deployments.

## Why Use .psp Files with Docker?

- **Smaller images**: No Python runtime needed in container
- **Faster builds**: No pip install step
- **Reproducible**: Exact same binary everywhere
- **Secure**: Pre-signed, verified packages

## Basic Pattern

```dockerfile
FROM alpine:latest

# Copy the pre-built package
COPY dist/myapp.psp /app/myapp.psp

# Make executable
RUN chmod +x /app/myapp.psp

# Run it
ENTRYPOINT ["/app/myapp.psp"]
```

## Multi-Stage Build

```dockerfile
# Stage 1: Build the package
FROM python:3.11-slim AS builder

WORKDIR /build
COPY . .

# Install FlavorPack
RUN pip install flavorpack

# Build helpers
RUN make build-helpers

# Package the application
RUN flavor pack --manifest pyproject.toml --output myapp.psp

# Stage 2: Minimal runtime
FROM alpine:latest

COPY --from=builder /build/myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp

EXPOSE 8000
CMD ["/app/myapp.psp"]
```

## With Environment Variables

```dockerfile
FROM alpine:latest

COPY myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp

ENV PORT=8000
ENV LOG_LEVEL=info

EXPOSE 8000
CMD ["/app/myapp.psp"]
```

```bash
# Run with custom env vars
docker run -e PORT=3000 -e LOG_LEVEL=debug myapp:latest
```

## Volume Mounts for Data

```dockerfile
FROM alpine:latest

COPY myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp

# Create volume mount points
VOLUME ["/data"]

CMD ["/app/myapp.psp"]
```

```bash
# Run with volume
docker run -v $(pwd)/data:/data myapp:latest
```

## Docker Compose

```yaml
version: '3.8'

services:
  api:
    image: myapp:latest
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=info
      - DATABASE_URL=postgresql://db/myapp
    volumes:
      - ./config:/config:ro
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Best Practices

### 1. **Use Scratch or Alpine**

```dockerfile
# Minimal footprint
FROM scratch
COPY myapp.psp /myapp.psp
ENTRYPOINT ["/myapp.psp"]

# Or Alpine for shell access
FROM alpine:latest
COPY myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp
CMD ["/app/myapp.psp"]
```

### 2. **Non-Root User**

```dockerfile
FROM alpine:latest

RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

COPY --chown=appuser:appuser myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp

USER appuser
CMD ["/app/myapp.psp"]
```

### 3. **Health Checks**

```dockerfile
FROM alpine:latest
COPY myapp.psp /app/myapp.psp
RUN chmod +x /app/myapp.psp

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -q --spider http://localhost:8000/health || exit 1

CMD ["/app/myapp.psp"]
```

## See Also

- **[CI/CD Integration](ci-cd/)**
- **[Multi-Platform Builds](multi-platform/)**
