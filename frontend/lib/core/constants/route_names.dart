/// Route name constants for AICO's navigation system.
/// Implements hub-and-spoke pattern with progressive disclosure.
class RouteNames {
  // Primary navigation routes
  static const String home = '/';
  static const String conversation = '/conversation';
  static const String people = '/people';
  static const String more = '/more';

  // Conversation sub-routes
  static const String conversationHistory = '/conversation/history';
  static const String conversationDetail = 'conversation-detail';
  static String conversationDetailPath(String id) => '/conversation/$id';

  // People sub-routes
  static const String personDetail = 'person-detail';
  static String personDetailPath(String id) => '/people/$id';

  // More section sub-routes
  static const String memory = '/more/memory';
  static const String memorySearch = '/more/memory/search';
  static const String settings = '/more/settings';
  static const String privacySettings = '/more/settings/privacy';
  static const String admin = '/more/admin';
  static const String adminLogs = '/more/admin/logs';

  // Navigation helpers
  static bool isHomeRoute(String route) => route == home;
  static bool isConversationRoute(String route) => route.startsWith(conversation);
  static bool isPeopleRoute(String route) => route.startsWith(people);
  static bool isMoreRoute(String route) => route.startsWith(more);
  
  // Get primary section from any route
  static String getPrimarySection(String route) {
    if (route == home) return home;
    if (route.startsWith(conversation)) return conversation;
    if (route.startsWith(people)) return people;
    if (route.startsWith(more)) return more;
    return home; // Default fallback
  }
}
