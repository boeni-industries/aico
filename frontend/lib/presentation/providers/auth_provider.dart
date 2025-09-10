import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/providers/domain_providers.dart';
import 'package:aico_frontend/domain/usecases/auth_usecases.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
class AuthNotifier extends StateNotifier<AuthState> {
  final LoginUseCase _loginUseCase;
  final AutoLoginUseCase _autoLoginUseCase;
  final LogoutUseCase _logoutUseCase;
  final CheckAuthStatusUseCase _checkAuthStatusUseCase;
  
  bool _isAutoLoginInProgress = false;

  AuthNotifier(
    this._loginUseCase,
    this._autoLoginUseCase,
    this._logoutUseCase,
    this._checkAuthStatusUseCase,
  ) : super(const AuthState());

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
      debugPrint('AuthProvider: Auto-login already in progress, skipping...');
      AICOLog.debug('Auto-login already in progress, skipping', topic: 'auth/autologin/skip');
      return;
    }
    
    _isAutoLoginInProgress = true;
    debugPrint('AuthProvider: Starting auto-login attempt...');
    AICOLog.info('Starting auto-login attempt', topic: 'auth/autologin/attempt');
    state = state.copyWith(isLoading: true);
    
    try {
      final result = await _autoLoginUseCase.execute();
      debugPrint('AuthProvider: Auto-login result: ${result != null ? "SUCCESS" : "FAILED - null result"}');
      
      if (result != null) {
        debugPrint('AuthProvider: Auto-login successful, user: ${result.user.id}');
        AICOLog.info('Auto-login successful', 
          topic: 'auth/autologin/success', 
          extra: {'user_id': result.user.id});
        state = state.copyWith(
          user: result.user,
          isAuthenticated: true,
          isLoading: false,
        );
      } else {
        debugPrint('AuthProvider: Auto-login failed - no result returned');
        AICOLog.warn('Auto-login failed - no result returned', topic: 'auth/autologin/failure');
        state = state.copyWith(isLoading: false);
      }
    } catch (e) {
      debugPrint('AuthProvider: Auto-login exception: $e');
      AICOLog.error('Auto-login exception', 
        topic: 'auth/autologin/error', 
        error: e, 
        extra: {'error_type': e.runtimeType.toString()});
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
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

  Future<void> checkAuthStatus() async {
    debugPrint('AuthProvider: Checking auth status...');
    AICOLog.debug('Checking auth status', topic: 'auth/status/check');
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
      debugPrint('AuthProvider: No stored credentials found');
      AICOLog.debug('No stored credentials found', topic: 'auth/status/no_credentials');
    } else if (state.isAuthenticated) {
      debugPrint('AuthProvider: Already authenticated');
      AICOLog.debug('Already authenticated', topic: 'auth/status/already_authenticated');
    }
  }

  void clearError() {
    state = state.copyWith(error: null);
  }
}

// Auth provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    ref.read(loginUseCaseProvider),
    ref.read(autoLoginUseCaseProvider),
    ref.read(logoutUseCaseProvider),
    ref.read(checkAuthStatusUseCaseProvider),
  );
});
