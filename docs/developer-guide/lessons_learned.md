# Lessons Learned

## SQLite Concurrent Access with Encrypted Databases

**Problem**: Backend service and CLI commands accessing the same encrypted SQLite database caused "file is not a database" errors and backend crashes.

**Root Cause**: Concurrent access conflicts between multiple processes with persistent connections to encrypted database files.

**Failed Approaches**: Connection health checks, fresh connections per operation, and database proxy patterns all failed due to performance or architectural constraints.

**Solution**: Multi-layered approach combining WAL mode (`PRAGMA journal_mode=WAL`), busy timeout (`PRAGMA busy_timeout=10000`), comprehensive retry logic for lock/corruption errors, and exponential backoff with forced reconnection.

**Key Lessons**: Encrypted SQLite requires special handling beyond standard concurrency patterns. No single mitigation works - requires WAL mode + timeouts + retry logic + connection recovery. CLI independence is non-negotiable. Integration testing with concurrent processes is essential.
