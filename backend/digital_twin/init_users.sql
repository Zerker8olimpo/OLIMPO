-- 1. Crear la tabla users si no existe
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Agregar la columna device_id si no existe
ALTER TABLE users ADD COLUMN IF NOT EXISTS device_id VARCHAR(255);