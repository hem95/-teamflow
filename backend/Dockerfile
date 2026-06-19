# Start from an official Python image (slim = smaller size)
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements first — Docker caches this layer
# If requirements.txt didn't change, it skips pip install on the next build
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose port 8000 so Docker knows we listen there
EXPOSE 8000

# Start the server
# --host 0.0.0.0 means "listen on all network interfaces" (required in Docker)
# --workers 4 means 4 parallel worker processes (adjust based on CPU cores)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
