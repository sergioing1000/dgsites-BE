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

Se ejecuta en push a `main` (producción) y `develop` (staging).

```
push develop → validate → deploy-staging (automático)
push main    → validate → tag (SemVer) → deploy-production (con aprobación) → release
```

> El job `release` depende de `deploy-production`, no se publica el GitHub
> Release hasta que el deploy a producción se complete exitosamente. Si la
> aprobación se rechaza o el deploy falla, no se crea release público.

### 2.1 GitHub Environments

Crear dos environments en **GitHub → Settings → Environments**:

#### `staging`
| Setting | Valor |
|---------|-------|
| Deployment branch | `develop` |
| Required reviewers | (ninguno — deploy automático) |
| Wait timer | 0 |

#### `production`
| Setting | Valor |
|---------|-------|
| Deployment branch | `main` |
| Required reviewers | Al menos 1 reviewer |
| Wait timer | Opcional (ej: 60s) |

> El job `deploy-production` usa `environment: production`, por lo que GitHub
> pausará el workflow hasta que un reviewer apruebe el deploy.

### 2.2 Secrets por environment

En cada environment, configurar las siguientes secrets:

| Secret | Environment | Descripción |
|--------|-------------|-------------|
| `RENDER_API_KEY` | `staging` | API key de Render (puede ser la misma) |
| `RENDER_SERVICE_ID` | `staging` | ID del servicio Render de staging |
| `RENDER_API_KEY` | `production` | API key de Render (puede ser la misma) |
| `RENDER_SERVICE_ID` | `production` | ID del servicio Render de producción |

> Usar el mismo nombre `RENDER_SERVICE_ID` en ambos environments permite que
> el workflow referencie `secrets.RENDER_SERVICE_ID` sin condicionales.
> GitHub resuelve automáticamente el secret del environment activo.

Alternativamente, `RENDER_API_KEY` puede configurarse como **repository
secret** (compartida) si se prefiere mantenerla en un solo lugar.

---

## 3. Render — Configuración de servicios

### 3.1 Servicio de Staging
| Setting | Valor |
|---------|-------|
| Branch | `develop` |
| Build Command | `pip install -r requirements.lock` |
| Start Command | `python -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Python Version | 3.11.11 |
| Root Directory | `/` (main.py está en la raíz; `app/` es un paquete Python) |

### 3.2 Servicio de Producción
| Setting | Valor |
|---------|-------|
| Branch | `main` |
| Build Command | `pip install -r requirements.lock` |
| Start Command | `python -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Python Version | 3.11.11 |
| Root Directory | `/` (main.py está en la raíz; `app/` es un paquete Python) |

> El `render.yaml` del repositorio define la configuración del servicio de
> producción. El servicio de staging debe crearse manualmente en el dashboard
> de Render (o mediante un segundo `render.yaml` con `env: staging`).

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

### 4.2 Rollback de staging
1. Revertir el commit en `develop`.
2. El push dispara `deploy-staging` automáticamente.
3. Alternativa: Render dashboard → Manual Deploy con commit anterior.

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
