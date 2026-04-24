create table system.user
(
    id         bigserial    primary key,
    subject_id text         not null unique,
    name       text         not null,
    email      text,
    created_at timestamptz  not null default now(),
    updated_at timestamptz
);
