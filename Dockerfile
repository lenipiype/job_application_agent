FROM python:3.12-slim

# Create a non-privileged system user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and config files
COPY . .

# Ensure appuser owns the application files to perform writes (e.g. creating/updating local sqlite db)
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose the web port for health checking
EXPOSE 10000

CMD ["python", "main.py"]