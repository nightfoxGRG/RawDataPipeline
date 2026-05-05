insert into data_pipline_schema.db_setting(db_label, host, port, name, db_user, password, user_id, created_by)
values ('LOCAL', 'localhost', 5432, 'data_pipeline_pro', 'user', 'password', 1, 1);

insert into data_pipline_schema.project (code, description, db_setting_id, schema, created_by)
values ('TEST001', 'Тестовый проект', 1, 'test_001', 1);

insert into data_pipline_schema.user_setting (user_id, actual_project_id, created_by)
values (1, 1, 1);
