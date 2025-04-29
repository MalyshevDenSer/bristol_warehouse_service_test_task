#!/bin/bash

PROJECT_NAME=bristol-wh
COMPOSE_FILES=(-f launch/docker-compose.yml -f launch/docker-compose.override.yml)


docker compose --project-name "$PROJECT_NAME" --env-file .env "${COMPOSE_FILES[@]}" down -v