# SES Mail Dashboard

Dashboard interno tipo bandeja de correo para visualizar correos enviados desde **Amazon SES**.

---

## 📁 Estructura del proyecto

```
ses-dashboard/
├── backend/
│   ├── main.py               # Punto de entrada FastAPI
│   ├── requirements.txt
│   ├── Dockerfile             # Multi-stage build, usuario no-root
│   ├── .dockerignore
│   ├── .env.example
│   ├── pytest.ini             # Configuración de tests
│   ├── db/
│   │   └── database.py       # Pool de conexiones asyncpg
│   ├── models/
│   │   └── schemas.py        # Modelos Pydantic
│   ├── routers/
│   │   ├── auth.py           # Login JWT
│   │   └── emails.py         # Endpoints de correos
│   └── tests/
│       ├── conftest.py       # Fixtures de testing
│       ├── test_auth.py      # Tests de autenticación
│       ├── test_health.py    # Tests de health check
│       └── test_emails.py    # Tests de endpoints de correo
├── frontend/
│   ├── index.html            # SPA principal (login + inbox)
│   ├── analytics.html        # Página de analíticas
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── config.js         # Configuración centralizada
│       ├── charts.js         # Gráficas y dashboard
│       ├── alerts.js         # Sistema de alertas
│       ├── actions.js        # Acciones sobre correos
│       └── reports.js        # Generación de reportes PDF
├── database/
│   └── init.sql              # Schema + datos de prueba
├── scripts/
│   └── deploy.sh             # Script de despliegue
├── .agents/                  # Skills y agents de calidad
├── Makefile                  # Comandos de despliegue
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🗄️ Estructura real de la base de datos

### Tabla: email_send

```sql
CREATE TABLE IF NOT EXISTS email_send (
    id              SERIAL PRIMARY KEY,
    message_id      TEXT UNIQUE,
    email_to        TEXT NOT NULL,
    subject         TEXT,
    content         TEXT,
    mime_type       TEXT,
    email_from      TEXT,
    has_attachments BOOLEAN DEFAULT FALSE,
    attachments     JSONB,
    status          TEXT NOT NULL DEFAULT 'sent',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

> El status se almacena directamente en la tabla y también se puede derivar
> del último evento en email_events.

### Tabla: email_events

```sql
CREATE TABLE IF NOT EXISTS email_events (
    id            SERIAL PRIMARY KEY,
    email_send_id INTEGER REFERENCES email_send(id) ON DELETE CASCADE,
    event_type    TEXT,    -- send | delivery | bounce | complaint | open | click
    event_data    JSONB,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: email_block

```sql
CREATE TABLE IF NOT EXISTS email_block (
    id         SERIAL PRIMARY KEY,
    email      TEXT UNIQUE,
    reason     TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Cómo se deriva el status

El status visible en el dashboard es el event_type del último evento del correo:

| Último evento | Status mostrado |
| -------------- | --------------- |
| send           | Enviado         |
| delivery       | Entregado       |
| bounce         | Bounce          |
| complaint      | Complaint       |
| open           | Abierto         |
| (sin eventos)  | Enviado         |

---

## 🚀 Inicio rápido

### Opción 1: Docker (recomendado)

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores (ver sección Variables de entorno)

# 2. Iniciar todo
make start
# o
./scripts/deploy.sh start

# 3. Abrir en navegador
# Frontend: http://localhost:8080
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Opción 2: Desarrollo local

```bash
# 1. Configurar variables de entorno
cd backend
cp .env.example .env
# Editar .env con tus valores

# 2. Iniciar backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs) && uvicorn main:app --reload --port 8000

# 3. En otra terminal, iniciar frontend
cd frontend
python -m http.server 8088

# 4. Abrir: http://localhost:8088
```

### Comandos disponibles

```bash
make help          # Ver todos los comandos
make start         # Iniciar con Docker
make start-local   # Iniciar en modo local
make stop          # Detener servicios
make logs          # Ver logs
make status        # Ver estado de servicios
make restart       # Reiniciar servicios
```

---

## 🔌 API REST

| Método | Endpoint                | Descripción                 |
| ------- | ----------------------- | ---------------------------- |
| POST    | /api/auth/login         | Login, retorna JWT           |
| GET     | /api/auth/me            | Info del usuario autenticado |
| GET     | /api/emails             | Lista paginada con filtros   |
| GET     | /api/emails/stats       | Estadísticas globales       |
| GET     | /api/emails/blocked     | Lista de bloqueados          |
| GET     | /api/emails/{id}        | Detalle completo + eventos   |
| GET     | /api/emails/{id}/events | Solo historial de eventos    |

### Parámetros de GET /api/emails

| Parámetro | Tipo | Descripción                          |
| ---------- | ---- | ------------------------------------- |
| page       | int  | Página (default: 1)                  |
| per_page   | int  | Items por página (max 100)           |
| status     | str  | delivered / sent / bounce / complaint |
| email_to   | str  | Búsqueda parcial en destinatario     |
| subject    | str  | Búsqueda parcial en asunto           |
| date_from  | date | Fecha inicio YYYY-MM-DD               |
| date_to    | date | Fecha fin YYYY-MM-DD                  |

Docs interactivas: http://localhost:8000/docs

---

## 🔒 Seguridad del HTML renderizado

Los correos HTML se muestran en un iframe con sandbox restriccivo:

```html
<iframe sandbox="">
```

- ✅ Renderiza CSS, imágenes y layout del correo
- ❌ Bloquea JavaScript
- ❌ Bloquea navegación y links externos
- ❌ Bloquea formularios y popups
- ❌ No comparte mismo-origin con la app principal

---

## ⚙️ Variables de entorno

| Variable         | Descripción                              | Default                    |
| ---------------- | ---------------------------------------- | -------------------------- |
| DATABASE_URL     | Cadena de conexión PostgreSQL            | -                          |
| SECRET_KEY       | Clave para firmar JWT (32+ chars)        | - (requerido)              |
| ADMIN_USER       | Usuario del dashboard                    | admin                      |
| ADMIN_PASSWORD   | Contraseña del dashboard                 | - (requerido)              |
| ALLOWED_ORIGINS  | Orígenes CORS permitidos (coma-separado) | http://localhost:8080,...   |
| POSTGRES_DB      | Nombre de la base de datos               | ses_dashboard              |
| POSTGRES_USER    | Usuario de PostgreSQL                    | user                       |
| POSTGRES_PASSWORD| Contraseña de PostgreSQL                 | - (requerido para Docker)  |

Generar SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📎 Adjuntos (PDFs y archivos)

Los adjuntos se almacenan como metadata JSONB en email_send.attachments.
El dashboard los muestra en el panel de detalle automáticamente.

Formato esperado del campo attachments:

```json
[
  {
    "filename": "factura_1234.pdf",
    "size": 204800,
    "content_type": "application/pdf"
  }
]
```

Iconos por tipo: PDF=📄  Excel=📊  Otros=📎

---

## 🗄️ Índices recomendados (ejecutar en producción)

```sql
CREATE INDEX IF NOT EXISTS idx_email_send_created_at
    ON email_send (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_send_email_to
    ON email_send (email_to);
CREATE INDEX IF NOT EXISTS idx_email_events_send_id
    ON email_events (email_send_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_type
    ON email_events (event_type);
```

---

## 🔮 Mejoras futuras recomendadas

- Gráfico de correos enviados por día (últimos 30 días)
- Tasa de apertura con eventos SNS open
- Alerta automática si bounce rate supera el 5%
- Exportar lista filtrada a CSV
- Multi-usuario con roles admin / viewer
- SSO con Google Workspace (OAuth2)
- Server-Sent Events para ver correos nuevos en tiempo real
- Particionado de email_send por mes para tablas grandes
