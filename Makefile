PROJECT          ?= bristol-wh
PROJECT_TESTS    ?= bristol-wh-tests
ENV_FILE         ?= .env

COMPOSE_BASE     = -f launch/docker-compose.yml
COMPOSE_SVC_OVR  = -f launch/docker-compose.override.yml
COMPOSE_TEST_OVR = -f launch/docker-compose.test.yml

COMPOSE_SVC      = docker compose --project-name $(PROJECT)       --env-file $(ENV_FILE) $(COMPOSE_BASE) $(COMPOSE_SVC_OVR)
COMPOSE_TEST     = docker compose --project-name $(PROJECT_TESTS) --env-file $(ENV_FILE) $(COMPOSE_BASE) $(COMPOSE_TEST_OVR)

.PHONY: up down test test-down


## up: Собрать и запустить сервис
up:
	@echo "▶️  Запуск приложения..."
	$(COMPOSE_SVC) up --build -d


## down: Остановить сервис и удалить тома
down:
	@echo "🛑 Остановка приложения..."
	$(COMPOSE_SVC) down -v


## test: Запустить интеграционные / e2e тесты в docker-compose
test:
	@echo "🧪  Запуск тестовой среды..."
	$(COMPOSE_TEST) up --build -d
	@echo "\n\033[1;44m ============ ЛОГИ КОНТЕЙНЕРА TESTS ============ \033[0m\n"
	$(COMPOSE_TEST) logs -f tests

## test-down: Остановить тестовые контейнеры и удалить тома
test-down:
	$(COMPOSE_TEST) down -v

