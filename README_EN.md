
# DataPipelinePro / RawDataPipeline

A Flask web application for building a raw data ingestion pipeline into PostgreSQL: from inferring table structure based on a sample file to loading data into the database and analyzing data quality.

Includes six tools organized into a unified workflow:

1. **Parametrizer** — management of database connections, credentials, and projects (schemas).
2. **Configurator** — defining table structure from an uploaded file/directory and generating a configuration file.
3. **SQL Generator** — generating a `CREATE TABLE` SQL script from a configuration file and optionally executing it on the working database.
4. **Router** — configuring "source column → table column" mappings with transformation functions.
5. **Loader** — loading data from files into project tables based on saved routes.
6. **Analyzer** — detecting duplicates and assessing data quality in loaded tables.

---

## Features

### 🗂️ Parametrizer (`/parametrizer`)

Central control screen for project and connection management.

- **Database settings** (db_setting): CRUD list of connections (label, host, port, name) with uniqueness validation on the `(host, port, name)` triple.
- **Connection credentials** (db_setting_credential): each user has their own login/password for each connection. The "Test connection" button performs a real `psycopg2.connect` (you can test either with an entered password or with a stored one).
- **Projects** (project): code, description, link to a connection, schema name in the database. Schema name validation (`^[a-z][a-z0-9_]*$`, minimum 2 characters, reserved names forbidden: `public`, `pg_catalog`, `information_schema`, `pg_toast`, `raw_data_pipline_schema`).
- **Actual project**: each user selects their own active project (user_setting.actual_project_id) — it determines which schema the other tools will access.
- **Project badge highlighting in the header**: after switching projects, the top badge updates with the project code and a tooltip with DSN and schema.
- In **local mode**, login/credentials blocks are hidden (single-user scenario); the "Connection settings" button leads to the first-run form `/setup`.

### 🔍 Configuration file generator (Configurator, `/configurator` and `/`)

- Accepts data files in `.xlsx`, `.xlsm`, `.csv` formats.
- First row of the file — column headers (names in any language, including Russian).
- Supports two upload scenarios:
  - **Single file** — `POST /table_config_generator`: a single table schema is generated.
  - **Directory** — `POST /table_config_generator_from_directory`: batch processing, a single configuration file can contain up to 5 table blocks (v2 format).
- Automatically **translates column and table names into English** via the LibreTranslate service.
- **Detects PostgreSQL type** for each column based on data content:
  - `boolean` — if all values are `true`/`false`
  - `date` — if all values match `YYYY-MM-DD` format
  - `timestamp` — if any values include time `YYYY-MM-DD HH:MM...`
  - `integer` / `bigint` — integers (up to/exceeding 2,147,483,647)
  - `numeric(p,s)` — fractional numbers with calculated precision and scale
  - `varchar(N)` — strings up to 255 characters (length rounded up to a multiple of 50)
  - `text` — strings longer than 255 characters or columns with no data
- Forms a **SQL identifier name** from each header: translates, removes invalid characters, converts to `snake_case`. A DB field named `id` is automatically renamed to `source_id` (reserved name — the project has its own auto-generated `id`).
- Generates a configuration file in the **`tables_config_v2`** format (`.xlsm`) based on the `TablesConfig.xlsm` template.
- Stores the generated file in **MinIO** (or in the local directory `~/.config/RawDataPipeline/table_configs/` in local mode); the reference is saved in `project.table_config_minio_id`.
- **Configuration validation**:
  - `GET /table_config_validate_system` — validates the file already linked to the project.
  - `POST /table_config_validate_local` — validates a locally selected file before uploading.
- **Download/re-download**:
  - `GET /table_config_download_system` — download the active project config.
  - `GET /download_table_config_template` — download an empty `TablesConfig.xlsm` template.
- If the translation service is unavailable, displays a clear message with the LibreTranslate URL.

### ⚙️ SQL Generator (`/generator`, `/sql`)

- Accepts configuration files in `.xlsx`, `.xlsm`, `.json` formats.
- Parses table descriptions in two Excel formats:
  - **v1** (sheet `tables_config`) — vertical blocks
  - **v2** (sheet `tables_config_v2`) — horizontal blocks
- Supports **JSON description** of tables (`tables_config` format).
- Generates a **correct SQL script** `CREATE TABLE` for PostgreSQL:
  - Data types with size: `varchar(N)`, `numeric(p,s)`, etc.
  - Constraints: `NOT NULL`, `UNIQUE`, `PRIMARY KEY`, `DEFAULT`, `REFERENCES`
  - `DEFAULT` values are formatted according to type (numbers — unquoted, strings — in quotes, SQL constants `NULL`, `TRUE`, `FALSE`, `now()`, etc. — as-is)
  - Column alignment and comments with display name
- **Optional technical columns** (checkboxes on the form):
  - `id bigserial primary key` — auto-generated surrogate key.
  - `__source text` — source file name.
  - `__package_id text` — load package identifier.
  - `__package_timestamp timestamptz default now()` — load timestamp.
- **SQL execution in the working database** (`POST /sql_execute`) — DDL is executed against the active project schema.
- **Validates** the configuration before generation:
  - Duplicate tables and columns
  - Names of tables/columns/foreign keys in PostgreSQL format (`[A-Za-z_][A-Za-z0-9_]*`)
  - Use of PostgreSQL reserved words
  - Correctness of foreign key references (format `table(column)`)
  - Correctness of `DEFAULT` values for the column type
- Displays SQL right on the page.
- Allows **downloading the template** `TablesConfig.xlsm` for manual filling.
- Allows **downloading the generated SQL** as a `tables.sql` file.

### 🔀 Router (`/router`)

Mapping "source file column → DB table column" — defines exactly how data should be loaded.

- **Route auto-generation** (`POST /source_to_table/generate_from_config`): from the project's configuration file, `source_to_table_config` records (one per table) are automatically created with the flag `is_auto_generated=True`, and `source_to_table` records are created for each column (one-to-one by name).
- **Manual route editing** (visual editor on jsplumb):
  - `GET /source_to_table/schema/tables` — list of base tables in the project schema (taken directly from `information_schema`).
  - `GET /source_to_table/schema/table-configs` — list of routes for the selected table.
  - `POST /source_to_table/schema/table-configs` — create a new route (name, code, description, mapping type, chunk_size).
  - `PATCH /source_to_table/schema/table-configs/<id>` — rename/update description.
  - `GET /source_to_table/schema/mapping` — get field mappings.
  - `POST /source_to_table/schema/mapping` — save all route mappings.
  - `DELETE /source_to_table/schema/mapping` — delete all mappings.
- **Mapping types** (`map_type`):
  - `MAP_BY_COLUMN_NAME` — matching by column name in the file.
  - `MAP_BY_COLUMN_NUMBER` — matching by ordinal column number.
- **Transformation functions** (can be applied to each target column):
  - `SERIAL` — auto-increment (internal load counter).
  - `PACKAGE_TIMESTAMP` — package timestamp.
  - `PACKAGE_ID` — load package identifier.
  - `SOURCE` — source file name.
  - empty value — take the source column value as-is.

### 📦 Loader (`/loader`)

Loading data into project tables. Two modes:

- **Loading from a directory using the project's main config**
  `POST /loader/load_by_table_config_from_directory` — for each file from the selected directory, the system:
  1. Downloads the project's .xlsm config from MinIO.
  2. By the `original_name` field, finds the table block matching the file name.
  3. Finds an auto-generated route (`is_auto_generated=True`) for this table.
  4. Runs `LoaderService.load()` — streaming file read, column mapping, type validation, chunked `INSERT`.
- **Loading with route selection**
  `POST /loader/directory/load` — the user picks a `source_to_table_config` themselves (for example, to load a "non-standard" file into an existing table through a different mapping).
- **Progress and errors**: returns the number of loaded rows per file or a list of errors (type mismatch, missing required column, conversion problem).
- **Supported data formats**: `.xlsx`, `.xlsm`, `.csv` (with auto-detection of encoding and delimiter for CSV: UTF-8/BOM, UTF-8, CP1251, latin-1; comma, semicolon, tab, pipe).
- **Chunked insertion**: chunk size is set on the route (`chunk_size`) — allows loading large files without memory overflow.
- **On-the-fly value validation**: each row is checked for conformance to the declared column type (int, numeric, bool, date, timestamp).

### 🔬 Analyzer (`/analyzer`)

Detecting duplicates and checking data quality in loaded tables.

- `GET /analyzer/tables` — list of available tables in the project schema.
- `POST /analyzer/run` — select one or more tables + chunk size, start the analysis.
- The result is an Excel report `.xlsx` with a separate sheet per table: grouping keys, match count, row similarity metric.
- The algorithm works in chunks to avoid loading the database and to handle tables with tens of millions of rows.

### 👤 Authentication and multi-user mode (server only)

- **Keycloak OAuth2 / OIDC**:
  - `GET /login` — redirect to `oauth.keycloak.authorize_redirect()`.
  - `GET /callback` — code handling, token exchange, user upsert by `email` (`subject_id`).
  - `GET /logout` — session cleanup + Keycloak logout with `post_logout_redirect_uri`.
- Working database credentials (`db_setting_credential`) are stored **per user** — a single project can be shared by different people with different DB privileges.
- All of this is disabled in local mode: a single `LOCAL_USER`, no authentication required.

### 🖥️ Run modes

- **Server mode** (`APP_MODE=server`, default)
  - Launched via Flask / WSGI / Docker; Keycloak + MinIO; multi-user; `config.toml` + optional `config.local.toml`.
  - Main area background — white, mode badge — pink.
- **Local mode** (`APP_MODE=local` or PyInstaller bundle, `sys.frozen=True`)
  - Single-user (`LOCAL_USER`), no Keycloak/MinIO; the config lives in `~/.config/RawDataPipeline/config.local.toml` (or `%APPDATA%\RawDataPipeline\` on Windows); configuration files — in `~/.config/RawDataPipeline/table_configs/`.
  - On first launch, the onboarding form `/setup` opens (host, port, database name, schema, login/password, LibreTranslate URL). After saving, migrations are applied automatically and the initial `db_setting` is created.
  - Background — light blue, mode badge — blue; no user block in the sidebar.
  - On macOS, a splash window with a progress indicator is shown for module loading and Flask startup; proper "Quit" item in the Dock via NSApplication.

---

## Launch

### From sources (server mode, development)

```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
flask --app app run --port 8080
```

Open `http://127.0.0.1:8080`.

### From sources (local mode, without Keycloak/MinIO)

```bash
APP_MODE=local python run_app.py
```

On first launch, the `/setup` form will open — fill in PostgreSQL parameters.

### Translation service (LibreTranslate)

For automatic translation of column headers from Russian to English, a running instance of [LibreTranslate](https://libretranslate.com/) is required.

The service URL is set in the `config.toml` file:

```toml
[translation]
libretranslate_url = "http://127.0.0.1:50001"
api_key = ""   # optional
```

Launch via Docker Compose:

```bash
docker compose -f docker/libretranslate.yml up -d
```

### PostgreSQL, MinIO, Keycloak (server mode)

In the `docker/` directory, compose files for the entire infrastructure are provided — see `docker/запуск`.

---

## Building an executable

The application can be packaged into a standalone executable for macOS and Windows using [PyInstaller](https://pyinstaller.org/):

```bash
pyinstaller build/RawDataPipeline.spec
```

Artifacts:

| Platform  | Result                          | Launch                                              |
|-----------|---------------------------------|-----------------------------------------------------|
| macOS     | `dist/RawDataPipeline.app`      | double click or `open dist/RawDataPipeline.app`     |
| Windows   | `dist/RawDataPipeline.exe`      | double click                                        |

The built file does not require Python installation and runs in **local mode**.

Details — `build/BUILD.md`.

---

## Configuration

### `resources/config.toml` (base, always read)

```toml
[app]
project_name = "RawDataPipeline"
secret_key = "..."

[database]          # working DB (project metadata + working schemas)
host = "localhost"
port = 5432
name = "raw_data_pipeline"
schema = "raw_data_pipline_schema"
user = "postgres"
password = "..."

[translation]
libretranslate_url = "http://127.0.0.1:50001"
api_key = ""

[minio]             # server mode only
endpoint = "localhost:50002"
access_key = "..."
secret_key = "..."

[keycloak]          # server mode only
server_url = "http://localhost:50004"
realm = "master"
client_id = "raw-data-pipeline"
client_secret = "..."
```

### `config.local.toml` (override)

- In **server mode**, it is read when `APP_ENV=local` from `resources/config.local.toml`.
- In **local mode**, it is read from `~/.config/RawDataPipeline/config.local.toml` (or `%APPDATA%\RawDataPipeline\config.local.toml`). Created automatically on first launch.
- Values are **deep-merged** on top of the base `config.toml`.

---

## Supported configuration formats

### Excel v1 (sheet `tables_config`)

Each table is a vertical block. The first row of the block is the table name, followed by attribute rows:

| Row (column A)             | Required | Description                                            |
|----------------------------|:---:|-------------------------------------------------------|
| Table name                 | ✔   | Table name in DB; value — in columns B+               |
| DB column code             | ✔   | Column codes (one per column, starting from B)        |
| Type                       | ✔   | PostgreSQL data type                                  |
| Size                       |     | E.g. `50` or `10,2`                                   |
| Description                |     | Display name of the column                            |
| Mandatory                  |     | `да` — NOT NULL                                       |
| Unique                     |     | `да` — UNIQUE                                         |
| Primary key                |     | `да` — PRIMARY KEY                                    |
| Foreign key                |     | Reference in the format `table(column)`               |
| Default value              |     | DEFAULT value for the column                          |

### Excel v2 (sheet `tables_config_v2`)

Tables are horizontal blocks, separated by an empty column. Each column is a separate row.

**Row 1** — table name. **Row 2** — attribute headers. **Rows 3+** — column data.

| Header (row 2)            | Required | Description                                   |
|---------------------------|:---:|-----------------------------------------------|
| Description               | ✔   | Block start marker; column display name       |
| DB column code            | ✔   | DB column code                                |
| Type                      | ✔   | PostgreSQL data type                          |
| Size                      |     | E.g. `50` or `10,2`                           |
| Mandatory                 |     | `да` — NOT NULL                               |
| Unique                    |     | `да` — UNIQUE                                 |
| Primary key               |     | `да` — PRIMARY KEY                            |
| Foreign key               |     | Reference in the format `table(column)`       |
| Default value             |     | DEFAULT value for the column                  |

### JSON

```json
{
  "tables_config": [
    {
      "table_name": "users",
      "columns": [
        {
          "column_code": "id",
          "type": "bigserial",
          "nullable": false,
          "primary_key": true
        },
        {
          "column_code": "email",
          "type": "varchar",
          "size": "255",
          "nullable": false,
          "unique": true,
          "column_name": "Email"
        },
        {
          "column_code": "role_id",
          "type": "bigint",
          "nullable": true,
          "foreign_key": "roles(id)"
        }
      ]
    }
  ]
}
```

The `tables_config` field is a list of objects or a dictionary `{ "table_name": { columns } }`.

| Column field   | Type    | Description                                          |
|----------------|---------|------------------------------------------------------|
| `column_code`  | string  | DB column code (required)                            |
| `type`         | string  | PostgreSQL data type (required)                      |
| `size`         | string  | Size, e.g. `"255"` or `"10,2"`                       |
| `nullable`     | bool    | `true` — allows NULL (default `true`)                |
| `unique`       | bool    | `true` — UNIQUE (default `false`)                    |
| `primary_key`  | bool    | `true` — PRIMARY KEY (default `false`)               |
| `foreign_key`  | string  | Reference in the format `table(column)`              |
| `default`      | string  | Default value                                        |
| `column_name`  | string  | Column display name                                  |

---

## PostgreSQL type auto-detection

| Condition                                    | PostgreSQL type     |
|----------------------------------------------|---------------------|
| All values are `true` / `false`              | `boolean`           |
| All values match `YYYY-MM-DD` format         | `date`              |
| Any values include time `YYYY-MM-DD HH:MM…`  | `timestamp`         |
| Integers ≤ 2,147,483,647                     | `integer`           |
| Integers > 2,147,483,647                     | `bigint`            |
| Fractional numbers                           | `numeric(p,s)`      |
| Strings ≤ 255 characters                     | `varchar(N)` (N is a multiple of 50, minimum 50) |
| Strings > 255 characters or empty column     | `text`              |

---

## System database schema

The system schema (`raw_data_pipline_schema` by default) stores the application's metadata:

| Table                      | Purpose                                                                       |
|----------------------------|-------------------------------------------------------------------------------|
| `users`                    | Users (Keycloak subject_id or `LOCAL_USER`); `is_tech_user` flag              |
| `db_setting`               | Connections to working databases (host, port, name, label)                    |
| `db_setting_credential`    | Login/password per pair `(user, db_setting)`                                  |
| `project`                  | Projects: code, description, link to `db_setting`, schema name, config reference (`table_config_minio_id`) |
| `user_setting`             | Active project per user (`actual_project_id`)                                 |
| `source_to_table_config`   | Load routes: table name, code, mapping type, chunk size, auto-generated flag  |
| `source_to_table`          | Route fields: source column/number, target column, transformation function    |

Migrations are applied automatically (yoyo-migrations); files are in `resources/migrations/`. The system table `_yoyo_migration` is also created in the system schema.

---

## External integrations

| Service             | Purpose                                                              | When needed              |
|---------------------|----------------------------------------------------------------------|--------------------------|
| **PostgreSQL**      | Primary storage: system tables + project schemas                     | always                   |
| **LibreTranslate**  | Translate Russian column headers into snake_case names for the DB    | when using the Configurator |
| **MinIO** (S3)      | Storage for `.xlsm` configuration files (server mode)                | server only              |
| **Keycloak** (OIDC) | Authentication and SSO                                               | server only              |

---

## Architecture

```
src/
├── app.py                       # Flask routes, app factory, middleware
├── run_app.py                   # PyInstaller entry-point (local mode)
├── common/                      # utilities: contexts, errors, paths, decorators
├── config/                      # AppMode, config_loader, keycloak, migrations, ORM/engine
└── domains/                     # business domains (by feature, not by technical layer)
    ├── db_setting/              # connections
    ├── db_setting_credential/   # credentials
    ├── project/                 # projects (schema namespace)
    ├── users/                   # users + user_setting (active project)
    ├── configurator/            # structure inference from files
    ├── generator/               # CREATE TABLE SQL
    ├── source_to_table/         # load routes + manual mapping
    ├── loader/                  # loading data into the DB
    ├── analyzer/                # duplicate analysis
    ├── libretranslate/          # translation
    ├── minio/                   # object storage
    └── working_db/              # executing queries in the project schema
```

Each domain consists of three files: `*_service.py` (Flask endpoint wrappers and business logic), `*_repository.py` (database access), `*_model.py` (SQLAlchemy ORM).

---

## Tests

```bash
pytest tests/
```

Tests use `testcontainers[postgres]` to spin up a temporary PostgreSQL instance.
