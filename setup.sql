-- setup.sql

CREATE DATABASE IF NOT EXISTS object_detection_db;

CREATE USER IF NOT EXISTS 'myuser'@'localhost' IDENTIFIED BY 'mypassword';

GRANT ALL PRIVILEGES ON `object_detection_db`.* TO `myuser`@`localhost`;
FLUSH PRIVILEGES;

USE object_detection_db;