FROM python:3.11-slim

WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend files
COPY frontend/ ./frontend/

CMD gunicorn app:app --bind 0.0.0.0:$PORT
