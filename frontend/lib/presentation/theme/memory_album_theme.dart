/// Memory Album Theme
/// 
/// Premium gold-on-blue color palette inspired by treasured family photo albums.
/// Creates an intimate, precious aesthetic for user-curated memories.

import 'package:flutter/material.dart';

class MemoryAlbumTheme {
  // Background - Deep navy blue (leather-bound album cover)
  static const Color background = Color(0xFF1E2A3A);
  static const Color backgroundGradientStart = Color(0xFF1E2A3A);
  static const Color backgroundGradientEnd = Color(0xFF2A3A4A);
  
  // Primary accents - Silver/Platinum (metallic album details)
  static const Color silver = Color(0xFFC5C8CC);
  static const Color silverDark = Color(0xFFA8ABB0);
  static const Color silverLight = Color(0xFFE0E2E5);
  
  // Gold accents - Warm highlights (special moments, favorites)
  static const Color gold = Color(0xFFD4AF37);
  static const Color goldDark = Color(0xFFB8941F);
  static const Color goldLight = Color(0xFFE5C158);
  
  // Purple glow - AICO's signature (emotional presence)
  static const Color purpleGlow = Color(0xFFB8A1EA);
  static const Color purpleGlowDark = Color(0xFF9B84D4);
  
  // Text colors
  static const Color textPrimary = Color(0xFFCDD1DB); // Soft blue-gray (noticeably softer than white)
  static const Color textSecondary = Color(0xFF8B95A5);
  static const Color textTertiary = Color(0xFF5A6370);
  
  // Glass morphism
  static const Color glassLight = Color(0x0DFFFFFF); // 5% white
  static const Color glassBorder = Color(0x26FFFFFF); // 15% white
  
  // Emotional tone colors (subtle overlays)
  static const Color toneJoyful = Color(0xFF8DD686);
  static const Color toneReflective = Color(0xFFB8A1EA);
  static const Color toneVulnerable = Color(0xFF8DD6B8);
  static const Color toneExcited = Color(0xFFE5C158);
  
  /// Get gradient for background
  static LinearGradient get backgroundGradient => const LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [backgroundGradientStart, backgroundGradientEnd],
  );
  
  /// Get glassmorphic card decoration
  static BoxDecoration glassCard({
    bool isFavorite = false,
    Color? emotionalTone,
  }) {
    return BoxDecoration(
      color: glassLight,
      borderRadius: BorderRadius.circular(36), // XLarge radius
      border: Border.all(
        color: isFavorite ? gold.withOpacity(0.4) : glassBorder,
        width: 1.5,
      ),
      boxShadow: [
        // Floating depth
        BoxShadow(
          color: Colors.black.withOpacity(0.4),
          blurRadius: 40,
          offset: const Offset(0, 20),
          spreadRadius: -10,
        ),
      ],
    );
  }
  
  /// Get memory type icon color
  static Color getMemoryTypeColor(String memoryType) {
    switch (memoryType.toLowerCase()) {
      case 'milestone':
        return gold;
      case 'wisdom':
        return goldLight;
      case 'moment':
        return purpleGlow;
      default:
        return silver;
    }
  }
  
  /// Get emotional tone color
  static Color getEmotionalToneColor(String? tone) {
    if (tone == null) return silver;
    
    switch (tone.toLowerCase()) {
      case 'joyful':
      case 'happy':
      case 'excited':
        return toneExcited;
      case 'reflective':
      case 'thoughtful':
        return toneReflective;
      case 'vulnerable':
      case 'sad':
        return toneVulnerable;
      default:
        return silver;
    }
  }
  
  /// Shimmer effect for empty state
  static List<Color> get shimmerGradient => [
    silver.withOpacity(0.3),
    gold.withOpacity(0.5),
    silver.withOpacity(0.3),
  ];
}
