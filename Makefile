# SES Mail Dashboard - Makefile de despliegue
# ============================================

.PHONY: help start start-local stop restart logs status build db-init clean

# Colores para mensajes
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Mostrar esta ayuda
	@echo "$(GREEN)SES Mail Dashboard - Comandos disponibles:$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker (producción):$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

start: ## Iniciar todo con Docker (DB + backend + frontend)
	@echo "$(GREEN)Iniciando servicios con Docker...$(NC)"
	docker-compose up -d --build
	@echo "$(GREEN)Servicios iniciados:$(NC)"
	@echo "  Frontend: http://localhost:8080"
	@echo "  Backend:  http://localhost:8000"
	@echo "  DB:       localhost:5432"

start-local: ## Iniciar en modo desarrollo local
	@echo "$(GREEN)Iniciando en modo local...$(NC)"
	@echo "$(YELLOW)Verificando PostgreSQL...$(NC)"
	@pg_isready -q || (echo "$(RED)Error: PostgreSQL no está ejecutándose$(NC)" && exit 1)
	@echo "$(YELLOW)Iniciando backend...$(NC)"
	@cd backend && source venv/bin/activate && export $$(cat .env | xargs) && uvicorn main:app --reload --port 8000 &
	@echo "$(YELLOW)Iniciando frontend...$(NC)"
	@cd frontend && python -m http.server 8088 &
	@echo "$(GREEN)Servicios locales iniciados:$(NC)"
	@echo "  Frontend: http://localhost:8088"
	@echo "  Backend:  http://localhost:8000"

stop: ## Detener todos los servicios Docker
	@echo "$(RED)Deteniendo servicios...$(NC)"
	docker-compose down
	@echo "$(GREEN)Servicios detenidos$(NC)"

restart: ## Reiniciar todos los servicios Docker
	@echo "$(YELLOW)Reiniciando servicios...$(NC)"
	docker-compose down
	docker-compose up -d --build
	@echo "$(GREEN)Servicios reiniciados$(NC)"

logs: ## Ver logs de todos los servicios
	docker-compose logs -f

status: ## Ver estado de los servicios
	@echo "$(GREEN)Estado de los servicios:$(NC)"
	@docker-compose ps

build: ## Construir imágenes Docker
	@echo "$(GREEN)Construyendo imágenes...$(NC)"
	docker-compose build
	@echo "$(GREEN)Imágenes construidas$(NC)"

db-init: ## Inicializar la base de datos
	@echo "$(GREEN)Inicializando base de datos...$(NC)"
	@docker-compose exec db psql -U user -d ses_dashboard -f /docker-entrypoint-initdb.d/init.sql
	@echo "$(GREEN)Base de datos inicializada$(NC)"

clean: ## Eliminar contenedores, volúmenes e imágenes
	@echo "$(RED)Eliminando todo...$(NC)"
	docker-compose down -v --rmi all
	@echo "$(GREEN)Limpieza completada$(NC)"
