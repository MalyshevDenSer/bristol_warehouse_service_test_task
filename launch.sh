#!/bin/bash

PROJECT_NAME=bristol-wh
COMPOSE_FILES=(-f launch/docker-compose.yml -f launch/docker-compose.override.yml)

# Запускаем тесты
docker compose --project-name "$PROJECT_NAME" --env-file .env "${COMPOSE_FILES[@]}" up --build -d

## Читаем логи tests после выполнения
#echo -e "\n\033[1;44m ============ ЛОГИ КОНТЕЙНЕРА TESTS ============ \033[0m\n"
#docker compose --project-name "$PROJECT_NAME" --env-file .env "${COMPOSE_FILES[@]}" logs -f tests
#
## Удаляем контейнеры и тома
#docker compose --project-name "$PROJECT_NAME" --env-file .env "${COMPOSE_FILES[@]}" down -v
