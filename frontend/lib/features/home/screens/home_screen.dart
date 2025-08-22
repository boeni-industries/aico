import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:aico_frontend/features/auth/bloc/auth_bloc.dart';
import 'package:aico_frontend/features/home/widgets/chat_input.dart';
import 'package:aico_frontend/features/home/widgets/companion_avatar.dart';
import 'package:aico_frontend/features/home/widgets/system_status_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final aicoTheme = theme.extension<AicoThemeExtension>()!;
    
    return Scaffold(
      backgroundColor: aicoTheme.colors.background,
      body: SafeArea(
        child: Column(
          children: [
            // System status and logout
            _buildTopBar(context, aicoTheme),
            
            // Main companion interface
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0),
                child: Column(
                  children: [
                    const Spacer(flex: 2),
                    
                    // Avatar centerpiece
                    const CompanionAvatar(),
                    
                    const SizedBox(height: 32),
                    
                    // Welcome message
                    _buildWelcomeMessage(aicoTheme),
                    
                    const Spacer(flex: 3),
                    
                    // Chat input
                    const ChatInput(),
                    
                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, AicoThemeExtension aicoTheme) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      child: Row(
        children: [
          // System status
          const Expanded(child: SystemStatusBar()),
          
          // Logout button
          AicoButton.minimal(
            onPressed: () {
              context.read<AuthBloc>().add(const AuthLogoutRequested());
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.logout,
                  size: 18,
                  color: aicoTheme.colors.onSurface.withValues(alpha: 0.7),
                ),
                const SizedBox(width: 8),
                Text(
                  'Sign Out',
                  style: aicoTheme.textTheme.labelMedium?.copyWith(
                    color: aicoTheme.colors.onSurface.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWelcomeMessage(AicoThemeExtension aicoTheme) {
    return Column(
      children: [
        Text(
          'Hello! I\'m AICO',
          style: aicoTheme.textTheme.headlineMedium?.copyWith(
            color: aicoTheme.colors.onSurface,
            fontWeight: FontWeight.w600,
          ),
          textAlign: TextAlign.center,
        ),
        
        const SizedBox(height: 12),
        
        Text(
          'Your AI companion is ready to chat, learn, and grow with you.',
          style: aicoTheme.textTheme.bodyLarge?.copyWith(
            color: aicoTheme.colors.onSurface.withValues(alpha: 0.7),
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}
