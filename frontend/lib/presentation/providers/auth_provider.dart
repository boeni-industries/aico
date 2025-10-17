import 'dart:async';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/providers/domain_providers.dart';
import 'package:aico_frontend/domain/usecases/auth_usecases.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'auth_provider.g.dart';

// Auth state
class AuthState {
  final User? user;
  final bool isAuthenticated;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.user,
    this.isAuthenticated = false,
    this.isLoading = false,
    this.error,
  });

  AuthState copyWith({
    User? user,
    bool? isAuthenticated,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      user: user ?? this.user,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// Auth notifier
@riverpod
class AuthNotifier extends _$AuthNotifier {
  late final LoginUseCase _loginUseCase;
  late final AutoLoginUseCase _autoLoginUseCase;
  late final LogoutUseCase _logoutUseCase;
  late final CheckAuthStatusUseCase _checkAuthStatusUseCase;
  late final TokenManager _tokenManager;
  
  bool _isAutoLoginInProgress = false;

  @override
  AuthState build() {
    // Initialize dependencies from ref
    _loginUseCase = ref.read(loginUseCaseProvider);
    _autoLoginUseCase = ref.read(autoLoginUseCaseProvider);
    _logoutUseCase = ref.read(logoutUseCaseProvider);
    _checkAuthStatusUseCase = ref.read(checkAuthStatusUseCaseProvider);
    _tokenManager = ref.read(tokenManagerProvider);
    
    _setupReAuthenticationListener();
    return const AuthState();
  }

  Future<void> login(String userUuid, String pin, {bool rememberMe = false}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final result = await _loginUseCase.execute(userUuid, pin, rememberMe: rememberMe);
      state = state.copyWith(
        user: result.user,
        isAuthenticated: true,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> attemptAutoLogin() async {
    if (_isAutoLoginInProgress) {
      return;
    }

    _isAutoLoginInProgress = true;
    
    try {
      // Check if we have stored credentials first (fast local check)
      final hasCredentials = await _checkAuthStatusUseCase.execute();
      
      if (!hasCredentials) {
        state = state.copyWith(
          isLoading: false,
          error: 'No stored credentials found. Please sign in.',
        );
        return;
      }

      // We have credentials - attempt auto-login
      state = state.copyWith(isLoading: true);
      
      final result = await _autoLoginUseCase.execute();
      
      if (result != null) {
        state = state.copyWith(
          user: result.user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        );
      } else {
        state = state.copyWith(
          isLoading: false,
          error: 'Unable to connect to AICO. Please check your connection.',
        );
      }
    } catch (e) {
      debugPrint('AuthProvider: Auto-login failed with error: $e');
      
      // Check if this is a backend unavailable error
      if (e.toString().contains('Authentication failed: Backend unavailable') ||
          e.toString().contains('connection refused') ||
          e.toString().contains('SocketException')) {
        // Don't clear credentials on backend unavailable - just set loading false
        state = state.copyWith(
          isLoading: false,
          error: 'Unable to connect to AICO. Please check your connection.',
        );
      } else if (e.toString().contains('401') || e.toString().contains('Unauthorized')) {
        // Clear credentials on authentication errors
        await _logoutUseCase.execute();
        state = state.copyWith(
          isLoading: false,
          error: 'Your session has expired. Please sign in again.',
        );
      } else {
        // Other errors - provide helpful message but keep credentials
        state = state.copyWith(
          isLoading: false,
          error: 'Sign-in issue occurred. Please try again.',
        );
      }
    } finally {
      _isAutoLoginInProgress = false;
    }
  }

  Future<void> logout() async {
    AICOLog.info('User logout initiated', topic: 'auth/logout/attempt');
    state = state.copyWith(isLoading: true);
    
    try {
      await _logoutUseCase.execute();
      AICOLog.info('User logout successful', topic: 'auth/logout/success');
      state = const AuthState();
    } catch (e) {
      AICOLog.error('User logout failed', 
        topic: 'auth/logout/error', 
        error: e, 
        extra: {'error_type': e.runtimeType.toString()});
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<bool> checkAuthStatus() async {
    debugPrint('AuthProvider: Checking auth status...');
    AICOLog.debug('Checking auth status', topic: 'auth/status/check');
    
    try {
      final hasCredentials = await _checkAuthStatusUseCase.execute();
      debugPrint('AuthProvider: Has stored credentials: $hasCredentials');
      debugPrint('AuthProvider: Current auth state: ${state.isAuthenticated}');
      AICOLog.debug('Auth status check result', 
        topic: 'auth/status/result', 
        extra: {
          'has_credentials': hasCredentials, 
          'is_authenticated': state.isAuthenticated
        });
      
      if (hasCredentials && !state.isAuthenticated) {
        debugPrint('AuthProvider: Attempting auto-login...');
        AICOLog.info('Credentials found, attempting auto-login', topic: 'auth/status/autologin_trigger');
        await attemptAutoLogin();
      } else if (!hasCredentials) {
        debugPrint('AuthProvider: No stored credentials found - clearing loading state');
        AICOLog.debug('No stored credentials found', topic: 'auth/status/no_credentials');
        // Ensure loading state is cleared when no credentials exist
        state = state.copyWith(isLoading: false);
      } else if (state.isAuthenticated) {
        debugPrint('AuthProvider: Already authenticated');
        AICOLog.debug('Already authenticated', topic: 'auth/status/already_authenticated');
        // Ensure loading state is cleared when already authenticated
        state = state.copyWith(isLoading: false);
      }
      
      return hasCredentials;
    } catch (e) {
      debugPrint('AuthProvider: Error during auth status check: $e');
      AICOLog.error('Auth status check failed', 
        topic: 'auth/status/error', 
        error: e);
      // Clear loading state on any error to prevent infinite loading
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }

  /// Listen for token expiration events and trigger re-authentication
  void _setupReAuthenticationListener() {
    _tokenManager.reAuthenticationStream.listen((event) {
      if (state.isAuthenticated && !_isAutoLoginInProgress) {
        AICOLog.info('Token expiration detected, attempting re-authentication',
          topic: 'auth/token/expiration_detected',
          extra: {'reason': event.reason});
        
        // Schedule re-authentication with delay to prevent blocking UI thread
        Future.delayed(const Duration(milliseconds: 100), () {
          if (state.isAuthenticated && !_isAutoLoginInProgress) {
            attemptAutoLogin();
          }
        });
      }
    });
  }

}
