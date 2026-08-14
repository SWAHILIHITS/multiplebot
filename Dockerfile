FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 8080

# Launch bot in background and Gunicorn web server in foreground
CMD ["sh", "-c", "python3 bot.py & gunicorn -b 0.0.0.0:8080 app:app"]
 python:3.12-slim
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD python3 bot.py
