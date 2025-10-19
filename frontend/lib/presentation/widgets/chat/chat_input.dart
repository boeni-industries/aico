import 'package:flutter/material.dart';

import 'package:aico_frontend/presentation/widgets/common/animated_button.dart';

class ChatInput extends StatefulWidget {
  final TextEditingController controller;
  final VoidCallback? onSend;
  final VoidCallback? onVoicePressed;
  final bool isEnabled;

  const ChatInput({
    super.key,
    required this.controller,
    this.onSend,
    this.onVoicePressed,
    this.isEnabled = true,
  });

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  bool _hasText = false;
  final GlobalKey _sendButtonKey = GlobalKey();
  final GlobalKey _voiceButtonKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onTextChanged() {
    final hasText = widget.controller.text.trim().isNotEmpty;
    if (hasText != _hasText) {
      setState(() {
        _hasText = hasText;
      });
    }
  }

  void _handleSend() {
    if (_hasText && widget.onSend != null) {
      widget.onSend!();
      // Show success animation after send
      Future.delayed(const Duration(milliseconds: 100), () {
        final state = _sendButtonKey.currentState;
        if (state != null && state.mounted) {
          // Access showSuccess through dynamic call since state type is private
          (state as dynamic).showSuccess();
        }
      });
    }
  }
  
  void _handleVoice() {
    if (widget.onVoicePressed != null) {
      widget.onVoicePressed!();
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outline.withValues(alpha: 0.2),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          // Voice input button with micro-interactions
          AnimatedButton(
            key: _voiceButtonKey,
            onPressed: widget.isEnabled ? _handleVoice : null,
            icon: Icons.mic,
            isEnabled: widget.isEnabled,
            size: 48,
            backgroundColor: theme.colorScheme.primaryContainer,
            foregroundColor: theme.colorScheme.onPrimaryContainer,
            tooltip: 'Voice input',
          ),
          const SizedBox(width: 8),
          // Text input field
          Expanded(
            child: TextField(
              controller: widget.controller,
              enabled: widget.isEnabled,
              decoration: InputDecoration(
                hintText: 'Type a message...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: theme.colorScheme.surfaceContainerHighest,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
              maxLines: null,
              textCapitalization: TextCapitalization.sentences,
              onSubmitted: (_) => _handleSend(),
            ),
          ),
          const SizedBox(width: 8),
          // Send button with micro-interactions and success animation
          AnimatedButton(
            key: _sendButtonKey,
            onPressed: (_hasText && widget.isEnabled) ? _handleSend : null,
            icon: Icons.send,
            successIcon: Icons.check,
            isEnabled: _hasText && widget.isEnabled,
            size: 48,
            backgroundColor: _hasText 
                ? theme.colorScheme.primary 
                : theme.colorScheme.surfaceContainerHighest,
            foregroundColor: _hasText 
                ? theme.colorScheme.onPrimary 
                : theme.colorScheme.onSurfaceVariant,
            tooltip: 'Send message',
          ),
        ],
      ),
    );
  }
}
