import 'package:flutter/material.dart';
import 'package:aico_frontend/data/models/interaction_model.dart';
import 'package:aico_frontend/presentation/widgets/common/glassmorphic_card.dart';
import 'package:aico_frontend/presentation/widgets/common/interaction_type_icon.dart';
import 'package:aico_frontend/core/utils/date_time_utils.dart';

/// Interaction card for drawer display
/// 
/// Shows interaction summary with action buttons
/// Follows glassmorphic design with urgency-based styling
class InteractionCard extends StatelessWidget {
  final InteractionRequest interaction;
  final VoidCallback? onTap;
  final VoidCallback? onAnswer;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;
  final VoidCallback? onDismiss;
  final VoidCallback? onDefer;

  const InteractionCard({
    super.key,
    required this.interaction,
    this.onTap,
    this.onAnswer,
    this.onApprove,
    this.onReject,
    this.onDismiss,
    this.onDefer,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isRequired = interaction.requirement == 'required';
    final isHighSeverity = interaction.severity == 'high';
    final timeAgo = DateTimeUtils.formatTimestampAgo(interaction.createdAt);

    return GlassmorphicCard(
      onTap: onTap,
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header: Status and metadata
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Left side: Status badges
              Expanded(
                child: Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    // Test/Simulated badge (if applicable)
                    if (interaction.idempotencyKey.startsWith('sim_'))
                      _buildTestBadge(theme),
                    // Source category badge
                    _buildSourceBadge(theme),
                    // Urgency indicator + Requirement badge
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (isRequired && isHighSeverity)
                          Container(
                            width: 6,
                            height: 6,
                            margin: const EdgeInsets.only(right: 6),
                            decoration: BoxDecoration(
                              color: Colors.red,
                              shape: BoxShape.circle,
                            ),
                          )
                        else if (isRequired)
                          Container(
                            width: 6,
                            height: 6,
                            margin: const EdgeInsets.only(right: 6),
                            decoration: BoxDecoration(
                              color: Colors.orange,
                              shape: BoxShape.circle,
                            ),
                          ),
                        Text(
                          isRequired ? 'Required' : 'Optional',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: isRequired 
                                ? Colors.red.withValues(alpha: 0.9)
                                : theme.colorScheme.onSurface.withValues(alpha: 0.6),
                            fontWeight: FontWeight.w600,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                    // Severity
                    Text(
                      _capitalizeFirst(interaction.severity),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                        fontSize: 11,
                      ),
                    ),
                    // Time ago
                    Text(
                      timeAgo,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              // Right side: Type icon
              InteractionTypeIcon(
                interactionType: interaction.interactionType,
                size: 18,
                alpha: 0.8,
              ),
            ],
          ),
          
          const SizedBox(height: 10),
          
          // Title (if present)
          if (interaction.title != null) ...[
            Text(
              interaction.title!,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
          ],
          
          // Prompt
          Text(
            interaction.prompt,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.8),
              fontSize: 13,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          
          const SizedBox(height: 12),
          
          // Action buttons
          _buildActionButtons(theme),
        ],
      ),
    );
  }

  Widget _buildActionButtons(ThemeData theme) {
    final buttons = <Widget>[];
    
    // Type-specific primary actions
    switch (interaction.interactionType) {
      case 'question':
        if (onAnswer != null) {
          buttons.add(_buildButton(
            'Answer',
            Icons.edit_outlined,
            onAnswer!,
            theme,
            isPrimary: true,
          ));
        }
        break;
      
      case 'choice':
        if (onAnswer != null) {
          buttons.add(_buildButton(
            'Choose',
            Icons.check,
            onAnswer!,
            theme,
            isPrimary: true,
          ));
        }
        break;
      
      case 'approval':
        if (onApprove != null) {
          buttons.add(_buildButton(
            'Approve',
            Icons.check_circle,
            onApprove!,
            theme,
            isPrimary: true,
            color: Colors.green,
          ));
        }
        if (onReject != null) {
          buttons.add(_buildButton(
            'Reject',
            Icons.cancel,
            onReject!,
            theme,
            color: Colors.red,
          ));
        }
        break;
      
      case 'dialogue':
        if (onAnswer != null) {
          buttons.add(_buildButton(
            'Start',
            Icons.chat,
            onAnswer!,
            theme,
            isPrimary: true,
          ));
        }
        break;
      
      case 'ack':
        if (onAnswer != null) {
          buttons.add(_buildButton(
            'Acknowledge',
            Icons.done,
            onAnswer!,
            theme,
            isPrimary: true,
          ));
        }
        break;
    }
    
    // Secondary actions
    if (onDefer != null) {
      buttons.add(_buildButton(
        'Later',
        Icons.schedule,
        onDefer!,
        theme,
      ));
    }
    
    if (buttons.isEmpty) {
      return const SizedBox.shrink();
    }
    
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: buttons,
    );
  }

  Widget _buildButton(
    String label,
    IconData icon,
    VoidCallback onPressed,
    ThemeData theme, {
    bool isPrimary = false,
    Color? color,
  }) {
    final buttonColor = color ?? (isPrimary ? theme.colorScheme.primary : theme.colorScheme.onSurface);
    
    return Material(
      color: isPrimary 
          ? buttonColor.withValues(alpha: 0.15)
          : Colors.transparent,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: isPrimary ? null : Border.all(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 16,
                color: buttonColor.withValues(alpha: 0.9),
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: buttonColor.withValues(alpha: 0.9),
                  fontWeight: isPrimary ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTestBadge(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: const Color(0xFFFF6B6B).withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: const Color(0xFFFF6B6B).withValues(alpha: 0.4),
          width: 0.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.science_outlined,
            size: 10,
            color: const Color(0xFFFF6B6B),
          ),
          const SizedBox(width: 4),
          Text(
            'TEST',
            style: theme.textTheme.bodySmall?.copyWith(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: const Color(0xFFFF6B6B),
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSourceBadge(ThemeData theme) {
    // Map category to display info
    final categoryInfo = _getCategoryInfo(interaction.category ?? 'general');
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: categoryInfo['color'].withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: categoryInfo['color'].withValues(alpha: 0.3),
          width: 0.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            categoryInfo['icon'],
            size: 10,
            color: categoryInfo['color'],
          ),
          const SizedBox(width: 4),
          Text(
            categoryInfo['label'],
            style: theme.textTheme.bodySmall?.copyWith(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: categoryInfo['color'],
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  Map<String, dynamic> _getCategoryInfo(String category) {
    switch (category.toLowerCase()) {
      case 'agency':
        return {
          'label': 'AGENCY',
          'icon': Icons.auto_awesome,
          'color': const Color(0xFF9C27B0), // Purple
        };
      case 'memory':
        return {
          'label': 'MEMORY',
          'icon': Icons.psychology,
          'color': const Color(0xFF2196F3), // Blue
        };
      case 'proactive':
        return {
          'label': 'PROACTIVE',
          'icon': Icons.lightbulb_outline,
          'color': const Color(0xFFFF9800), // Orange
        };
      case 'system':
        return {
          'label': 'SYSTEM',
          'icon': Icons.settings,
          'color': const Color(0xFF607D8B), // Blue Grey
        };
      case 'user':
        return {
          'label': 'USER',
          'icon': Icons.person_outline,
          'color': const Color(0xFF00BCD4), // Cyan
        };
      case 'general':
      default:
        // Default for uncategorized - likely from agency analyzing user context
        return {
          'label': 'CONTEXT',
          'icon': Icons.insights,
          'color': const Color(0xFF4CAF50), // Green
        };
    }
  }

  String _capitalizeFirst(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }
}
