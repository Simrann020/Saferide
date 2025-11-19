FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY crash.csv ./crash.csv
COPY .env ./.env
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create data directory (will be empty initially, but script can write to it)
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["./entrypoint.sh"]
