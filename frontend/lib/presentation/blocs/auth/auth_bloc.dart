import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';

import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/networking/services/jwt_decoder.dart';

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
class AuthBloc extends Bloc<AuthEvent, AuthState> {
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
        // Decode JWT expiry time
        final expiryTime = JWTDecoder.getExpiryTime(response.token!) ?? 
            DateTime.now().add(const Duration(minutes: 15));
        
        // Store token with real expiry
        await _tokenManager.storeTokens(
          accessToken: response.token!,
          expiresAt: expiryTime,
        );

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
      emit(AuthFailure(
        message: 'Connection error. Please check your network and try again.',
        errorCode: 'NETWORK_ERROR',
      ));
    }
  }

  Future<void> _onLogoutRequested(
    AuthLogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      // Clear stored tokens
      await _tokenManager.clearTokens();
      
      // TODO: Call logout API endpoint to revoke token on server
      // await _userRepository.logout();

      emit(const AuthUnauthenticated());
    } catch (e) {
      // Even if logout fails, clear local tokens
      await _tokenManager.clearTokens();
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
        emit(const AuthUnauthenticated());
      }
      // If successful, the current state remains unchanged
      // as the token is refreshed transparently
    } catch (e) {
      emit(const AuthUnauthenticated());
    }
  }

  Future<void> _onStatusChecked(
    AuthStatusChecked event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      final token = await _tokenManager.getValidToken();
      
      if (token != null) {
        // TODO: Validate token with backend and get user info
        // For now, we'll assume the token is valid
        // In a real implementation, you'd call an API to verify the token
        // and get the current user information
        
        // Placeholder - implement proper token validation
        emit(const AuthUnauthenticated());
      } else {
        emit(const AuthUnauthenticated());
      }
    } catch (e) {
      emit(const AuthUnauthenticated());
    }
  }
}
