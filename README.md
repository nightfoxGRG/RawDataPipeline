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

- `.xlsx` (лист `tables_config`, либо единственный лист)
- `.yaml` / `.yml`
- `.json`
- `.toml`
- `.ini`

## Что проверяется

- Дубликаты таблиц
- Дубликаты колонок внутри таблицы
- Имена таблиц/колонок/FK в формате PostgreSQL (`[A-Za-z_][A-Za-z0-9_]*`)
- Использование зарезервированных слов PostgreSQL
