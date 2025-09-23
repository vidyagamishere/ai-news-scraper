# PostgreSQL Migration Guide for AI News Scraper

## Overview
This guide walks you through migrating your SQLite database to PostgreSQL on Railway.

## Prerequisites
- Railway CLI installed (`npm i -g @railway/cli`)
- PostgreSQL client tools installed locally
- Access to your Railway project

## Step 1: Create PostgreSQL Service on Railway

1. **Add PostgreSQL to your Railway project:**
   ```bash
   # In your Railway project dashboard
   # Click "+ New" → "Database" → "PostgreSQL"
   ```

2. **Wait for PostgreSQL to provision** (usually takes 1-2 minutes)

3. **Get connection details:**
   - Go to your PostgreSQL service in Railway dashboard
   - Navigate to "Variables" tab
   - Copy the `DATABASE_URL` (it should look like: `postgresql://postgres:password@host:port/railway`)

## Step 2: Verify Migration Script

The migration script has been generated at: `postgresql_migration.sql`

**Contents include:**
- ✅ Complete PostgreSQL schema with proper data types
- ✅ All normalized tables (articles, users, ai_topics, etc.)
- ✅ Foreign key relationships and constraints
- ✅ Optimized database views for content delivery
- ✅ Performance indexes
- ✅ Data migration from SQLite
- ✅ Sequence updates for auto-increment columns

## Step 3: Run Migration

### Option A: Using psql locally (Recommended)
```bash
# Connect to Railway PostgreSQL and run migration
psql "postgresql://postgres:password@host:port/railway" < postgresql_migration.sql
```

### Option B: Using Railway CLI
```bash
# Connect to your Railway project
railway link

# Copy migration file to Railway environment
railway run bash
# Then inside the container:
cat postgresql_migration.sql | psql $DATABASE_URL
```

## Step 4: Update Backend Configuration

1. **Add PostgreSQL support to requirements.txt:**
   ```bash
   echo "psycopg2-binary>=2.9.0" >> requirements.txt
   ```

2. **Update environment variables in Railway:**
   - Set `DATABASE_URL` to your PostgreSQL connection string
   - Set `DB_TYPE=postgresql` (new environment variable)

3. **Update the backend code** (see code changes below)

## Step 5: Code Changes for PostgreSQL Support

The backend needs to be updated to support both SQLite and PostgreSQL. Here are the key changes:

### Database Connection Module
```python
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    db_type = os.getenv('DB_TYPE', 'sqlite')
    
    if db_type == 'postgresql':
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable required for PostgreSQL")
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return conn
    else:
        # Default to SQLite
        db_path = os.getenv('DATABASE_PATH', '/app/ai_news.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
```

### SQL Query Compatibility
```python
def get_sql_syntax(db_type):
    if db_type == 'postgresql':
        return {
            'autoincrement': 'SERIAL PRIMARY KEY',
            'datetime': 'TIMESTAMP',
            'json_type': 'JSONB',
            'limit': 'LIMIT',
            'group_concat': 'STRING_AGG',
            'ilike': 'ILIKE'
        }
    else:
        return {
            'autoincrement': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'datetime': 'TIMESTAMP',
            'json_type': 'TEXT',
            'limit': 'LIMIT',
            'group_concat': 'GROUP_CONCAT',
            'ilike': 'LIKE'
        }
```

## Step 6: Test Migration

1. **Verify data integrity:**
   ```sql
   -- Check table row counts
   SELECT 
       'articles' as table_name, COUNT(*) as count FROM articles
   UNION ALL
   SELECT 'users', COUNT(*) FROM users
   UNION ALL  
   SELECT 'ai_topics', COUNT(*) FROM ai_topics
   UNION ALL
   SELECT 'article_topics', COUNT(*) FROM article_topics;
   ```

2. **Test application functionality:**
   ```bash
   # Test health endpoint
   curl https://your-railway-app.up.railway.app/api/health
   
   # Test digest endpoint
   curl https://your-railway-app.up.railway.app/api/digest
   ```

3. **Verify enhanced features:**
   - Topic-based personalization
   - Article-topic mappings
   - Optimized database views
   - User authentication

## Step 7: Environment Variables for Railway

Set these environment variables in your Railway project:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@host:port/railway
DB_TYPE=postgresql

# Application Configuration  
JWT_SECRET=your-jwt-secret
GOOGLE_CLIENT_ID=your-google-client-id
ALLOWED_ORIGINS=https://your-frontend-domain.com

# Optional: Backup SQLite path (for fallback)
SQLITE_BACKUP_PATH=/app/data/ai_news_backup.db
```

## Step 8: Performance Optimization

After migration, consider these optimizations:

1. **Connection Pooling:**
   ```python
   from psycopg2 import pool
   
   # Create connection pool
   connection_pool = psycopg2.pool.SimpleConnectionPool(
       1, 20,  # min and max connections
       database_url
   )
   ```

2. **Query Optimization:**
   - Use prepared statements for frequent queries
   - Leverage PostgreSQL's JSONB operators for user preferences
   - Use EXPLAIN ANALYZE for slow queries

3. **Monitoring:**
   - Set up Railway metrics monitoring
   - Monitor connection usage
   - Track query performance

## Rollback Plan

If issues occur, you can rollback to SQLite:

1. **Change environment variables:**
   ```bash
   DB_TYPE=sqlite
   # Remove or comment out DATABASE_URL
   ```

2. **Redeploy application** - it will use the existing SQLite database

## Migration Checklist

- [ ] PostgreSQL service created on Railway
- [ ] Migration script generated and reviewed
- [ ] Database migration executed successfully
- [ ] Backend code updated for PostgreSQL support
- [ ] Environment variables configured
- [ ] Application deployed and tested
- [ ] Data integrity verified
- [ ] Performance benchmarked
- [ ] Monitoring set up
- [ ] Rollback plan documented

## Troubleshooting

### Common Issues:

1. **Connection timeout:**
   - Check Railway PostgreSQL service status
   - Verify DATABASE_URL format
   - Ensure network connectivity

2. **Schema errors:**
   - Review migration script for syntax issues
   - Check PostgreSQL version compatibility
   - Verify column data types

3. **Data integrity issues:**
   - Compare row counts between SQLite and PostgreSQL
   - Verify foreign key relationships
   - Check JSON/JSONB field parsing

4. **Application errors:**
   - Review application logs in Railway
   - Test database connection independently
   - Verify environment variable configuration

## Support

If you encounter issues:
1. Check Railway dashboard for service status
2. Review application logs in Railway
3. Test database connection with psql command line
4. Verify migration script executed completely

---

**Migration Generated:** {current_date}
**Source Database:** SQLite (ai_news.db)
**Target Database:** PostgreSQL on Railway
**Script Size:** 247KB with complete schema and data