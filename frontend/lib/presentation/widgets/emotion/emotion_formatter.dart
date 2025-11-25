/// Utilities for formatting emotion data
class EmotionFormatter {
  /// Format emotion label for display
  /// Example: "warm_concern" → "Warm Concern"
  static String formatLabel(String label) {
    return label
        .split('_')
        .map((word) => word.isEmpty ? '' : word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  /// Get human-readable description for emotion
  static String getDescription(String label) {
    return switch (label.toLowerCase()) {
      'neutral' => 'Calm and balanced',
      'calm' => 'Peaceful and centered',
      'curious' => 'Engaged and attentive',
      'playful' => 'Lighthearted and fun',
      'warm_concern' => 'Caring and supportive',
      'protective' => 'Watchful and caring',
      'focused' => 'Concentrated and present',
      'encouraging' => 'Supportive and uplifting',
      'reassuring' => 'Comforting and steady',
      'apologetic' => 'Understanding and gentle',
      'tired' => 'Low energy, still here',
      'reflective' => 'Thoughtful and contemplative',
      _ => 'Present with you',
    };
  }

  /// Get arousal level label
  /// 0.0-0.3 = calm, 0.3-0.6 = engaged, 0.6-1.0 = energized
  static String getArousalLabel(double arousal) {
    if (arousal < 0.3) return 'calm';
    if (arousal < 0.6) return 'engaged';
    return 'energized';
  }

  /// Format intensity as percentage
  static String formatIntensity(double intensity) {
    return '${(intensity * 100).round()}%';
  }

  /// Get emoji for emotion (optional, for future use)
  static String? getEmoji(String label) {
    return switch (label.toLowerCase()) {
      'playful' => '😊',
      'curious' => '🤔',
      'warm_concern' => '💜',
      'encouraging' => '✨',
      'calm' => '😌',
      _ => null,
    };
  }
}
