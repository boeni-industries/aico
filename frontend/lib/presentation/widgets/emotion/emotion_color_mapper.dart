import 'package:flutter/material.dart';

/// Maps emotion labels to colors (dark mode optimized)
class EmotionColorMapper {
  /// Get color for emotion label
  static Color getColor(String emotionLabel) {
    return switch (emotionLabel.toLowerCase()) {
      'neutral' => const Color(0xFF9CA3AF),      // Gray
      'calm' => const Color(0xFF60A5FA),         // Soft blue
      'curious' => const Color(0xFF14B8A6),      // Teal
      'playful' => const Color(0xFF06B6D4),      // Bright cyan
      'warm_concern' => const Color(0xFFB8A1EA), // Purple (brand)
      'protective' => const Color(0xFF8B5CF6),   // Deep purple
      'focused' => const Color(0xFF3B82F6),      // Blue
      'encouraging' => const Color(0xFF10B981),  // Green
      'reassuring' => const Color(0xFF34D399),   // Soft green
      'apologetic' => const Color(0xFFA78BFA),   // Light purple
      'tired' => const Color(0xFF6B7280),        // Muted gray
      'reflective' => const Color(0xFF0891B2),   // Deep teal
      _ => const Color(0xFFB8A1EA),              // Default: brand purple
    };
  }

  /// Get color with custom opacity
  static Color getColorWithOpacity(String emotionLabel, double opacity) {
    return getColor(emotionLabel).withValues(alpha: opacity);
  }
}
