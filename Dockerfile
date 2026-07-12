FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# Run headless — no display available inside the container
ENV HEADLESS=true

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
