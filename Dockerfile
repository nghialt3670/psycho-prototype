FROM python:3.9-slim

WORKDIR /app

# Copy requirements.txt first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Expose port for the server
EXPOSE 5000

# Run the server
CMD ["python", "server.py"] 