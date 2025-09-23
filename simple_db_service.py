#!/usr/bin/env python3
"""
Simple PostgreSQL Database Service for AI News Scraper
Clean CRUD operations only - no migration code
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)

class SimplePostgreSQLService:
    def __init__(self):
        """Initialize PostgreSQL connection pool"""
        self.database_url = os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("POSTGRES_URL or DATABASE_URL environment variable is required")
        
        logger.info(f"🐘 Connecting to PostgreSQL database")
        
        # Create connection pool
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,  # min and max connections
                self.database_url,
                cursor_factory=RealDictCursor
            )
            logger.info("✅ PostgreSQL connection pool created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL connection pool: {str(e)}")
            raise e

    @contextmanager
    def get_db_connection(self):
        """Get database connection from pool"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def execute_query(self, query: str, params: tuple = None, fetch_results: bool = True, fetch_all: bool = True):
        """Execute a database query"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    
                    if not fetch_results:
                        conn.commit()
                        return cursor.rowcount
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ Database query failed: {str(e)}")
            logger.error(f"❌ Query: {query}")
            raise e

    def close_connections(self):
        """Close all database connections"""
        try:
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
                logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing connections: {str(e)}")

# Global database service instance
_db_service = None

def get_database_service() -> SimplePostgreSQLService:
    """Get database service singleton"""
    global _db_service
    if _db_service is None:
        _db_service = SimplePostgreSQLService()
    return _db_service

def close_database_service():
    """Close database service"""
    global _db_service
    if _db_service:
        _db_service.close_connections()
        _db_service = None