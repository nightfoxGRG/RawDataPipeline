"""
Запуск миграций БД через yoyo-migrations.
Использование:
    python migrate.py             # применить все новые миграции
    python migrate.py rollback    # откатить последнюю миграцию
    python migrate.py list        # показать статус миграций
"""
import sys
from pathlib import Path

from config.config_loader import load_config
from services.dbmigrate.db_migrate import build_dsn
from yoyo import read_migrations, get_backend
def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else 'apply'
    cfg = load_config()
    dsn = build_dsn(cfg.get('database', {}))
    migrations_dir = str(Path(__file__).parent / 'migrations')
    migrations = read_migrations(migrations_dir)
    backend = get_backend(dsn)
    with backend.lock():
        if command == 'apply':
            to_apply = backend.to_apply(migrations)
            pending = list(to_apply)
            if not pending:
                print('Нет новых миграций.')
                return
            print(f'Применяю {len(pending)} миграций...')
            backend.apply_migrations(backend.to_apply(migrations))
            print('Готово.')
        elif command == 'rollback':
            to_rollback = backend.to_rollback(migrations)
            steps = list(to_rollback)
            if not steps:
                print('Нечего откатывать.')
                return
            print(f'Откатываю: {steps[0].id}')
            backend.rollback_migrations(to_rollback)
            print('Готово.')
        elif command == 'list':
            applied = {m.id for m in backend.get_applied_migration_hashes(migrations)}
            print(f'{"ID":<40} {"Статус"}')
            print('-' * 55)
            for m in migrations:
                status = 'применена' if m.id in applied else 'ожидает'
                print(f'{m.id:<40} {status}')
        else:
            print(f'Неизвестная команда: {command}')
            print('Доступные команды: apply, rollback, list')
            sys.exit(1)
if __name__ == '__main__':
    main()
