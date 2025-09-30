-- Initialize database with basic setup
-- This script runs when PostgreSQL container starts

-- Create test database
CREATE DATABASE vehicle_inspection_test;

-- Create extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON DATABASE vehicle_inspection TO postgres;
GRANT ALL PRIVILEGES ON DATABASE vehicle_inspection_test TO postgres;
