/// Date and time formatting utilities
/// 
/// Provides consistent time formatting across the application
class DateTimeUtils {
  DateTimeUtils._();

  /// Format a DateTime as a human-readable "time ago" string
  /// 
  /// Examples:
  /// - "just now" (< 60 seconds)
  /// - "5m ago" (minutes)
  /// - "2h ago" (hours)
  /// - "3d ago" (days)
  /// - "2w ago" (weeks)
  static String formatTimeAgo(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inSeconds < 60) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      final weeks = (difference.inDays / 7).floor();
      return '${weeks}w ago';
    }
  }

  /// Parse ISO 8601 timestamp string and format as "time ago"
  static String formatTimestampAgo(String timestamp) {
    final dateTime = DateTime.parse(timestamp);
    return formatTimeAgo(dateTime);
  }
}
