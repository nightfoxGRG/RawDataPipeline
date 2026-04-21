# TableCreator

Веб-приложение на Flask для генерации SQL-скрипта создания таблиц PostgreSQL из настроечного файла (`tables_config`).

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```

Откройте `http://127.0.0.1:5000`, загрузите конфигурационный файл и получите SQL + скачивание `tables.sql`.

## Поддерживаемые форматы

- `.xlsx` / `.xlsm` (лист `tables_config`, либо единственный лист)
- `.json`

## Структура JSON

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
          "unique": false,
          "primary_key": true
        },
        {
          "column_code": "email",
          "type": "varchar",
          "size": "255",
          "nullable": false,
          "unique": true,
          "column_name": "Электронная почта"
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

Поле `tables_config` может быть либо **списком** объектов (как выше), либо **словарём** `{ "table_name": { columns } }`.

| Поле таблицы  | Тип       | Описание                                           |
|---------------|-----------|----------------------------------------------------|
| `table_name`  | string    | Наименование таблицы (обязательное)                |

| Поле колонки  | Тип       | Описание                                           |
|---------------|-----------|----------------------------------------------------|
| `column_code` | string    | Код колонки в БД (обязательное)                    |
| `type`        | string    | Тип данных PostgreSQL (обязательное)               |
| `size`        | string    | Размерность, например `"255"`                      |
| `nullable`    | bool      | `true` — допускает NULL (по умолчанию `true`)      |
| `unique`      | bool      | `true` — уникальное значение (по умолчанию `false`)|
| `primary_key` | bool      | `true` — первичный ключ (по умолчанию `false`)     |
| `foreign_key` | string    | Ссылка в формате `table(column)`                   |
| `default`     | string    | Значение по умолчанию                              |
| `column_name` | string    | Отображаемое наименование колонки                  |

## Что проверяется

- Дубликаты таблиц
- Дубликаты колонок внутри таблицы
- Имена таблиц/колонок/FK в формате PostgreSQL (`[A-Za-z_][A-Za-z0-9_]*`)
- Использование зарезервированных слов PostgreSQL
