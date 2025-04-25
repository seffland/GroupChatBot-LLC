FROM python:3.13-alpine
# Install sqlite for CLI and compatibility
RUN apk add --no-cache sqlite sqlite-dev
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
