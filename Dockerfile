FROM python:3.11-slim

WORKDIR /app

# Ставим только то, что нужно для работы веб-сервера
RUN pip install --no-cache-dir fastapi uvicorn

# Копируем код нашего сервиса оплаты
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
