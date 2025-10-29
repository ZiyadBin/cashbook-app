FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY backend/ .

# Expose the port
EXPOSE $PORT

# Start command
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
