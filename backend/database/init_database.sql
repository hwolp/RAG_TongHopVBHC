-- Bootstrap database for the RAG backend.
-- Run this once before starting the backend if the MySQL database does not exist.
-- The backend will create/update application tables from SQLAlchemy models.

CREATE DATABASE IF NOT EXISTS rag_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE rag_db;
