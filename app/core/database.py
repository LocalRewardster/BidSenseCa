"""Database connection and session management."""

import os
from typing import Generator
from supabase import create_client, Client
from loguru import logger

from app.config import settings


class DatabaseManager:
    """Database manager for Supabase connection."""
    
    def __init__(self):
        self.client: Client = None
        self._connect()
    
    def _connect(self):
        """Initialize Supabase client connection."""
        try:
            self.client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    def get_client(self) -> Client:
        """Get the Supabase client."""
        if not self.client:
            self._connect()
        return self.client


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Client:
    """Get database client dependency."""
    return db_manager.get_client()


def execute_query(query: str, params: dict = None) -> dict:
    """Execute a raw SQL query."""
    try:
        client = get_db()
        result = client.rpc('exec_sql', {'query': query, 'params': params or {}})
        return result
    except Exception as e:
        logger.error(f"Database query error: {e}")
        raise


def insert_tender(tender_data: dict) -> dict:
    """Insert a new tender into the database."""
    try:
        client = get_db()
        result = client.table('tenders').insert(tender_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to insert tender: {e}")
        raise


def get_tenders(
    limit: int = 50,
    offset: int = 0,
    source_name: str = None,
    keyword: str = None,
    status: str = None
) -> dict:
    """Get tenders with filtering and pagination."""
    try:
        client = get_db()
        query = client.table('tenders').select('*')
        
        # Apply filters
        if source_name:
            query = query.eq('source_name', source_name)
        
        if keyword:
            query = query.or_(f'title.ilike.%{keyword}%,description.ilike.%{keyword}%')
        
        if status:
            query = query.eq('status', status)
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data)
        
        # Apply pagination
        result = query.range(offset, offset + limit - 1).execute()
        
        return {
            "tenders": result.data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get tenders: {e}")
        raise


def get_tender_by_id(tender_id: str) -> dict:
    """Get a specific tender by ID."""
    try:
        client = get_db()
        result = client.table('tenders').select('*').eq('id', tender_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to get tender {tender_id}: {e}")
        raise


def update_tender(tender_id: str, update_data: dict) -> dict:
    """Update a tender."""
    try:
        client = get_db()
        result = client.table('tenders').update(update_data).eq('id', tender_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Failed to update tender {tender_id}: {e}")
        raise


def delete_tender(tender_id: str) -> bool:
    """Delete a tender."""
    try:
        client = get_db()
        result = client.table('tenders').delete().eq('id', tender_id).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Failed to delete tender {tender_id}: {e}")
        raise 