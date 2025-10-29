FROM python:3.11

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY backend/ .

CMD gunicorn app:app --bind 0.0.0.0:$PORT
