# Refresh Token Implementation

## Problem

After backend or modelservice restart, users experienced "Streaming failed" errors with 403 Forbidden responses. The root cause was **missing refresh token functionality** in the authentication system.

### Symptoms
```
WARNING frontend.token_manager No refresh token available, triggering automatic re-authentication
WARNING frontend.unified_api_client No valid token available for request
ERROR frontend.message_repository_impl Streaming failed
ERROR frontend.conversation_provider Streaming failed
```

### Root Cause

The authentication system only used **access tokens** (short-lived, 15 minutes) without **refresh tokens** (long-lived, 7 days). When access tokens expired:

1. Frontend had no refresh token to get a new access token
2. Requests sent without Authorization header
3. Backend returned 403 Forbidden
4. Streaming requests failed

This was **not related to service restarts** - it was a fundamental auth system gap that manifested whenever access tokens naturally expired.

## Solution Implemented

Implemented complete refresh token flow following JWT best practices:

### Backend Changes

#### 1. Updated Authentication Response Schema
**File:** `/backend/api/users/schemas.py`

Added `refresh_token` field to `AuthenticationResponse`:
```python
class AuthenticationResponse(BaseModel):
    success: bool
    user: Optional[UserResponse]
    jwt_token: Optional[str]  # Access token (15 min)
    refresh_token: Optional[str]  # NEW: Refresh token (7 days)
    error: Optional[str]
    last_login: Optional[str]
```

#### 2. Added Refresh Token Generation
**File:** `/backend/api_gateway/models/core/auth.py`

Added `generate_refresh_token()` method:
```python
def generate_refresh_token(self, user_uuid: str, username: str = None, 
                           roles: List[str] = None, permissions: Set[str] = None,
                           device_uuid: str = None) -> str:
    """Generate JWT refresh token (long-lived, used only for token refresh)"""
    refresh_expiry_minutes = 7 * 24 * 60  # 7 days
    
    payload = {
        "sub": user_uuid,
        "user_uuid": user_uuid,
        "username": username or user_uuid,
        "roles": roles or ["user"],
        "permissions": list(permissions or set()),
        "iat": current_time,
        "exp": exp_time,
        "iss": "aico-api-gateway",
        "type": "refresh"  # Mark as refresh token
    }
    
    return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
```

#### 3. Updated Authentication Endpoint
**File:** `/backend/api/users/router.py`

Modified `/authenticate` endpoint to return both tokens:
```python
# Generate access token
jwt_token = auth_manager.generate_jwt_token(
    user_uuid=user.uuid,
    username=user.full_name,
    roles=user_roles,
    permissions=user_permissions,
    device_uuid="web-client"
)

# Generate refresh token
refresh_token = auth_manager.generate_refresh_token(
    user_uuid=user.uuid,
    username=user.full_name,
    roles=user_roles,
    permissions=user_permissions,
    device_uuid="web-client"
)

return AuthenticationResponse(
    success=True,
    user=_user_to_response(user),
    jwt_token=jwt_token,
    refresh_token=refresh_token,
    last_login=result.get("last_login")
)
```

#### 4. Added Refresh Endpoint
**File:** `/backend/api/users/router.py`

New `POST /users/refresh` endpoint:
```python
@router.post("/refresh", response_model=AuthenticationResponse)
async def refresh_token(request: Request, auth_manager = Depends(get_auth_manager)):
    """Refresh access token using refresh token"""
    # Extract refresh token from Authorization header
    auth_header = request.headers.get("authorization", "")
    refresh_token = auth_header[7:]  # Remove "Bearer " prefix
    
    # Decode and validate refresh token
    payload = jwt.decode(refresh_token, auth_manager.jwt_secret, ...)
    
    # Verify token type
    if payload.get("type") != "refresh":
        return AuthenticationResponse(success=False, error="Invalid token type")
    
    # Generate new access token
    new_access_token = auth_manager.generate_jwt_token(
        user_uuid=payload["user_uuid"],
        username=payload.get("username"),
        roles=payload.get("roles", ["user"]),
        permissions=set(payload.get("permissions", [])),
        device_uuid="web-client"
    )
    
    # Return new access token (keep same refresh token)
    return AuthenticationResponse(
        success=True,
        jwt_token=new_access_token,
        refresh_token=refresh_token
    )
```

### Frontend Changes

#### 1. Updated Domain Entity
**File:** `/frontend/lib/domain/repositories/auth_repository.dart`

Added `refreshToken` to `AuthResult`:
```dart
class AuthResult {
  final User user;
  final String token;
  final String? refreshToken;  // NEW
  final DateTime? lastLogin;
}
```

#### 2. Updated Data Model
**File:** `/frontend/lib/data/models/auth_model.dart`

Added refresh token parsing:
```dart
class AuthModel {
  final UserModel user;
  final String token;
  final String? refreshToken;  // NEW
  final DateTime? lastLogin;

  factory AuthModel.fromJson(Map<String, dynamic> json) {
    return AuthModel(
      user: UserModel.fromJson(json['user'] ?? {}),
      token: json['jwt_token']?.toString() ?? '',
      refreshToken: json['refresh_token']?.toString(),  // NEW
      lastLogin: ...
    );
  }
}
```

#### 3. Added Refresh Token Storage
**File:** `/frontend/lib/data/datasources/local/auth_local_datasource.dart`

Added methods to store/retrieve refresh tokens:
```dart
abstract class AuthLocalDataSource {
  Future<void> storeRefreshToken(String refreshToken);
  Future<String?> getRefreshToken();
  Future<void> clearRefreshToken();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  static const String _keyRefreshToken = 'refresh_token';
  
  @override
  Future<void> storeRefreshToken(String refreshToken) async {
    await _secureStorage.write(key: _keyRefreshToken, value: refreshToken);
    await _secureStorage.write(key: 'aico_refresh_token', value: refreshToken);
  }
  
  @override
  Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: _keyRefreshToken);
  }
}
```

#### 4. Updated Repository to Use Refresh Tokens
**File:** `/frontend/lib/data/repositories/auth_repository_impl.dart`

Store refresh token on authentication:
```dart
@override
Future<AuthResult> authenticate(String userUuid, String pin) async {
  final authModel = await _remoteDataSource.authenticate(userUuid, pin);
  
  // Store refresh token if provided
  if (authModel.refreshToken != null) {
    await _localDataSource.storeRefreshToken(authModel.refreshToken!);
  }
  
  return authModel.toDomain();
}
```

Implement proper token refresh:
```dart
@override
Future<bool> refreshToken() async {
  // Get refresh token (not access token)
  final refreshToken = await _localDataSource.getRefreshToken();
  if (refreshToken == null) return false;

  // Call backend refresh endpoint
  final authModel = await _remoteDataSource.refreshToken(refreshToken);
  if (authModel == null) return false;

  // Store new access token
  await _localDataSource.storeToken(authModel.token);
  
  // Store new refresh token if provided (token rotation)
  if (authModel.refreshToken != null) {
    await _localDataSource.storeRefreshToken(authModel.refreshToken!);
  }

  return true;
}
```

#### 5. Updated Remote Data Source
**File:** `/frontend/lib/data/datasources/remote/auth_remote_datasource.dart`

Changed refresh endpoint to return `AuthModel`:
```dart
@override
Future<AuthModel?> refreshToken(String refreshToken) async {
  final responseData = await _resilientApi.executeOperation<dynamic>(
    () => _resilientApi.apiClient.request(
      'POST',
      '/users/refresh',
      data: {'refresh_token': refreshToken},
    ),
    operationName: 'Token Refresh',
  );

  if (responseData != null && responseData['success'] == true) {
    return AuthModel.fromJson(responseData);
  }
  
  return null;
}
```

## Token Lifecycle

### Initial Authentication
1. User logs in with UUID + PIN
2. Backend generates:
   - Access token (15 min expiry, type="access")
   - Refresh token (7 days expiry, type="refresh")
3. Frontend stores both tokens in secure storage

### Token Refresh Flow
1. Access token expires (after 15 minutes)
2. `TokenManager` detects expiration
3. Calls `AuthRepository.refreshToken()`
4. Sends refresh token to `/users/refresh` endpoint
5. Backend validates refresh token
6. Backend generates new access token
7. Frontend stores new access token
8. Requests continue with new access token

### Token Rotation (Optional)
- Backend can return new refresh token in refresh response
- Frontend replaces old refresh token with new one
- Provides additional security by rotating refresh tokens

## Security Benefits

1. **Short-lived access tokens**: Minimizes exposure window if token is compromised
2. **Long-lived refresh tokens**: Better UX, users stay logged in for 7 days
3. **Token type validation**: Backend verifies `type="refresh"` to prevent access token reuse
4. **Secure storage**: Refresh tokens stored in platform secure storage (Keychain/Keystore)
5. **Token rotation**: Optional refresh token rotation for enhanced security

## Testing

To verify the fix works:

1. **Login**: Authenticate and verify both tokens are stored
2. **Wait 16 minutes**: Let access token expire
3. **Send message**: Should automatically refresh and work
4. **Check logs**: Should see token refresh instead of "No refresh token available"

## Migration Notes

- **Existing users**: Will get refresh tokens on next login
- **Backward compatible**: Backend still accepts requests without refresh tokens
- **No breaking changes**: All existing functionality preserved

## Related Files

### Backend
- `/backend/api/users/schemas.py` - Response schema
- `/backend/api/users/router.py` - Authentication endpoints
- `/backend/api_gateway/models/core/auth.py` - Token generation

### Frontend
- `/frontend/lib/domain/repositories/auth_repository.dart` - Domain entity
- `/frontend/lib/data/models/auth_model.dart` - Data model
- `/frontend/lib/data/datasources/local/auth_local_datasource.dart` - Storage
- `/frontend/lib/data/datasources/remote/auth_remote_datasource.dart` - API calls
- `/frontend/lib/data/repositories/auth_repository_impl.dart` - Business logic
