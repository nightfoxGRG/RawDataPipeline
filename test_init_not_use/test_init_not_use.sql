insert into data_pipline_schema.project (schema, description, user_id, created_by)
values ('TEST_001', 'Тестовый проект', 1, 1);

insert into data_pipline_schema.db_setting(db_label, host, port, name, db_user, password, user_id, created_by)
values ('LOCAL', 'localhost', 5432, 'data_pipeline_pro', 'user', 'password', 1, 1);

insert into data_pipline_schema.user_setting (user_id, actual_project_id, actual_db_setting_id, created_by)
values (1, 1, 1, 1);
