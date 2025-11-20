import 'package:flutter/material.dart';
import 'package:aico_frontend/data/models/emotion_model.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_color_mapper.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotion_formatter.dart';

/// Compact emotion badge showing current emotional state
class EmotionBadge extends StatelessWidget {
  final EmotionModel emotion;
  final bool showArousal;
  final bool showIntensityBar;

  const EmotionBadge({
    super.key,
    required this.emotion,
    this.showArousal = true,
    this.showIntensityBar = true,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final emotionColor = EmotionColorMapper.getColor(emotion.primary);

    return Container(
      width: double.infinity, // Use full available width
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        // Subtle gradient background, no border for better integration
        gradient: LinearGradient(
          colors: [
            emotionColor.withValues(alpha: 0.08),
            emotionColor.withValues(alpha: 0.04),
          ],
        ),
        borderRadius: BorderRadius.circular(6),
      ),
      child: IntrinsicHeight(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Emotion color indicator dot
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: emotionColor,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: emotionColor.withValues(alpha: 0.4),
                    blurRadius: 4,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            
            // Main content - wraps if needed
            Flexible(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Emotion label with intensity bar
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Emotion label - never truncate
                      Text(
                        EmotionFormatter.formatLabel(emotion.primary),
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                        ),
                      ),
                      if (showIntensityBar) ...[
                        const SizedBox(width: 6),
                        _buildIntensityBar(emotion.confidence, emotionColor),
                      ],
                    ],
                  ),
                  
                  // Arousal label on second line if both present
                  if (showArousal) ...[
                    const SizedBox(height: 2),
                    Text(
                      EmotionFormatter.getArousalLabel(emotion.arousal),
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.54),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIntensityBar(double intensity, Color color) {
    return Container(
      width: 40,
      height: 4,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(2),
      ),
      child: FractionallySizedBox(
        alignment: Alignment.centerLeft,
        widthFactor: intensity,
        child: Container(
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      ),
    );
  }
}
