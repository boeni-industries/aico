import asyncio
from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.security.key_manager import AICOKeyManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection


async def main():
    db_connection = None
    try:
        # Initialize config and key manager
        config_manager = ConfigurationManager()
        config_manager.initialize()
        key_manager = AICOKeyManager(config_manager)

        # Resolve database path (matches backend/main.py logic)
        db_path = AICOPaths.resolve_database_path("aico.db")

        # Get/derive encryption key
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        else:
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            else:
                print("ERROR: Master key not found. Run 'aico security setup' or authenticate first.")
                return

        # Open encrypted DB connection
        db_connection = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        await db_connection.connect()

        if not db_connection.is_connected():
            print("Failed to connect to the database.")
            return

        print("--- Echo logs (most recent 5) ---")
        echo_logs = await db_connection.fetchall(
            """
            SELECT timestamp, subsystem, module, level, message
            FROM logs
            WHERE subsystem = 'aico.api.echo' OR message LIKE '%ECHO TRACE%' OR message LIKE '%Echo %'
            ORDER BY id DESC
            LIMIT 5
            """
        )
        if not echo_logs:
            print("No recent echo logs found.")
        for row in echo_logs:
            print(f"[{row[0]}] {row[1]}.{row[2]} {row[3]}: {row[4]}")

        print("\n--- Health logs (most recent 5) ---")
        health_logs = await db_connection.fetchall(
            """
            SELECT timestamp, subsystem, module, level, message
            FROM logs
            WHERE message LIKE '%/api/v1/health%' OR message LIKE '%Health%' OR module LIKE '%rest%'
            ORDER BY id DESC
            LIMIT 5
            """
        )
        if not health_logs:
            print("No recent health logs found.")
        for row in health_logs:
            print(f"[{row[0]}] {row[1]}.{row[2]} {row[3]}: {row[4]}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if db_connection and db_connection.is_connected():
            await db_connection.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
