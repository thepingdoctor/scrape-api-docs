-- PostgreSQL initialization script for Documentation Scraper
-- This script sets up the initial database schema and configuration

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS scraper;
SET search_path TO scraper, public;

-- Jobs table (for future API implementation)
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    options JSONB DEFAULT '{}',
    result_path TEXT,
    error_message TEXT,
    pages_scraped INTEGER DEFAULT 0,
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

-- Create indexes
CREATE INDEX idx_jobs_status ON jobs(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_url ON jobs USING gin(url gin_trgm_ops);

-- Pages table (cache scraped pages)
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    content TEXT,
    content_hash VARCHAR(64),
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, url)
);

CREATE INDEX idx_pages_job_id ON pages(job_id);
CREATE INDEX idx_pages_url ON pages USING gin(url gin_trgm_ops);
CREATE INDEX idx_pages_content_hash ON pages(content_hash);

-- Users table (for future multi-user support)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_role CHECK (role IN ('admin', 'user', 'readonly'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    last_used TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- Cache table for HTTP responses
CREATE TABLE IF NOT EXISTS http_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    response_body TEXT,
    response_headers JSONB,
    status_code INTEGER,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_http_cache_url ON http_cache USING hash(url);
CREATE INDEX idx_http_cache_expires_at ON http_cache(expires_at);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up old cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM http_cache WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate job statistics
CREATE OR REPLACE FUNCTION job_statistics(
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP - INTERVAL '30 days',
    end_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE (
    total_jobs BIGINT,
    completed_jobs BIGINT,
    failed_jobs BIGINT,
    avg_duration INTERVAL,
    total_pages BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_jobs,
        COUNT(*) FILTER (WHERE status = 'completed')::BIGINT AS completed_jobs,
        COUNT(*) FILTER (WHERE status = 'failed')::BIGINT AS failed_jobs,
        AVG(completed_at - started_at) FILTER (WHERE status = 'completed') AS avg_duration,
        SUM(pages_scraped)::BIGINT AS total_pages
    FROM jobs
    WHERE created_at BETWEEN start_date AND end_date
        AND deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Create default admin user (password: changeme123 - CHANGE THIS!)
INSERT INTO users (email, password_hash, full_name, role)
VALUES (
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0xnxN0xI8m', -- bcrypt hash of 'changeme123'
    'System Administrator',
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA scraper TO scraper;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA scraper TO scraper;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA scraper TO scraper;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA scraper TO scraper;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA scraper
    GRANT ALL ON TABLES TO scraper;
ALTER DEFAULT PRIVILEGES IN SCHEMA scraper
    GRANT ALL ON SEQUENCES TO scraper;
ALTER DEFAULT PRIVILEGES IN SCHEMA scraper
    GRANT EXECUTE ON FUNCTIONS TO scraper;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Print summary
DO $$
BEGIN
    RAISE NOTICE 'Database initialization complete!';
    RAISE NOTICE 'Schemas created: scraper';
    RAISE NOTICE 'Tables created: jobs, pages, users, api_keys, http_cache, audit_logs';
    RAISE NOTICE 'Default admin user: admin@example.com (password: changeme123)';
    RAISE NOTICE 'IMPORTANT: Change the default admin password immediately!';
END $$;
