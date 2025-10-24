# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Налаштовуємо змінні середовища
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc g++ make libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо requirements
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 Встановлюємо watchfiles для hot reload
RUN pip install watchfiles

# Створюємо папку для логів
RUN mkdir -p /app/logs

# Створюємо користувача без root-доступу
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

USER botuser

# Команда за замовчуванням (перевизначена в docker-compose)
CMD ["python", "-m", "app.main"]