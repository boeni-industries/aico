import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:flutter/material.dart';

class ChatInput extends StatefulWidget {
  const ChatInput({super.key});

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  bool _isComposing = false;

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSubmitted(String text) {
    if (text.trim().isEmpty) return;
    
    // TODO: Send message to chat service
    debugPrint('Sending message: $text');
    
    _controller.clear();
    setState(() {
      _isComposing = false;
    });
  }

  void _handleChanged(String text) {
    setState(() {
      _isComposing = text.trim().isNotEmpty;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final aicoTheme = theme.extension<AicoThemeExtension>()!;
    
    return Container(
      constraints: const BoxConstraints(maxWidth: 600),
      child: Row(
        children: [
          // Voice input button
          Container(
            margin: const EdgeInsets.only(right: 12),
            child: AicoButton.secondary(
              onPressed: () {
                // TODO: Implement voice input
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Voice input coming soon!'),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              },
              width: 48,
              height: 48,
              padding: EdgeInsets.zero,
              child: Icon(
                Icons.mic_outlined,
                color: aicoTheme.colors.primary,
                size: 20,
              ),
            ),
          ),
          
          // Text input field
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: aicoTheme.colors.outline,
                  width: 1,
                ),
                color: aicoTheme.colors.surface,
              ),
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                onChanged: _handleChanged,
                onSubmitted: _handleSubmitted,
                textInputAction: TextInputAction.send,
                maxLines: null,
                style: aicoTheme.textTheme.bodyLarge?.copyWith(
                  color: aicoTheme.colors.onSurface,
                ),
                decoration: InputDecoration(
                  hintText: 'Chat with AICO...',
                  hintStyle: aicoTheme.textTheme.bodyLarge?.copyWith(
                    color: aicoTheme.colors.onSurface.withValues(alpha: 0.5),
                  ),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 14,
                  ),
                ),
              ),
            ),
          ),
          
          // Send button
          Container(
            margin: const EdgeInsets.only(left: 12),
            child: AicoButton.primary(
              onPressed: _isComposing 
                ? () => _handleSubmitted(_controller.text)
                : null,
              width: 48,
              height: 48,
              padding: EdgeInsets.zero,
              child: Icon(
                Icons.send_rounded,
                color: aicoTheme.colors.onPrimary,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
