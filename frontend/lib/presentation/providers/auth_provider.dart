import 'package:aico_frontend/domain/entities/user.dart';
import 'package:aico_frontend/domain/providers/domain_providers.dart';
import 'package:aico_frontend/domain/usecases/auth_usecases.dart';
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
      return;
    }
    
    _isAutoLoginInProgress = true;
    debugPrint('AuthProvider: Starting auto-login attempt...');
    state = state.copyWith(isLoading: true);
    
    try {
      final result = await _autoLoginUseCase.execute();
      debugPrint('AuthProvider: Auto-login result: ${result != null ? "SUCCESS" : "FAILED - null result"}');
      
      if (result != null) {
        debugPrint('AuthProvider: Auto-login successful, user: ${result.user.id}');
        state = state.copyWith(
          user: result.user,
          isAuthenticated: true,
          isLoading: false,
        );
      } else {
        debugPrint('AuthProvider: Auto-login failed - no result returned');
        state = state.copyWith(isLoading: false);
      }
    } catch (e) {
      debugPrint('AuthProvider: Auto-login exception: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    } finally {
      _isAutoLoginInProgress = false;
    }
  }

  Future<void> logout() async {
    state = state.copyWith(isLoading: true);
    
    try {
      await _logoutUseCase.execute();
      state = const AuthState();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> checkAuthStatus() async {
    debugPrint('AuthProvider: Checking auth status...');
    final hasCredentials = await _checkAuthStatusUseCase.execute();
    debugPrint('AuthProvider: Has stored credentials: $hasCredentials');
    debugPrint('AuthProvider: Current auth state: ${state.isAuthenticated}');
    
    if (hasCredentials && !state.isAuthenticated) {
      debugPrint('AuthProvider: Attempting auto-login...');
      await attemptAutoLogin();
    } else if (!hasCredentials) {
      debugPrint('AuthProvider: No stored credentials found');
    } else if (state.isAuthenticated) {
      debugPrint('AuthProvider: Already authenticated');
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
