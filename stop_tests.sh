# Удаляем контейнеры и тома
PROJECT_NAME=bristol-wh-tests
COMPOSE_FILES=(-f launch/docker-compose.yml -f launch/docker-compose.test.yml)


docker compose --project-name "$PROJECT_NAME" --env-file .env "${COMPOSE_FILES[@]}" down -v