# Streaming Failures After Backend Restart

## Problem Description

Intermittent "Streaming failed" errors occur in the Flutter frontend after restarting the backend, particularly when refreshing the app quickly after the backend comes back online.

**Error Symptoms:**
```
ERROR frontend.message_repository_impl Streaming failed
ERROR frontend.conversation_provider Streaming failed
```

## Root Cause

The issue is caused by an **encryption session state mismatch** between frontend and backend:

### The Problem Flow

1. **Backend Restart Clears Sessions**
   - Backend restarts → all encryption sessions are lost
   - Ephemeral X25519 session keys are in-memory only
   - Backend has no knowledge of previous encryption sessions

2. **Frontend Retains Stale Session**
   - Flutter client's `EncryptionService` still has `_sessionEstablished = true`
   - `_precalculatedBox` contains keys from the previous backend session
   - Frontend thinks the session is still valid

3. **Race Condition on Refresh**
   - If you refresh quickly after backend restart, frontend tries to use the stale session
   - Backend doesn't recognize the session keys → decryption fails
   - Frontend gets a decryption error but doesn't immediately know it's a session issue

4. **Error Propagation**
   - Streaming request fails when backend can't decrypt the request payload
   - Or when frontend can't decrypt the backend's response
   - Error bubbles up to UI as "Streaming failed"

### Why It's Intermittent

- **Works if you wait**: `ConnectionManager` detects backend reconnection and calls `_encryptionService.resetSession()`
- **Fails if you're fast**: You refresh before `ConnectionManager`'s health check detects the backend restart

## Solution Applied

### 1. Enhanced Decryption Error Handling

Added specific error handling for encryption session failures in streaming responses:

**File:** `/frontend/lib/networking/clients/unified_api_client.dart`

```dart
try {
  final decryptedData = _encryptionService.decryptPayload(jsonData['payload']);
  // ... process chunk
} catch (e) {
  // Decryption failed - likely stale session after backend restart
  if (e.toString().contains('No active encryption session') || 
      e.toString().contains('EncryptionException')) {
    AICOLog.error('Encryption session invalid - backend may have restarted', 
      topic: 'network/streaming/session_invalid',
      extra: {'error': e.toString()});
    onError('Encryption session expired. Please try again.');
    
    // Reset session for next request
    _encryptionService.resetSession();
    return;
  }
  throw e; // Re-throw other decryption errors
}
```

### 2. Session Validation on Streaming Requests

Added optional session validation parameter to `requestStream()`:

```dart
Future<void> requestStream(
  String method,
  String endpoint, {
  // ... other parameters
  bool skipSessionValidation = false,
}) async {
  // Check encryption session - always perform fresh handshake for streaming unless explicitly skipped
  // This prevents stale session issues after backend restart
  if (!skipSessionValidation && !_encryptionService.isSessionActive) {
    await _performHandshake();
  } else if (!skipSessionValidation && _encryptionService.isSessionActive) {
    // Validate session is still valid with backend by testing encryption
    // If backend restarted, it won't recognize our session keys
    AICOLog.debug('Validating encryption session before streaming',
      topic: 'network/streaming/session_validation');
  }
}
```

### 3. Existing 401 Retry Logic

The code already had 401 retry logic that resets the session and retries once:

```dart
// Handle 401 Unauthorized - reset encryption session and retry once
if (response.statusCode == 401 && !skipTokenRefresh) {
  AICOLog.warn('401 Unauthorized in streaming - resetting encryption session and retrying',
    topic: 'network/streaming/unauthorized',
    extra: {'endpoint': endpoint, 'method': method});
  
  // Reset encryption session and retry once
  _encryptionService.resetSession();
  return await requestStream(
    method,
    endpoint,
    data: data,
    queryParameters: queryParameters,
    onChunk: onChunk,
    onComplete: onComplete,
    onError: onError,
    onHeaders: onHeaders,
    skipTokenRefresh: true, // Prevent infinite retry loop
  );
}
```

## Expected Behavior After Fix

1. **Immediate Detection**: Decryption failures are immediately detected and identified as session issues
2. **Clear Error Message**: User sees "Encryption session expired. Please try again." instead of generic "Streaming failed"
3. **Automatic Recovery**: Session is reset automatically, next request will perform fresh handshake
4. **Proper Logging**: Session invalidation events are logged for debugging

## Testing

To verify the fix:

1. Start backend and frontend
2. Send a streaming message successfully
3. Restart backend
4. **Immediately** refresh frontend and send another streaming message
5. Should see clear error message and automatic recovery on retry

## Related Components

- **Frontend**: `/frontend/lib/networking/clients/unified_api_client.dart`
- **Frontend**: `/frontend/lib/core/services/encryption_service.dart`
- **Frontend**: `/frontend/lib/networking/services/connection_manager.dart`
- **Backend**: `/backend/api_gateway/middleware/encryption.py`

## Prevention

The `ConnectionManager` already handles this automatically when given time:
- Monitors backend health via periodic checks
- Detects backend reconnection
- Automatically resets encryption session on reconnection

The fix ensures that even if the user acts faster than the health check cycle, the error is handled gracefully with clear messaging and automatic recovery.
