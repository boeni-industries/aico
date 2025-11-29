import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../providers/avatar_state_provider.dart';
import '../../../providers/conversation_provider.dart';

/// Controller for typing detection and avatar state synchronization
/// 
/// Manages:
/// - Typing start/stop detection with 1-second debounce
/// - Avatar ring state transitions (listening → thinking → idle)
/// - Cleanup of timers on disposal
class TypingController {
  final WidgetRef ref;
  final TextEditingController textController;
  
  Timer? _typingTimer;
  bool _isUserTyping = false;

  TypingController({
    required this.ref,
    required this.textController,
  }) {
    textController.addListener(_onTypingChanged);
  }

  bool get isUserTyping => _isUserTyping;

  void _onTypingChanged() {
    final hasText = textController.text.trim().isNotEmpty;
    
    // Cancel existing timer
    _typingTimer?.cancel();
    
    if (hasText && !_isUserTyping) {
      // User started typing - switch to listening mode
      _isUserTyping = true;
      ref.read(avatarRingStateProvider.notifier).startListening(intensity: 0.6);
    } else if (hasText) {
      // User is still typing - reset timer
      _typingTimer = Timer(const Duration(seconds: 1), () {
        // User stopped typing for 1 second
        _isUserTyping = false;
        final avatarNotifier = ref.read(avatarRingStateProvider.notifier);
        final conversationState = ref.read(conversationProvider);
        
        // Return to appropriate state
        if (conversationState.isSendingMessage || conversationState.isStreaming) {
          avatarNotifier.startThinking();
        } else {
          avatarNotifier.returnToIdle();
        }
      });
    } else if (!hasText && _isUserTyping) {
      // Text cleared - return to idle immediately
      _isUserTyping = false;
      _typingTimer = Timer(const Duration(seconds: 1), () {
        ref.read(avatarRingStateProvider.notifier).returnToIdle();
      });
    }
  }

  void dispose() {
    _typingTimer?.cancel();
    textController.removeListener(_onTypingChanged);
  }
}
