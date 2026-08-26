# CI/CD Setup — dgsites-BE

Configuración manual requerida en GitHub y Render para que los workflows
`.github/workflows/ci.yml` y `.github/workflows/deploy.yml` funcionen
correctamente.

---

## 1. Pipeline CI (`ci.yml`)

Se ejecuta en push y PR a `main`, `develop` y `staging`, además de ejecución manual (`workflow_dispatch`).

| Job | Verificaciones | Requerido para merge a `main` |
|-----|----------------|-------------------------------|
| `lint` | `ruff check .` + `mypy app/ main.py` | Sí |
| `test` | `pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=30` | Sí |
| `build` | `py_compile main.py` + verificación de imports (`from main import app`) | Sí |

> **Nota sobre la estructura del código:** La aplicación sigue una arquitectura por capas
> bajo el directorio `app/`: `routers/` (endpoints), `schemas/` (Pydantic), `services/`
> (NASA, Excel) y `validators/` (Colombia). El entry point es `main.py` que monta el
> router de `app.routers.weather`.

### 1.1 Required status checks (branch protection)

En **GitHub → Settings → Branches → Branch protection rules → main**:

1. Marcar **"Require status checks to pass before merging"**.
2. Marcar **"Require branches to be up to date before merging"**.
3. Añadir los checks obligatorios:
   - `Lint (ruff + mypy)`
   - `Test (pytest + coverage)`
   - `Build (syntax + import verification)`
4. Marcar **"Require a pull request before merging"** con al menos **1 approval**.
5. Marcar **"Require conversation resolution before merging"**.

> Los nombres exactos de los checks corresponden al campo `name:` de cada job
> en `ci.yml`. Si se renombran, actualizar aquí también.

---

## 2. Pipeline CD (`deploy.yml`)

Se ejecuta en push a `main` (producción). La rama `develop` ejecuta
únicamente CI (`ci.yml`); no dispara deploy ni consume secrets de Render.

```
push main → validate → tag (SemVer) → deploy-production (trigger Render + smoke GET /health, con aprobación) → release
```

> El job `validate` de `deploy.yml` es **equivalente al CI** (`ci.yml`): ejecuta
> `ruff check .`, `mypy app/ main.py`, `python -m py_compile main.py`,
> `python -c "from main import app"` y `pytest --cov=. --cov-report=term-missing
> --cov-fail-under=30`. Cualquier cambio en CI debe replicarse aquí.

> El job `release` depende de `deploy-production`, no se publica el GitHub
> Release hasta que el deploy a producción se complete exitosamente. Si la
> aprobación se rechaza o el deploy falla, no se crea release público.

> **Smoke check post-deploy:** tras disparar el deploy en Render, el workflow
> captura el `deployId` devuelto por la API, hace polling del estado del deploy
> hasta alcanzar `live` (hasta 10 min) y luego verifica `GET {RENDER_SERVICE_URL}/health`
> esperando `{"status":"healthy"}`. Si `RENDER_SERVICE_URL` no está configurada,
> el job falla explícitamente con un `::error::` indicando cómo añadirla.

### 2.1 GitHub Environments

Crear un environment en **GitHub → Settings → Environments**:

#### `production`
| Setting | Valor |
|---------|-------|
| Deployment branch | `main` |
| Required reviewers | Al menos 1 reviewer |
| Wait timer | Opcional (ej: 60s) |

> El job `deploy-production` usa `environment: production`, por lo que GitHub
> pausará el workflow hasta que un reviewer apruebe el deploy.

> La rama `staging` se usa únicamente como rama de validación CI/PR (ver
> `ci.yml`); no existe environment de staging ni servicio Render de staging.

### 2.2 Secrets por environment

En el environment `production`, configurar las siguientes **secrets** (valores
sensibles, enmascarados en los logs):

| Secret | Environment | Descripción |
|--------|-------------|-------------|
| `RENDER_API_KEY` | `production` | API key de Render |
| `RENDER_SERVICE_ID` | `production` | ID del servicio Render de producción |

> El workflow referencia `secrets.RENDER_SERVICE_ID` directamente; GitHub
> resuelve automáticamente el secret del environment activo (`production`).

Alternativamente, `RENDER_API_KEY` puede configurarse como **repository
secret** si se prefiere mantenerla en un solo lugar.

### 2.3 Variables de entorno por environment (no secretos)

El smoke check post-deploy necesita la URL pública del servicio. Como la URL
**no es sensible**, se configura como **environment variable** (no como secret)
para que sea visible en los logs y diferenciable de las credenciales:

| Variable | Environment | Descripción | Ejemplo |
|----------|-------------|-------------|---------|
| `RENDER_SERVICE_URL` | `production` | URL base pública del servicio de producción | `https://wind-data-api.onrender.com` |

> Configurar en **GitHub → Settings → Environments → `production` → Environment variables**
> (NO en "Environment secrets"). El workflow la referencia como
> `vars.RENDER_SERVICE_URL`. Si falta, el smoke check falla con un `::error::`
> explícito que indica cómo añadirla.

> En Render, la URL pública del servicio se encuentra en la pestaña
> **Settings → Domains** del servicio. Los servicios Free de Render exponen
> `https://<service-name>.onrender.com`.

---

## 3. Render — Configuración del servicio

### 3.1 Servicio de Producción
| Setting | Valor |
|---------|-------|
| Branch | `main` |
| Build Command | `pip install -r requirements.lock` |
| Start Command | `python -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Python Version | 3.11.11 |
| Root Directory | `/` (main.py está en la raíz; `app/` es un paquete Python) |

> El `render.yaml` del repositorio define la configuración del servicio de
> producción, incluyendo `healthCheckPath: /health` para que Render realice
> probes de disponibilidad contra el endpoint `GET /health` (definido en
> `app/routers/health.py`). Confirmar que el health check path del servicio
> en el dashboard también es `/health`.

> No existe servicio de staging en Render. La rama `staging` se usa
> únicamente como rama de validación CI/PR.

---

## 4. Rollback

### 4.1 Rollback de producción
1. Identificar el último tag estable: `git tag --sort=-creatordate | head -5`
2. Revertir el commit en `main` o crear un hotfix branch desde el tag:
   ```bash
   git checkout v1.0.0    # o el último tag estable
   git checkout -b hotfix/revert-issue
   # aplicar fix, commit, PR a main
   ```
3. El push a `main` dispara el pipeline: nuevo tag (patch bump) + deploy.
4. Alternativa rápida: en el dashboard de Render, hacer **Manual Deploy →
   Deploy specific commit** con el SHA del último tag estable.

---

## 5. Versionamiento (SemVer)

- Los tags se generan automáticamente en `deploy.yml` al hacer push a `main`.
- Primer release: `v1.0.0`.
- Bumps: `feat:` → minor, `fix:` → patch (Conventional Commits).
- Cada release incluye release notes autogeneradas por GitHub.
- Los tags son idempotentes: re-ejecutar el workflow no crea tags duplicados.
- **El job `release` depende de `deploy-production`**: no se publica GitHub Release hasta que el deploy a producción se complete exitosamente. Si la aprobación se rechaza o el deploy falla, no se crea release público.

---

## 6. Endpoints de la API (Fase 1)

La aplicación expone dos endpoints bajo el prefijo `/api/v1`:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/weather-data` | Devuelve datos meteorológicos (viento, radiación solar) en JSON |
| POST | `/api/v1/excel-report` | Genera y descarga reporte Excel con datos y gráficos polares (streaming XLSX) |

**Request body** (ambos endpoints):

```json
{
  "station_name": "Bogotá",
  "latitude": 4.6097,
  "longitude": -74.0817,
  "start": "2024-01-01",
  "end": "2024-01-31"
}
```

**Validaciones:**
- Coordenadas dentro del bounding box de Colombia (`-4.23` a `12.44` lat, `-79.09` a `-66.88` lon)
- Fechas no futuras, `start < end`
- `station_name` entre 1 y 200 caracteres

**Códigos de error:**

| Código | Condición |
|--------|----------|
| 422 | Validación de request (campos faltantes, coordenadas fuera de rango, fechas inválidas) |
| 502 | NASA POWER API retorna error |
| 504 | Timeout de conexión a NASA POWER API (30s) |

> **Nota:** Los endpoints obsoletos `POST /generate-files` y `GET /download/{filename}`
> fueron reemplazados por los endpoints actuales en la Fase 1. El archivo
> `generate_excel.py` fue migrado a `app/services/excel.py`.

---

## 6.1 Observabilidad: Correlation ID (X-Request-ID)

Todos los requests pasan por `CorrelationIDMiddleware` (`app/middleware.py`), que
gestiona un ID de correlación por request para trazabilidad distribuida:

| Comportamiento | Descripción |
|----------------|-------------|
| **Request sin `X-Request-ID`** | Genera UUID4 y lo propaga |
| **Request con `X-Request-ID`** | Reutiliza el valor recibido |
| **Logging** | Binda `request_id` a `structlog.contextvars` — todos los logs del request incluyen el ID |
| **Response** | Incluye header `X-Request-ID` con el ID resuelto |

**Ejemplo de log estructurado:**

```json
{"event": "NASA API call", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "level": "info"}
```

**Smoke check post-deploy:** el health check `GET /health` también pasa por el
middleware, por lo que el response incluye `X-Request-ID`. Esto permite verificar
que el middleware está activo y funcionando correctamente tras cada deploy.

---

## 7. Checklist de configuración manual (orden recomendado)

Pasos manuales obligatorios en GitHub y Render antes del primer deploy real.
El pipeline falla explícitamente si falta cualquiera de los marcados con ⛔.

### 7.1 GitHub — Branch protection (`main`)
1. Settings → Branches → Branch protection rules → `main`.
2. Require status checks: `Lint (ruff + mypy)`, `Test (pytest + coverage)`,
   `Build (syntax + import verification)`.
3. Require PR + 1 approval + conversation resolution.

### 7.2 GitHub — Environments
Crear `production` (deployment branch `main`, required reviewers ≥ 1).
La rama `staging` no requiere environment; se usa solo para validación CI/PR.

### 7.3 GitHub — Secrets por environment ⛔
En el environment `production`, añadir **Environment secrets**:
- `RENDER_API_KEY` ⛔ — sin este, el deploy no se dispara.
- `RENDER_SERVICE_ID` ⛔ — sin este, el deploy no se dispara.

### 7.4 GitHub — Variables por environment ⛔
En el environment `production`, añadir **Environment variables** (NO secrets):
- `RENDER_SERVICE_URL` ⛔ — sin este, el smoke check post-deploy falla con
  `::error::RENDER_SERVICE_URL is not set...`. Valor: URL pública del servicio
  Render de producción (p.ej. `https://wind-data-api.onrender.com`).

### 7.5 Render — Servicio
1. Servicio de producción: definido por `render.yaml` (incluye
   `healthCheckPath: /health`). Confirmar que el health check path del servicio
   en el dashboard también es `/health`.
2. Obtener el `Service ID` del servicio (Settings → Service Detail) y
   volcarlo en `RENDER_SERVICE_ID` del environment `production` (7.3).
3. Obtener la URL pública del servicio (Settings → Domains) y volcarla en
   `RENDER_SERVICE_URL` del environment `production` (7.4).

### 7.6 Render — API Key
Generar una API key en Render (Account Settings → API Keys) y guardarla como
`RENDER_API_KEY` en el environment `production` (7.3), o como repository secret.

### 7.7 Verificación previa al primer deploy
- `pip install -r requirements.lock` en Python 3.11 debe completarse sin
  errores (lock reproducible generado con `pip-compile`).
- `ruff check .`, `mypy app/ main.py`, `python -c "from main import app"` y
  `pytest --cov-fail-under=30` deben pasar localmente antes de pushear.
- `GET /health` debe responder `{"status":"healthy"}` en el servicio desplegado.
