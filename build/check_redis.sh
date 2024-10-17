#!/bin/bash

echo "=================================================="
echo "Starting the Redis check script..."
echo "=================================================="

# Количество попыток проверки порта
MAX_ATTEMPTS=5
ATTEMPT=1

# Проверка, занят ли порт 6379 на сервисе redis с использованием nmap
while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  if nmap -p 6379 -T4 -oG - redis | grep -q '6379/open'; then
    echo "Redis is already running on port 6379. Exiting..."
    exit 1
  else
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Redis is not running on port 6379. Retrying..."
    ATTEMPT=$((ATTEMPT+1))
    sleep 2
  fi
done

echo "=================================================="
echo "Starting Redis..."
echo "=================================================="
# Использование встроенного docker-entrypoint.sh для запуска Redis
exec docker-entrypoint.sh redis-server
