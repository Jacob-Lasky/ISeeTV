import sqlite3
import os
import logging

logger = logging.getLogger("ISeeTV-InitDB")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
logger.setFormatter(
    logging.Formatter("%(name)s | %(levelname)s: %(asctime)s - %(message)s")
)

try:
    # # for development purposes, delete the  entire database
    # logger.warning("Deleting database...")
    # os.remove("/app/data/sql_app.db")

    logger.info("Connecting to database...")
    conn = sqlite3.connect("/app/data/sql_app.db")
    cursor = conn.cursor()

    logger.info("Creating channels table...")
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS channels (
            guide_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            "group" TEXT,
            logo TEXT,
            is_favorite INTEGER DEFAULT 0,
            last_watched TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_missing INTEGER DEFAULT 0
        )"""
    )

    logger.info("Creating channel_streams table...")
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS channel_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            variant_name TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(guide_id),
            UNIQUE(channel_id, variant_name)
        )"""
    )

    # Add ON CONFLICT clause for UPSERT support
    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS update_channel_timestamp
        AFTER UPDATE ON channels
        BEGIN
            UPDATE channels SET created_at = CURRENT_TIMESTAMP
            WHERE guide_id = NEW.guide_id;
        END
        """
    )

    # Create trigger for channel_streams
    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS update_channel_stream_timestamp
        AFTER UPDATE ON channel_streams
        BEGIN
            UPDATE channel_streams SET created_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
        """
    )

    # Update indexes
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_channels_group 
           ON channels("group")"""
    )
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_channels_guide_id 
           ON channels(guide_id)"""
    )
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_channels_name 
           ON channels(name)"""
    )
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_channel_streams_channel_id 
           ON channel_streams(channel_id)"""
    )

    logger.info("Creating EPG tables...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS epg_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            icon TEXT,
            is_primary INTEGER DEFAULT 0,
            FOREIGN KEY (channel_id) REFERENCES channels(guide_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(guide_id)
        )
        """
    )

    # Add EPG indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_epg_channel_id ON epg_channels(channel_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_program_channel ON programs(channel_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_program_time ON programs(start_time, end_time)"
    )

    logger.info("Committing changes...")
    conn.commit()
    logger.info("Database initialization completed successfully")

except sqlite3.OperationalError as e:
    logger.error(f"Database error: {e}")
    raise
finally:
    if conn:
        try:
            conn.close()
            logger.info(
                "Database connection closed (all operations successfully completed)"
            )
        except sqlite3.Error as e:
            logger.error(f"Error closing database connection: {e}")
