# Сборка исполняемого файла TableCreator

## Что получится

| Платформа | Результат                     | Запуск                        |
|-----------|-------------------------------|-------------------------------|
| macOS     | `dist/TableCreator.app`       | двойной клик или `open dist/TableCreator.app` |
| Windows   | `dist/TableCreator.exe`       | двойной клик                  |

При запуске автоматически откроется браузер по адресу `http://127.0.0.1:8080`.

---

## Требования

```bash
pip install pyinstaller
```

---

## Сборка на macOS

```bash
cd /Volumes/External_SSD/work/projects/TableCreator

# Установить зависимости (если не установлены)
pip install -r requirements.txt
pip install pyinstaller

# Собрать
pyinstaller TableCreator.spec

# Запустить
open dist/TableCreator.app
# или
./dist/TableCreator
```

## Сборка на Windows

> **Важно:** сборку нужно выполнять **на той же платформе**, на которой будет запускаться файл.  
> Exe под Windows собирается на Windows, .app под macOS — на macOS.

```cmd
cd C:\путь\до\TableCreator

pip install -r requirements.txt
pip install pyinstaller

pyinstaller TableCreator.spec

dist\TableCreator.exe
```

---

## Структура после сборки

```
dist/
  TableCreator          ← исполняемый файл (macOS/Linux)
  TableCreator.exe      ← исполняемый файл (Windows)
  TableCreator.app/     ← .app bundle для macOS
```

---

## Советы

- **Консольное окно** — в `TableCreator.spec` параметр `console=True` показывает терминал (удобно для отладки). Установите `console=False` чтобы скрыть.
- **Иконка** — раскомментируйте строку `icon=` в spec-файле и укажите путь к `.ico` (Windows) или `.icns` (macOS).
- **Антивирус** — на Windows некоторые антивирусы могут блокировать PyInstaller-файлы. Это ложное срабатывание.
- **Размер файла** — обычно 30–60 МБ, так как внутри упакован интерпретатор Python.

