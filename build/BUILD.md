# Сборка RawDataPipeline для локального запуска

## Что получается

| Платформа | Результат                       | Запуск                              |
|-----------|---------------------------------|-------------------------------------|
| macOS     | `dist/RawDataPipeline.app`      | двойной клик или `open dist/RawDataPipeline.app` |
| Windows   | `dist/RawDataPipeline.exe`      | двойной клик                        |

При запуске:
1. Создаётся пользовательский каталог:
   - macOS/Linux: `~/.config/RawDataPipeline/`
   - Windows: `%APPDATA%\RawDataPipeline\`
2. Туда копируется `config.local.toml` (шаблон).
3. Открывается браузер на `http://127.0.0.1:8080`.
4. Если в config-файле не заполнены параметры БД — открывается onboarding-форма `/setup`.

После заполнения и сохранения формы — применяются миграции и приложение готово к работе.

---

## Локальный режим — что отключено

| Подсистема    | Server-режим              | Local-режим                                   |
|---------------|---------------------------|-----------------------------------------------|
| Авторизация   | Keycloak (OIDC)           | Без авторизации; пользователь = LOCAL_USER    |
| Файлы конфиг. | MinIO                     | Файловая система `~/.config/RawDataPipeline/table_configs/` |
| Настройки БД  | Управление списком в UI   | Read-only из config.local.toml                |
| LibreTranslate| URL из config             | Так же из config (как в server)               |

---

## Требования

```bash
pip install -r requirements.txt
pip install pyinstaller
```

---

## Сборка на macOS

```bash
cd /Volumes/External_SSD/work/projects/RawDataPipeline

pyinstaller build/RawDataPipeline.spec

# Запуск
open dist/RawDataPipeline.app
# или
./dist/RawDataPipeline
```

## Сборка на Windows

> Сборка под Windows должна выполняться **на Windows**.

```cmd
cd C:\путь\до\RawDataPipeline

pyinstaller build\RawDataPipeline.spec

dist\RawDataPipeline.exe
```

---

## Запуск из исходников (server-режим)

```bash
python app.py
```

По умолчанию режим `server` — нужен Keycloak и MinIO. Чтобы запустить локально из
исходников (без Keycloak/MinIO), укажите режим явно:

```bash
APP_MODE=local python app.py
```

---

## Советы

- **Консольное окно** в `RawDataPipeline.spec`: `console=True` оставляет видимый
  терминал (полезно для отладки). Установите `console=False` для скрытия.
- **Иконка** — раскомментируйте `icon=` в spec.
- **Где править параметры БД после сборки** — `~/.config/RawDataPipeline/config.local.toml`
  или через onboarding-форму на `/setup`, или кнопкой "Открыть config в редакторе"
  в Параметризаторе.
