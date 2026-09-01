#!/bin/bash
# ============================================
# SES Mail Dashboard - Script de despliegue
# ============================================

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Función de ayuda
show_help() {
    echo -e "${GREEN}SES Mail Dashboard - Script de despliegue${NC}"
    echo ""
    echo "Uso: ./scripts/deploy.sh [comando]"
    echo ""
    echo "Comandos:"
    echo "  start         Iniciar todo con Docker"
    echo "  start-local   Iniciar en modo desarrollo local"
    echo "  stop          Detener servicios Docker"
    echo "  restart       Reiniciar servicios Docker"
    echo "  logs          Ver logs de servicios"
    echo "  status        Ver estado de servicios"
    echo "  build         Construir imágenes Docker"
    echo "  clean         Eliminar todo (contenedores, volúmenes, imágenes)"
    echo "  help          Mostrar esta ayuda"
}

# Verificar Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker no está instalado${NC}"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker no está ejecutándose${NC}"
        exit 1
    fi
}

# Verificar docker-compose
check_compose() {
    if docker compose version &> /dev/null; then
        COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE="docker-compose"
    else
        echo -e "${RED}Error: docker-compose no está instalado${NC}"
        exit 1
    fi
}

# Comando: start
cmd_start() {
    check_docker
    check_compose
    echo -e "${GREEN}Iniciando servicios con Docker...${NC}"
    $COMPOSE up -d --build
    echo -e "${GREEN}Servicios iniciados:${NC}"
    echo "  Frontend: http://localhost:8080"
    echo "  Backend:  http://localhost:8000"
    echo "  DB:       localhost:5432"
}

# Comando: start-local
cmd_start_local() {
    echo -e "${GREEN}Iniciando en modo local...${NC}"
    
    # Verificar PostgreSQL
    if ! pg_isready -q 2>/dev/null; then
        echo -e "${RED}Error: PostgreSQL no está ejecutándose${NC}"
        exit 1
    fi
    
    # Verificar venv
    if [ ! -d "backend/venv" ]; then
        echo -e "${YELLOW}Creando entorno virtual...${NC}"
        cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cd ..
    fi
    
    echo -e "${YELLOW}Iniciando backend...${NC}"
    cd backend && source venv/bin/activate && export $(cat .env | xargs) && uvicorn main:app --reload --port 8000 &
    BACKEND_PID=$!
    
    echo -e "${YELLOW}Iniciando frontend...${NC}"
    cd frontend && python -m http.server 8088 &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}Servicios locales iniciados:${NC}"
    echo "  Frontend: http://localhost:8088"
    echo "  Backend:  http://localhost:8000"
    echo ""
    echo "Presiona Ctrl+C para detener"
    
    # Manejar señal de interrupción
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
}

# Comando: stop
cmd_stop() {
    check_docker
    check_compose
    echo -e "${RED}Deteniendo servicios...${NC}"
    $COMPOSE down
    echo -e "${GREEN}Servicios detenidos${NC}"
}

# Comando: restart
cmd_restart() {
    check_docker
    check_compose
    echo -e "${YELLOW}Reiniciando servicios...${NC}"
    $COMPOSE down
    $COMPOSE up -d --build
    echo -e "${GREEN}Servicios reiniciados${NC}"
}

# Comando: logs
cmd_logs() {
    check_docker
    check_compose
    $COMPOSE logs -f
}

# Comando: status
cmd_status() {
    check_docker
    check_compose
    echo -e "${GREEN}Estado de los servicios:${NC}"
    $COMPOSE ps
}

# Comando: build
cmd_build() {
    check_docker
    check_compose
    echo -e "${GREEN}Construyendo imágenes...${NC}"
    $COMPOSE build
    echo -e "${GREEN}Imágenes construidas${NC}"
}

# Comando: clean
cmd_clean() {
    check_docker
    check_compose
    echo -e "${RED}Eliminando todo...${NC}"
    $COMPOSE down -v --rmi all
    echo -e "${GREEN}Limpieza completada${NC}"
}

# Main
case "${1:-help}" in
    start)
        cmd_start
        ;;
    start-local)
        cmd_start_local
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    build)
        cmd_build
        ;;
    clean)
        cmd_clean
        ;;
    help|*)
        show_help
        ;;
esac
