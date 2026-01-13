#!/usr/bin/env python3
"""
Check Neon Database - List tables and schema
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection"""
    db_url = (
        os.getenv("DATABASE_URL") or 
        os.getenv("NEON_DATABASE_URL") or 
        os.getenv("POSTGRES_URL")
    )
    
    if not db_url:
        print("❌ DATABASE_URL not found in .env")
        print("\n💡 Please add DATABASE_URL to your .env file:")
        print("   DATABASE_URL=postgresql://user:password@host/database")
        return None
    
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None


def list_tables(conn):
    """List all tables in the database"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        return [t['table_name'] for t in tables]
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []


def get_table_schema(conn, table_name):
    """Get schema for a specific table"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cursor.fetchall()
        return columns
    except Exception as e:
        print(f"❌ Error getting schema for {table_name}: {e}")
        return []


def main():
    print("=" * 80)
    print("🔍 CHECKING NEON DATABASE")
    print("=" * 80)
    print()
    
    # Connect to database
    print("📡 Connecting to database...")
    conn = get_db_connection()
    if not conn:
        sys.exit(1)
    
    print("✅ Connected successfully")
    print()
    
    # List tables
    print("📋 Listing tables...")
    tables = list_tables(conn)
    
    if not tables:
        print("⚠️  No tables found in database")
        conn.close()
        return
    
    print(f"✅ Found {len(tables)} table(s):")
    for table in tables:
        print(f"   - {table}")
    print()
    
    # Show schema for each table
    print("=" * 80)
    print("📊 TABLE SCHEMAS")
    print("=" * 80)
    print()
    
    for table in tables:
        print(f"📋 Table: {table}")
        print("-" * 80)
        
        columns = get_table_schema(conn, table)
        if columns:
            print(f"{'Column':<30} {'Type':<20} {'Nullable':<10} {'Default'}")
            print("-" * 80)
            for col in columns:
                col_name = col['column_name']
                col_type = col['data_type']
                if col['character_maximum_length']:
                    col_type += f"({col['character_maximum_length']})"
                nullable = col['is_nullable']
                default = col['column_default'] or ''
                
                print(f"{col_name:<30} {col_type:<20} {nullable:<10} {default}")
        else:
            print("   (no columns found)")
        print()
    
    conn.close()
    print("✅ Database check complete")


if __name__ == "__main__":
    main()

