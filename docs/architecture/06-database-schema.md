# Database Schema and Data Models
## PostgreSQL Schema for Job Management and Metadata

**Version:** 2.0.0
**Date:** 2025-10-26
**Status:** Design Phase

---

## Overview

The database schema supports job management, user authentication, export tracking, and system metrics. Designed for PostgreSQL with async support via asyncpg.

---

## Schema Overview

### Entity Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  users   │──────<│   jobs   │>──────│  exports │
└──────────┘       └──────────┘       └──────────┘
                         │
                         │
                   ┌─────▼──────┐
                   │ job_pages  │
                   └────────────┘
                         │
                   ┌─────▼──────┐
                   │ job_logs   │
                   └────────────┘

┌──────────────┐       ┌───────────────┐
│ credentials  │       │ api_keys      │
└──────────────┘       └───────────────┘

┌──────────────┐       ┌───────────────┐
│ system_stats │       │ audit_log     │
└──────────────┘       └───────────────┘
```

---

## Core Tables

### 1. users

Stores user accounts and authentication.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    -- Roles: admin, user, readonly

    -- Account status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMP,

    -- Limits
    max_jobs_per_day INTEGER DEFAULT 10,
    max_concurrent_jobs INTEGER DEFAULT 3,
    max_pages_per_job INTEGER DEFAULT 1000,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(role) WHERE deleted_at IS NULL;
```

### 2. jobs

Primary table for scraping jobs.

```sql
CREATE TYPE job_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE job_priority AS ENUM (
    'low',
    'normal',
    'high',
    'urgent'
);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Job configuration
    url TEXT NOT NULL,
    options JSONB NOT NULL DEFAULT '{}',
    export_formats TEXT[] NOT NULL DEFAULT ARRAY['markdown'],
    priority job_priority NOT NULL DEFAULT 'normal',

    -- Status tracking
    status job_status NOT NULL DEFAULT 'queued',
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    progress_percent DECIMAL(5,2) DEFAULT 0.0,
    current_operation TEXT,

    -- Timing
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    queued_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_completion_at TIMESTAMP,
    duration_seconds DECIMAL(10,2),

    -- Statistics
    pages_discovered INTEGER DEFAULT 0,
    pages_processed INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    -- Results
    output_dir TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',

    -- Webhook
    webhook_url TEXT,
    webhook_sent_at TIMESTAMP,

    -- Soft delete
    deleted_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_jobs_user_status ON jobs(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_jobs_status_created ON jobs(status, created_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_priority_status ON jobs(priority, status) WHERE status IN ('queued', 'running');

-- Partial index for active jobs
CREATE INDEX idx_active_jobs ON jobs(status) WHERE status IN ('queued', 'running') AND deleted_at IS NULL;

-- GIN index for JSONB queries
CREATE INDEX idx_jobs_options ON jobs USING GIN (options);
CREATE INDEX idx_jobs_metadata ON jobs USING GIN (metadata);
```

### 3. job_pages

Tracks individual pages within a job.

```sql
CREATE TABLE job_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    -- Page information
    url TEXT NOT NULL,
    title TEXT,
    order_index INTEGER NOT NULL,

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Statuses: pending, processing, completed, failed

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10,2),

    -- Content metadata
    content_hash VARCHAR(64),
    content_size_bytes INTEGER,
    word_count INTEGER,
    heading_count INTEGER,
    link_count INTEGER,
    image_count INTEGER,

    -- Rendering info
    rendered_with_javascript BOOLEAN DEFAULT false,
    render_time_seconds DECIMAL(10,2),
    from_cache BOOLEAN DEFAULT false,

    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_pages_job_id ON job_pages(job_id);
CREATE INDEX idx_job_pages_status ON job_pages(job_id, status);
CREATE INDEX idx_job_pages_url_hash ON job_pages(content_hash);
```

### 4. exports

Tracks export files for jobs.

```sql
CREATE TYPE export_status AS ENUM (
    'pending',
    'generating',
    'completed',
    'failed'
);

CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    -- Export configuration
    format VARCHAR(50) NOT NULL,
    -- Formats: markdown, pdf, epub, json, html

    status export_status NOT NULL DEFAULT 'pending',

    -- File information
    file_path TEXT,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64),

    -- Processing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10,2),

    -- Storage
    storage_backend VARCHAR(50) DEFAULT 'local',
    -- Backends: local, s3, gcs, azure
    storage_url TEXT,

    -- Metadata
    options JSONB DEFAULT '{}',
    error_message TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_exports_job_id ON exports(job_id);
CREATE INDEX idx_exports_format ON exports(format);
CREATE INDEX idx_exports_status ON exports(status);
CREATE INDEX idx_exports_expires_at ON exports(expires_at) WHERE expires_at IS NOT NULL;
```

### 5. job_logs

Detailed logging for job execution.

```sql
CREATE TYPE log_level AS ENUM (
    'debug',
    'info',
    'warning',
    'error',
    'critical'
);

CREATE TABLE job_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    level log_level NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_logs_job_id ON job_logs(job_id, created_at DESC);
CREATE INDEX idx_job_logs_level ON job_logs(job_id, level) WHERE level IN ('error', 'critical');

-- Partition by month for large datasets
CREATE TABLE job_logs_y2025m10 PARTITION OF job_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

---

## Authentication & Security Tables

### 6. api_keys

API key management for programmatic access.

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Key information
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    -- Store prefix for identification (e.g., "sk_prod_abc")

    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Permissions
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read'],
    -- Scopes: read, write, admin

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 1000,

    -- Usage tracking
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash) WHERE is_active = true AND revoked_at IS NULL;
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;
```

### 7. credentials

Stored authentication credentials for target sites.

```sql
CREATE TYPE auth_type AS ENUM (
    'none',
    'basic',
    'bearer',
    'api_key',
    'cookie',
    'oauth2',
    'custom_header'
);

CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Target information
    domain VARCHAR(255) NOT NULL,
    auth_type auth_type NOT NULL,

    -- Encrypted credentials
    credentials_encrypted BYTEA NOT NULL,
    -- Store as encrypted JSON

    -- Metadata
    name VARCHAR(255),
    description TEXT,

    -- Expiration
    expires_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,

    UNIQUE(user_id, domain)
);

CREATE INDEX idx_credentials_user_domain ON credentials(user_id, domain);
CREATE INDEX idx_credentials_expires_at ON credentials(expires_at) WHERE expires_at IS NOT NULL;
```

---

## System Tables

### 8. system_stats

Aggregated system statistics and metrics.

```sql
CREATE TABLE system_stats (
    id BIGSERIAL PRIMARY KEY,

    -- Time bucket
    timestamp TIMESTAMP NOT NULL,
    granularity VARCHAR(20) NOT NULL,
    -- Granularities: minute, hour, day

    -- Job metrics
    jobs_created INTEGER DEFAULT 0,
    jobs_completed INTEGER DEFAULT 0,
    jobs_failed INTEGER DEFAULT 0,
    total_pages_scraped INTEGER DEFAULT 0,

    -- Performance metrics
    avg_job_duration_seconds DECIMAL(10,2),
    avg_page_processing_seconds DECIMAL(10,2),
    cache_hit_rate DECIMAL(5,4),

    -- Resource metrics
    active_workers INTEGER DEFAULT 0,
    queue_depth INTEGER DEFAULT 0,
    storage_used_bytes BIGINT DEFAULT 0,

    -- User metrics
    active_users INTEGER DEFAULT 0,
    api_requests INTEGER DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(timestamp, granularity)
);

CREATE INDEX idx_system_stats_timestamp ON system_stats(timestamp DESC, granularity);

-- Partition by month
CREATE TABLE system_stats_y2025m10 PARTITION OF system_stats
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

### 9. audit_log

Comprehensive audit trail for security and compliance.

```sql
CREATE TYPE audit_action AS ENUM (
    'user_login',
    'user_logout',
    'user_created',
    'user_updated',
    'user_deleted',
    'job_created',
    'job_cancelled',
    'job_deleted',
    'api_key_created',
    'api_key_revoked',
    'credential_created',
    'credential_deleted',
    'export_downloaded',
    'settings_updated'
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,

    -- Actor information
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,

    -- Action details
    action audit_action NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,

    -- Context
    details JSONB DEFAULT '{}',
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, created_at DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- Partition by month
CREATE TABLE audit_log_y2025m10 PARTITION OF audit_log
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

---

## Database Functions and Triggers

### Auto-update timestamps

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_credentials_updated_at
    BEFORE UPDATE ON credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Calculate job duration

```sql
CREATE OR REPLACE FUNCTION calculate_job_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_job_duration_trigger
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION calculate_job_duration();
```

### Update job progress

```sql
CREATE OR REPLACE FUNCTION update_job_progress()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.progress_total > 0 THEN
        NEW.progress_percent = (NEW.progress_current::DECIMAL / NEW.progress_total::DECIMAL) * 100;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_job_progress_trigger
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    WHEN (NEW.progress_current IS NOT NULL AND NEW.progress_total IS NOT NULL)
    EXECUTE FUNCTION update_job_progress();
```

### Enforce job limits

```sql
CREATE OR REPLACE FUNCTION check_user_job_limits()
RETURNS TRIGGER AS $$
DECLARE
    user_max_concurrent INTEGER;
    user_current_jobs INTEGER;
BEGIN
    -- Get user's concurrent job limit
    SELECT max_concurrent_jobs INTO user_max_concurrent
    FROM users WHERE id = NEW.user_id;

    -- Count user's active jobs
    SELECT COUNT(*) INTO user_current_jobs
    FROM jobs
    WHERE user_id = NEW.user_id
      AND status IN ('queued', 'running')
      AND deleted_at IS NULL;

    IF user_current_jobs >= user_max_concurrent THEN
        RAISE EXCEPTION 'User has reached maximum concurrent jobs limit (%)' , user_max_concurrent;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_user_job_limits_trigger
    BEFORE INSERT ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION check_user_job_limits();
```

---

## Views

### Active jobs summary

```sql
CREATE VIEW active_jobs_summary AS
SELECT
    j.id,
    j.user_id,
    u.username,
    j.url,
    j.status,
    j.priority,
    j.progress_percent,
    j.current_operation,
    j.created_at,
    j.started_at,
    j.estimated_completion_at,
    EXTRACT(EPOCH FROM (NOW() - j.started_at)) as elapsed_seconds
FROM jobs j
JOIN users u ON j.user_id = u.id
WHERE j.status IN ('queued', 'running')
  AND j.deleted_at IS NULL;
```

### User statistics

```sql
CREATE VIEW user_statistics AS
SELECT
    u.id as user_id,
    u.username,
    u.email,
    COUNT(j.id) as total_jobs,
    COUNT(CASE WHEN j.status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN j.status = 'failed' THEN 1 END) as failed_jobs,
    SUM(j.pages_processed) as total_pages_scraped,
    AVG(j.duration_seconds) as avg_job_duration,
    MAX(j.created_at) as last_job_at
FROM users u
LEFT JOIN jobs j ON u.id = j.user_id AND j.deleted_at IS NULL
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.username, u.email;
```

---

## SQLAlchemy Models

### Python Models

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ARRAY, JSON, ForeignKey, Numeric
import enum
from datetime import datetime
from uuid import uuid4

Base = declarative_base()

class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), nullable=False, default="user")

    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    email_verified_at = Column(DateTime)

    max_jobs_per_day = Column(Integer, default=10)
    max_concurrent_jobs = Column(Integer, default=3)
    max_pages_per_job = Column(Integer, default=1000)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime)

    # Relationships
    jobs = relationship("Job", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    credentials = relationship("Credential", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    url = Column(String, nullable=False)
    options = Column(JSON, nullable=False, default={})
    export_formats = Column(ARRAY(String), nullable=False, default=["markdown"])
    priority = Column(Enum(JobPriority), nullable=False, default=JobPriority.NORMAL)

    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED, index=True)
    progress_current = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    progress_percent = Column(Numeric(5, 2), default=0.0)
    current_operation = Column(String)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion_at = Column(DateTime)
    duration_seconds = Column(Numeric(10, 2))

    pages_discovered = Column(Integer, default=0)
    pages_processed = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    error_count = Column(Integer, default=0)

    output_dir = Column(String)
    error_message = Column(String)
    metadata = Column(JSON, default={})

    webhook_url = Column(String)
    webhook_sent_at = Column(DateTime)

    deleted_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="jobs")
    pages = relationship("JobPage", back_populates="job", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
```

---

## Migration Scripts

### Alembic Migration (Initial)

```python
"""Initial schema

Revision ID: 001
Create Date: 2025-10-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create ENUM types
    op.execute("CREATE TYPE job_status AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE job_priority AS ENUM ('low', 'normal', 'high', 'urgent')")

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        # ... rest of columns
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])

    # Create jobs table
    # ... similar pattern

def downgrade():
    op.drop_table('jobs')
    op.drop_table('users')
    op.execute("DROP TYPE job_priority")
    op.execute("DROP TYPE job_status")
```

---

## Performance Optimization

### Partitioning Strategy
- Partition `job_logs` and `audit_log` by month
- Partition `system_stats` by time period
- Automatic partition creation via pg_partman

### Indexing Strategy
- Composite indexes for common query patterns
- Partial indexes for filtered queries
- GIN indexes for JSONB columns
- Covering indexes for read-heavy queries

### Query Optimization
```sql
-- Example: Efficient job queue query
SELECT id, user_id, url, priority, created_at
FROM jobs
WHERE status = 'queued'
  AND deleted_at IS NULL
ORDER BY priority DESC, created_at ASC
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

---

## Next Steps

1. Create database schema with migrations
2. Implement SQLAlchemy models
3. Set up Alembic for schema versioning
4. Create database initialization scripts
5. Implement connection pooling
6. Add database backup procedures
7. Set up monitoring and slow query logging
8. Write database tests
9. Document query patterns and performance
10. Plan data retention and archival strategy
