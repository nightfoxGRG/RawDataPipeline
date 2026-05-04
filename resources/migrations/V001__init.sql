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
    id          bigserial primary key,
    schema      varchar(100) not null unique,
    description text         not null,
    user_id     bigint references users (id),
    created_at  timestamptz  not null default now(),
    created_by  bigint       not null references users (id),
    updated_at  timestamptz,
    updated_by  bigint references users (id),

    -- Запрещаем зарезервированные имена
    constraint project_schema_forbidden check (
        schema not in ('public', 'pg_catalog', 'information_schema', 'pg_toast', 'data_pipline_schema')
        )
);

create table user_setting
(
    user_id              bigint primary key not null references users (id),
    actual_project_id    bigint references project (id),
    actual_db_setting_id bigint references db_setting (id),
    created_at           timestamptz        not null default now(),
    created_by           bigint             not null references users (id),
    updated_at           timestamptz,
    updated_by           bigint references users (id)
);