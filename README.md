# SES Mail Dashboard

Dashboard interno tipo bandeja de correo para visualizar correos enviados desde **Amazon SES**.

---

## 📁 Estructura del proyecto

```
ses-dashboard/
├── backend/
│   ├── main.py               # Punto de entrada FastAPI
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── db/
│   │   └── database.py       # Pool de conexiones asyncpg
│   ├── models/
│   │   └── schemas.py        # Modelos Pydantic
│   └── routers/
│       ├── auth.py           # Login JWT
│       └── emails.py         # Endpoints de correos
├── frontend/
│   └── index.html            # SPA completa (sin dependencias de build)
├── database/
│   └── init.sql              # Schema de referencia (no ejecutar en producción)
├── docker-compose.yml
└── README.md
```

---

## 🗄️ Estructura real de la base de datos

### Tabla: email_send
```sql
CREATE TABLE email_send (
    id              BIGSERIAL PRIMARY KEY,
    message_id      VARCHAR(255) UNIQUE,
    email_to        VARCHAR(255) NOT NULL,
    subject         VARCHAR(255),
    content         TEXT,
    mime_type       VARCHAR(100),
    email_from      VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    has_attachments BOOLEAN DEFAULT FALSE,
    attachments     JSONB   -- metadatos de archivos adjuntos (PDF, etc.)
);
```

> ⚠️ La tabla email_send NO tiene columna status.
> El estado se deriva dinámicamente del último evento en email_events.

### Tabla: email_events
```sql
CREATE TABLE email_events (
    id            BIGSERIAL PRIMARY KEY,
    email_send_id BIGINT REFERENCES email_send(id) ON DELETE CASCADE,
    event_type    VARCHAR(50),   -- send | delivery | bounce | complaint | open | click
    event_data    JSONB,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: email_block
```sql
CREATE TABLE email_block (
    id         BIGSERIAL PRIMARY KEY,
    email      VARCHAR(255) UNIQUE,
    reason     VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Cómo se deriva el status
El status visible en el dashboard es el event_type del último evento del correo:

| Último evento  | Status mostrado |
|----------------|----------------|
| send           | Enviado         |
| delivery       | Entregado       |
| bounce         | Bounce          |
| complaint      | Complaint       |
| open           | Abierto         |
| (sin eventos)  | Enviado         |

---

## 🚀 Inicio rápido (desarrollo local)

### 1. Configurar variables de entorno

```bash
cd ses-dashboard/backend
cp .env.example .env
nano .env
```

```env
# Contraseñas con espacios: reemplazar espacio por %20
DATABASE_URL=postgresql://usuario:contraseña@host:5432/email_service
SECRET_KEY=genera-con-el-comando-de-abajo
ADMIN_USER=admin
ADMIN_PASSWORD=tu-contraseña-segura
```

Generar SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Instalar dependencias y levantar backend

```bash
cd ses-dashboard/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Cargar .env y levantar (el export es importante)
export $(cat .env | xargs) && uvicorn main:app --reload --port 8000
```

### 3. Servir el frontend

En otra terminal:
```bash
cd ses-dashboard/frontend
python -m http.server 8088
```

Abrir: http://localhost:8088

### 4. Verificar funcionamiento

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

---

## 🔌 API REST

| Método | Endpoint              | Descripción                        |
|--------|-----------------------|------------------------------------|
| POST   | /api/auth/login       | Login, retorna JWT                 |
| GET    | /api/auth/me          | Info del usuario autenticado       |
| GET    | /api/emails           | Lista paginada con filtros         |
| GET    | /api/emails/stats     | Estadísticas globales              |
| GET    | /api/emails/blocked   | Lista de bloqueados                |
| GET    | /api/emails/{id}      | Detalle completo + eventos         |
| GET    | /api/emails/{id}/events | Solo historial de eventos        |

### Parámetros de GET /api/emails

| Parámetro  | Tipo | Descripción                          |
|------------|------|--------------------------------------|
| page       | int  | Página (default: 1)                  |
| per_page   | int  | Items por página (max 100)           |
| status     | str  | delivered / sent / bounce / complaint|
| email_to   | str  | Búsqueda parcial en destinatario     |
| subject    | str  | Búsqueda parcial en asunto           |
| date_from  | date | Fecha inicio YYYY-MM-DD              |
| date_to    | date | Fecha fin YYYY-MM-DD                 |

Docs interactivas: http://localhost:8000/docs

---

## 🔒 Seguridad del HTML renderizado

Los correos HTML se muestran en un iframe con sandbox:

```html
<iframe sandbox="allow-same-origin">
```

- ✅ Renderiza CSS, imágenes y layout del correo
- ❌ Bloquea JavaScript
- ❌ Bloquea navegación y links externos
- ❌ Bloquea formularios y popups

---

## ⚙️ Variables de entorno

| Variable        | Descripción                        |
|-----------------|------------------------------------|
| DATABASE_URL    | Cadena de conexión PostgreSQL      |
| SECRET_KEY      | Clave para firmar JWT (32+ chars)  |
| ADMIN_USER      | Usuario del dashboard              |
| ADMIN_PASSWORD  | Contraseña del dashboard           |

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