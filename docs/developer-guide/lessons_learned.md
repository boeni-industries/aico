# Lessons Learned

## SQLite Concurrent Access with Encrypted Databases

**Problem**: Backend service and CLI commands accessing the same encrypted SQLite database caused "file is not a database" errors and backend crashes.

**Root Cause**: Concurrent access conflicts between multiple processes with persistent connections to encrypted database files.

**Failed Approaches**: Connection health checks, fresh connections per operation, and database proxy patterns all failed due to performance or architectural constraints.

**Solution**: Multi-layered approach combining WAL mode (`PRAGMA journal_mode=WAL`), busy timeout (`PRAGMA busy_timeout=10000`), comprehensive retry logic for lock/corruption errors, and exponential backoff with forced reconnection.

**Key Lessons**: Encrypted SQLite requires special handling beyond standard concurrency patterns. No single mitigation works - requires WAL mode + timeouts + retry logic + connection recovery. CLI independence is non-negotiable. Integration testing with concurrent processes is essential.

## Windows Unicode Encoding and Graceful Shutdown

**Problem**: Backend server crashed immediately on startup with `UnicodeEncodeError` when using emoji characters in console output on Windows.

**Root Cause**: Windows Command Prompt uses CP1252 encoding by default, which cannot handle Unicode emoji characters (`🚀`, `📡`, etc.).

**Failed Approaches**: Complex signal handler coordination, asyncio signal handlers, and Uvicorn signal override attempts all failed because the server never started successfully.

**Solution**: Remove emoji characters from console output and implement file-based shutdown mechanism (`gateway.shutdown` file in runtime directory) instead of signal-based approaches.

**Key Lessons**: Simple encoding issues can masquerade as complex architectural problems. File-based IPC is more reliable than signals for cross-platform graceful shutdown. Always test with actual Windows console environments, not just IDE terminals.

## Windows Background Processes and Console Windows

**Problem**: Background processes spawned via subprocess still showed CMD windows on Windows despite various creation flags and STARTUPINFO configurations.

**Root Cause**: Using `python.exe` always creates a console window on Windows, regardless of subprocess creation flags.

**Solution**: Use `pythonw.exe` (windowless Python interpreter) instead of `python.exe` for background processes.

**Key Lessons**: The executable itself determines console behavior on Windows. Subprocess flags cannot override the fundamental nature of console vs. windowless executables.

## FastAPI Decorator Signature Preservation

**Problem**: Admin API endpoints generated incorrect `args` and `kwargs` parameters in OpenAPI spec, causing "Field required" errors despite correct authentication.

**Root Cause**: Custom exception handling decorator not using `@functools.wraps(func)`, causing FastAPI to lose original function signatures.

**Solution**: Add `@functools.wraps(func)` to preserve function metadata in decorators.

**Key Lessons**: FastAPI relies on function signatures for OpenAPI generation. Always use `@functools.wraps` in decorators to preserve metadata.
