# meli-token-manager

Rotación y consumo de tokens de MercadoLibre con sincronización en GCP Secret Manager.

## Funcionalidades
- Bootstrap inicial vía OAuth (interactivo o pasando el code) que guarda tokens en JSON y los sincroniza a GCP Secret Manager.
- Rotación cada 4h (configurable) guardando los tokens localmente y en GCP Secret Manager.
- Creación/actualización de secretos si no existen.
- Helper de acceso que siempre recarga configuración con env-manager antes de leer el secreto, evitando usar tokens caducados.

## Requisitos
- Python 3.11+
- Credenciales de GCP con permisos de Secret Manager (`Secret Manager Admin` para creación, `Secret Manager Secret Accessor` para lectura).
- Variables definidas en `config/config_vars.yaml` (copiar desde `config/config_vars.yaml.example`).
- `SECRET_ORIGIN=gcp` y `GCP_PROJECT_ID` configurados en producción.

## Configuración
1. Copia el ejemplo y completa valores:
   ```bash
   cp config/config_vars.yaml.example config/config_vars.yaml
   ```
2. Asegura las variables obligatorias: `MELI_APP_ID`, `MELI_CLIENT_SECRET`, `MELI_REDIRECT_URI`, `MELI_TOKENS_SECRET_NAME`, `GCP_PROJECT_ID`.
3. Opcionales: `MELI_REFRESH_TOKEN` (solo si ya tienes uno y quieres precargar), `MELI_TOKEN_FILE` (ruta local) y `ROTATION_INTERVAL_SECONDS` (default 14400 = 4h).

## Bootstrap inicial (tokens.json)
- Interactivo (abre URL y pega `code`):
  ```bash
  python -m meli_token_manager.cli init --secret-origin gcp --config /ruta/config/config_vars.yaml
  ```
- Con code ya obtenido:
  ```bash
  python -m meli_token_manager.cli init --secret-origin gcp --config /ruta/config/config_vars.yaml --code "<code>"
  ```
Esto genera `tokens.json` (o la ruta definida en `MELI_TOKEN_FILE`) y crea/actualiza el secreto en GCP.

## Rotación (cron / servicio)
- Loop continuo (recomendado, llamar desde cron `@reboot` o supervisor):
  ```bash
  python -m meli_token_manager.cli rotate --secret-origin gcp --config /ruta/config/config_vars.yaml
  ```
- Una sola ejecución (útil para pruebas o cron cada 4h):
  ```bash
  python -m meli_token_manager.cli rotate --once --secret-origin gcp --config /ruta/config/config_vars.yaml
  ```
- Flags disponibles:
  - `--gcp-project-id` para sobrescribir proyecto.
  - `--interval-seconds` para ajustar el intervalo del loop.

## Acceso al token en cualquier servicio
Cada llamada vuelve a cargar env-manager para evitar valores en caché:
```python
from meli_token_manager import get_access_token

token = get_access_token(
    config_path="/ruta/config/config_vars.yaml",
    secret_origin="gcp",
)
```
Si necesitas el payload completo (incluye `refresh_token`, `expires_at`, etc.):
```python
from meli_token_manager import get_token_payload

tokens = get_token_payload(config_path="/ruta/config/config_vars.yaml", secret_origin="gcp")
```

## Notas
- El refresco escribe un JSON con `access_token`, `refresh_token`, `expires_in`, `expires_at` y metadatos tanto en disco como en el secreto configurado.
- Si no existe el secreto en GCP, se crea automáticamente con replicación automática y se agrega una nueva versión.
- Para inicializar, se usa `MELI_REFRESH_TOKEN` de la configuración si no hay archivo ni secreto previo.
