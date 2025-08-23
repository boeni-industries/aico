import 'package:flutter/foundation.dart';
import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/core/utils/platform_utils.dart';
import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';

// Events
abstract class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

class AuthLoginRequested extends AuthEvent {
  final String userUuid;
  final String pin;
  final bool rememberMe;

  const AuthLoginRequested({
    required this.userUuid,
    required this.pin,
    this.rememberMe = false,
  });

  @override
  List<Object?> get props => [userUuid, pin, rememberMe];
}

class AuthLogoutRequested extends AuthEvent {
  const AuthLogoutRequested();
}

class AuthTokenRefreshRequested extends AuthEvent {
  const AuthTokenRefreshRequested();
}

class AuthStatusChecked extends AuthEvent {
  const AuthStatusChecked();
}

class AuthAutoLoginRequested extends AuthEvent {
  const AuthAutoLoginRequested();
}

// States
abstract class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class AuthAuthenticated extends AuthState {
  final User user;
  final String token;
  final DateTime? lastLogin;

  const AuthAuthenticated({
    required this.user,
    required this.token,
    this.lastLogin,
  });

  @override
  List<Object?> get props => [user, token, lastLogin];
}

class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

class AuthFailure extends AuthState {
  final String message;
  final String? errorCode;

  const AuthFailure({
    required this.message,
    this.errorCode,
  });

  @override
  List<Object?> get props => [message, errorCode];
}

// BLoC
class AuthBloc extends HydratedBloc<AuthEvent, AuthState> {
  final UserRepository _userRepository;
  final TokenManager _tokenManager;

  AuthBloc({
    required UserRepository userRepository,
    required TokenManager tokenManager,
  })  : _userRepository = userRepository,
        _tokenManager = tokenManager,
        super(const AuthInitial()) {
    
    on<AuthLoginRequested>(_onLoginRequested);
    on<AuthLogoutRequested>(_onLogoutRequested);
    on<AuthTokenRefreshRequested>(_onTokenRefreshRequested);
    on<AuthStatusChecked>(_onStatusChecked);
    on<AuthAutoLoginRequested>(_onAutoLoginRequested);
  }

  Future<void> _onLoginRequested(
    AuthLoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      final request = AuthenticateRequest(
        uuid: event.userUuid,
        pin: event.pin,
      );

      final response = await _userRepository.authenticate(request);

      if (response.success && response.user != null && response.token != null) {
        // Set token expiry based on "remember me" preference
        final expiryTime = event.rememberMe 
            ? DateTime.now().add(const Duration(days: 30)) // 30 days for "remember me"
            : DateTime.now().add(const Duration(minutes: 15)); // 15 minutes for regular login
        
        debugPrint('🔐 AuthBloc: Token expiry set to: $expiryTime (Remember me: ${event.rememberMe})');
        
        // Store token with real expiry
        await _tokenManager.storeTokens(
          accessToken: response.token!,
          expiresAt: expiryTime,
        );

        // Store credentials if "Remember Me" is enabled
        debugPrint('🔐 AuthBloc: Remember me enabled: ${event.rememberMe}');
        if (event.rememberMe) {
          debugPrint('🔐 AuthBloc: Storing credentials for future auto-login');
          final userRepository = _userRepository as ApiUserRepository;
          await userRepository.storeCredentials(event.userUuid, event.pin, response.token!);
          debugPrint('🔐 AuthBloc: Credentials stored successfully');
        } else {
          debugPrint('🔐 AuthBloc: Remember me not enabled, skipping credential storage');
        }

        emit(AuthAuthenticated(
          user: response.user!,
          token: response.token!,
          lastLogin: response.lastLogin ?? DateTime.now(),
        ));
      } else {
        emit(AuthFailure(
          message: response.error ?? 'Authentication failed',
          errorCode: 'AUTH_FAILED',
        ));
      }
    } catch (e) {
      // Provide more specific error messages based on exception type
      String message;
      String errorCode;
      
      if (e.toString().contains('SocketException') || 
          e.toString().contains('TimeoutException') ||
          e.toString().contains('HandshakeException')) {
        message = PlatformUtils.getNetworkErrorMessage();
        errorCode = 'NETWORK_ERROR';
      } else if (e.toString().contains('FormatException') ||
                 e.toString().contains('HttpException')) {
        message = 'AICO server is temporarily unavailable. Please try again later.';
        errorCode = 'SERVER_ERROR';
      } else {
        message = PlatformUtils.getNetworkErrorMessage();
        errorCode = 'NETWORK_ERROR';
      }
      
      emit(AuthFailure(
        message: message,
        errorCode: errorCode,
      ));
    }
  }

  Future<void> _onLogoutRequested(
    AuthLogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      // Clear stored tokens and credentials
      await _tokenManager.clearTokens();
      final userRepository = _userRepository as ApiUserRepository;
      await userRepository.clearStoredCredentials();
      
      // TODO: Call logout API endpoint to revoke token on server
      // await _userRepository.logout();

      emit(const AuthUnauthenticated());
    } catch (e) {
      // Even if logout fails, clear local tokens and credentials
      await _tokenManager.clearTokens();
      final userRepository = _userRepository as ApiUserRepository;
      await userRepository.clearStoredCredentials();
      emit(const AuthUnauthenticated());
    }
  }

  Future<void> _onTokenRefreshRequested(
    AuthTokenRefreshRequested event,
    Emitter<AuthState> emit,
  ) async {
    try {
      final success = await _tokenManager.refreshToken();
      
      if (!success) {
        emit(const AuthFailure(
          message: 'Your session has expired. Please sign in again.',
          errorCode: 'TOKEN_EXPIRED',
        ));
      }
      // If successful, the current state remains unchanged
      // as the token is refreshed transparently
    } catch (e) {
      emit(const AuthFailure(
        message: 'Your session has expired. Please sign in again.',
        errorCode: 'TOKEN_EXPIRED',
      ));
    }
  }

  Future<void> _onStatusChecked(
    AuthStatusChecked event,
    Emitter<AuthState> emit,
  ) async {
    // Delegate to auto-login handler
    add(const AuthAutoLoginRequested());
  }

  Future<void> _onAutoLoginRequested(
    AuthAutoLoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    debugPrint('🔐 AuthBloc: Starting auto-login process');
    emit(const AuthLoading());

    try {
      // Attempt auto-login using stored credentials
      final userRepository = _userRepository as ApiUserRepository;
      final authResponse = await userRepository.attemptAutoLogin();
      
      if (authResponse != null && authResponse.user != null) {
        debugPrint('🔐 AuthBloc: Auto-login successful');
        emit(AuthAuthenticated(
          user: authResponse.user!,
          token: authResponse.token ?? '',
          lastLogin: DateTime.now(),
        ));
      } else {
        debugPrint('🔐 AuthBloc: No stored credentials found');
        emit(const AuthUnauthenticated());
      }
    } catch (e, stackTrace) {
      debugPrint('🔐 AuthBloc: Auto-login exception: $e');
      debugPrint('🔐 AuthBloc: Stack trace: $stackTrace');
      
      // Auto-login failed, clear stored credentials
      await _tokenManager.clearTokens();
      
      // Provide specific error message based on exception type
      String message;
      String errorCode;
      
      if (e is AuthException) {
        if (e.message == 'AUTH_FAILED') {
          message = 'Stored credentials are no longer valid. Please sign in again.';
          errorCode = 'AUTH_FAILED';
        } else if (e.message == 'PERMISSION_DENIED') {
          message = 'Access denied. Your account may not have the required permissions.';
          errorCode = 'PERMISSION_DENIED';
        } else {
          message = 'Authentication failed. Please sign in again.';
          errorCode = 'AUTH_FAILED';
        }
        debugPrint('🔐 AuthBloc: Authentication exception handled');
      } else if (e is ServerException) {
        message = 'AICO server is temporarily unavailable. Please try again later.';
        errorCode = 'SERVER_ERROR';
        debugPrint('🔐 AuthBloc: Server exception handled');
      } else if (e is ConnectionException) {
        if (e.message == 'NETWORK_ERROR') {
          message = PlatformUtils.getNetworkErrorMessage();
          errorCode = 'NETWORK_ERROR';
        } else {
          message = 'Connection error. Please check your internet connection.';
          errorCode = 'CONNECTION_ERROR';
        }
        debugPrint('🔐 AuthBloc: Connection exception handled');
      } else if (e.toString().contains('SocketException') || 
                 e.toString().contains('TimeoutException')) {
        message = PlatformUtils.getNetworkErrorMessage();
        errorCode = 'NETWORK_ERROR';
        debugPrint('🔐 AuthBloc: Network error detected');
      } else {
        message = 'Automatic sign-in failed. Please enter your credentials.';
        errorCode = 'AUTO_LOGIN_FAILED';
        debugPrint('🔐 AuthBloc: General auto-login failure');
      }
      
      emit(AuthFailure(
        message: message,
        errorCode: errorCode,
      ));
    }
  }

  @override
  AuthState? fromJson(Map<String, dynamic> json) {
    try {
      final type = json['type'] as String?;
      
      switch (type) {
        case 'authenticated':
          final userData = json['user'] as Map<String, dynamic>?;
          final token = json['token'] as String?;
          final lastLoginString = json['lastLogin'] as String?;
          
          if (userData != null && token != null) {
            return AuthAuthenticated(
              user: User.fromJson(userData),
              token: token,
              lastLogin: lastLoginString != null 
                  ? DateTime.parse(lastLoginString)
                  : null,
            );
          }
          break;
        case 'unauthenticated':
          return const AuthUnauthenticated();
        case 'failure':
          final message = json['message'] as String? ?? 'Unknown error';
          final errorCode = json['errorCode'] as String?;
          return AuthFailure(message: message, errorCode: errorCode);
      }
    } catch (e) {
      // Return null to use initial state
      return null;
    }
    return null;
  }

  @override
  Map<String, dynamic>? toJson(AuthState state) {
    switch (state.runtimeType) {
      case AuthAuthenticated:
        final authState = state as AuthAuthenticated;
        return {
          'type': 'authenticated',
          'user': authState.user.toJson(),
          'token': authState.token,
          'lastLogin': authState.lastLogin?.toIso8601String(),
        };
      case AuthUnauthenticated:
        return {'type': 'unauthenticated'};
      case AuthFailure:
        final failureState = state as AuthFailure;
        return {
          'type': 'failure',
          'message': failureState.message,
          'errorCode': failureState.errorCode,
        };
      default:
        // Don't persist loading or initial states
        return null;
    }
  }
}
