#!/usr/bin/env python3
"""
Database setup script for the Diagram Chat API
"""
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Get database configuration
        host = os.getenv('DB_HOST', '127.0.0.1')  # Use 127.0.0.1 for Docker compatibility
        user = os.getenv('DB_USER', 'root')
        password = os.getenv('DB_PASSWORD', 'your_password_here')
        
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database
            database_name = os.getenv('DB_NAME', 'diagram_chat')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
            print(f"Database '{database_name}' created successfully (or already exists)")
            
            # Create user and grant privileges (optional)
            db_user = os.getenv('DB_USER', 'root')
            if db_user != 'root':
                cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'127.0.0.1' IDENTIFIED BY '{os.getenv('DB_PASSWORD', 'password')}'")
                cursor.execute(f"GRANT ALL PRIVILEGES ON {database_name}.* TO '{db_user}'@'127.0.0.1'")
                cursor.execute("FLUSH PRIVILEGES")
                print(f"User '{db_user}' created and granted privileges")
            
    except Error as e:
        print(f"Error creating database: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
    
    return True

def create_tables():
    """Create database tables using SQLAlchemy"""
    try:
        from app.core.database import create_tables as create_db_tables
        create_db_tables()
        print("Database tables created successfully")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    print("Setting up database for Diagram Chat API...")
    
    # Step 1: Create database
    if create_database():
        print("✓ Database created")
    else:
        print("✗ Failed to create database")
        exit(1)
    
    # Step 2: Create tables
    if create_tables():
        print("✓ Tables created")
    else:
        print("✗ Failed to create tables")
        exit(1)
    
    print("Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Create a .env file with your configuration (see env_example.txt)")
    print("2. Start the server: uvicorn app.main:app --reload --port 8080")
    print("3. Test the API endpoints")
