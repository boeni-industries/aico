import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:flutter/material.dart';

class SystemStatusBar extends StatelessWidget {
  const SystemStatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final aicoTheme = theme.extension<AicoThemeExtension>()!;
    
    return Row(
      children: [
        // Connection status
        _buildStatusIndicator(
          context,
          aicoTheme,
          icon: Icons.wifi,
          status: 'Connected',
          isHealthy: true,
        ),
        
        const SizedBox(width: 16),
        
        // System health
        _buildStatusIndicator(
          context,
          aicoTheme,
          icon: Icons.psychology_outlined,
          status: 'Active',
          isHealthy: true,
        ),
      ],
    );
  }

  Widget _buildStatusIndicator(
    BuildContext context,
    AicoThemeExtension aicoTheme, {
    required IconData icon,
    required String status,
    required bool isHealthy,
  }) {
    final statusColor = isHealthy 
      ? aicoTheme.colors.success 
      : aicoTheme.colors.error;
    
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: statusColor,
          ),
        ),
        
        const SizedBox(width: 6),
        
        Icon(
          icon,
          size: 16,
          color: aicoTheme.colors.onSurface.withValues(alpha: 0.6),
        ),
        
        const SizedBox(width: 4),
        
        Text(
          status,
          style: aicoTheme.textTheme.bodySmall?.copyWith(
            color: aicoTheme.colors.onSurface.withValues(alpha: 0.6),
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
