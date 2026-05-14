
insert into data_pipline_schema.db_setting(db_label, host, port, name, created_by)
values ('LOCAL', 'localhost', 5432, 'data_pipeline_pro', 1);

insert into data_pipline_schema.db_setting_credential(user_id, db_setting_id, login, password, created_by)
values (1, 1, 'user', 'password', 1);

insert into data_pipline_schema.project (code, description, db_setting_id, schema, created_by)
values ('TEST001', 'Тестовый проект', 1, 'test_001', 1);

insert into data_pipline_schema.user_setting (user_id, actual_project_id, created_by)
values (1, 1, 1);


insert into data_pipline_schema.users (subject_id, first_name, last_name, email, is_tech_user)
values ('USER1', 'Роман', 'Горобченко', 'local@example.com', false);

insert into data_pipline_schema.db_setting_credential(user_id, db_setting_id, login, password, created_by)
values (3, 1, 'user', 'password', 1);

insert into data_pipline_schema.project (code, description, db_setting_id, schema, created_by)
values ('TEST002', 'Тестовый проект2', 1, 'test_002', 3);

insert into data_pipline_schema.user_setting (user_id, actual_project_id, created_by)
values (3, 2, 2);
