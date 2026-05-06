-- V001__init.sql

create table users
(
    id           bigserial primary key,
    subject_id   varchar(50) not null,
    first_name   varchar(50),
    last_name    varchar(50),
    email        varchar(100),
    is_tech_user boolean     not null default false,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz
);
create unique index idx_users_only_one_local on users (subject_id) where is_tech_user = false;

insert into users (subject_id, first_name, is_tech_user)
values ('LOCAL_USER', 'Локальный пользователь', true);

insert into users (subject_id, first_name, is_tech_user)
values ('TECH_USER', 'Технический пользователь', true);


create table db_setting
(
    id         bigserial primary key,
    user_id    bigint       not null references users (id),
    db_label   varchar(100) not null,
    host       text         not null,
    port       int          not null,
    name       text         not null,
    db_user    text         not null,
    password   text         not null,
    created_at timestamptz  not null default now(),
    created_by bigint       not null references users (id),
    updated_at timestamptz,
    updated_by bigint references users (id)
);


create table project
(
    id                    bigserial primary key,
    code                  varchar(200) not null unique,
    description           text         not null,
    db_setting_id         bigint       not null references db_setting (id),
    schema                varchar(200) not null,
    table_config_minio_id text,
    created_at            timestamptz  not null default now(),
    created_by            bigint       not null references users (id),
    updated_at            timestamptz,
    updated_by            bigint references users (id),

    -- Запрещаем зарезервированные имена
    constraint project_schema_forbidden check (
        schema not in ('public', 'pg_catalog', 'information_schema', 'pg_toast', 'data_pipline_schema')
        ),

    -- Добавляем проверку на нижний регистр, цифры и подчеркивания
    constraint project_schema_lowercase check (schema ~ '^[a-z][a-z0-9_]*$'),

    -- Добавляем проверку на минимальную длину (опционально)
    constraint project_schema_min_length check (length(schema) >= 2)
);
create unique index idx_project_unique on project (db_setting_id, schema);


create table user_setting
(
    id                bigserial primary key,
    user_id           bigint unique not null references users (id),
    actual_project_id bigint references project (id),
    created_at        timestamptz   not null default now(),
    created_by        bigint        not null references users (id),
    updated_at        timestamptz,
    updated_by        bigint references users (id)
);

create table source_to_table_config
(
    id         bigserial primary key,
    project_id bigint       not null references project (id),
    table_name varchar(200) not null,
    map_type   varchar(100),

    CONSTRAINT allowed_map_type CHECK (map_type IN ('MAP_BY_COLUMN_NAME', 'MAP_BY_COLUMN_NUMBER'))
);
create unique index idx_source_to_table_config_unique on source_to_table_config (project_id, table_name);

create table source_to_table
(
    id                        bigserial primary key not null,
    project_id                bigint                not null references project (id),
    table_name                varchar(200)          not null,
    source_column             varchar(200),
    source_column_number      int,
    source_column_order       int                   not null,
    source_column_description varchar(200),
    table_column              varchar(200)          not null,
    function                  varchar(200),
    created_at                timestamptz           not null default now(),
    created_by                bigint                not null references users (id),
    updated_at                timestamptz,
    updated_by                bigint references users (id),

    CONSTRAINT allowed_functions CHECK (
        function IN ('SERIAL', 'PACKAGE_TIMESTAMP', 'PACKAGE_ID')
            OR function IS NULL -- разрешаем NULL значения
        )
);
create unique index idx_source_to_table_table_column_unique on source_to_table (project_id, table_name, table_column);

