/// AICO Central Topic Registry - Dart Mirror
/// 
/// Dart mirror of the Python topic registry for frontend consistency.
/// Maintains alignment with shared/aico/core/topics.py
class AICOTopics {
  // ===== AUTH DOMAIN =====
  static const String authLoginAttempt = 'auth/login/attempt/v1';
  static const String authLoginSuccess = 'auth/login/success/v1';
  static const String authLoginFailure = 'auth/login/failure/v1';
  static const String authLoginError = 'auth/login/error/v1';
  static const String authLogoutAttempt = 'auth/logout/attempt/v1';
  static const String authLogoutSuccess = 'auth/logout/success/v1';
  static const String authLogoutError = 'auth/logout/error/v1';
  static const String authAutoLoginAttempt = 'auth/auto_login/attempt/v1';
  static const String authAutoLoginSuccess = 'auth/auto_login/success/v1';
  static const String authAutoLoginFailure = 'auth/auto_login/failure/v1';
  static const String authAutoLoginConcurrent = 'auth/auto_login/concurrent/v1';
  static const String authLoginConcurrent = 'auth/login/concurrent/v1';
  static const String authAutoLoginNoCredentials = 'auth/auto_login/no_credentials/v1';
  
  // ===== APP DOMAIN =====
  static const String appStartup = 'app/startup/v1';
  static const String appInitialization = 'app/initialization/v1';
  static const String appThemeChange = 'app/theme/change/v1';
  
  // ===== UI DOMAIN =====
  static const String uiStateUpdate = 'ui/state/update/v1';
  static const String uiInteractionEvent = 'ui/interaction/event/v1';
  static const String uiNotificationShow = 'ui/notification/show/v1';
  static const String uiCommandExecute = 'ui/command/execute/v1';
  static const String uiPreferencesUpdate = 'ui/preferences/update/v1';
  static const String uiConnectionStatus = 'ui/connection/status/v1';
  
  // ===== USER DOMAIN =====
  static const String userInteractionHistory = 'user/interaction/history/v1';
  static const String userFeedbackExplicit = 'user/feedback/explicit/v1';
  static const String userFeedbackImplicit = 'user/feedback/implicit/v1';
  static const String userStateUpdate = 'user/state/update/v1';
  static const String userPresenceUpdate = 'user/presence/update/v1';
  
  // ===== CONVERSATION DOMAIN =====
  static const String conversationContextCurrent = 'conversation/context/current/v1';
  static const String conversationContextUpdate = 'conversation/context/update/v1';
  static const String conversationHistoryAdd = 'conversation/history/add/v1';
  static const String conversationIntentDetected = 'conversation/intent/detected/v1';
  static const String conversationUserInput = 'conversation/user/input/v1';
  static const String conversationAiResponse = 'conversation/ai/response/v1';
  
  // ===== WILDCARD PATTERNS =====
  static const String allAuth = 'auth/*';
  static const String allApp = 'app/*';
  static const String allUi = 'ui/*';
  static const String allUser = 'user/*';
  static const String allConversation = 'conversation/*';
  static const String allLogs = 'logs/*';
  static const String allSystem = 'system/*';
}
