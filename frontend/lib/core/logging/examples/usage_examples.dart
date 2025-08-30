import 'package:aico_frontend/core/logging/logging.dart';
import 'package:flutter/material.dart';

/// Example usage of AICO logging system in various scenarios
class LoggingExamples {
  
  /// Example: Basic logging in a widget
  static void widgetLogging() {
    // Simple info log
    Log.i('frontend.chat_ui', 'ui/button/click', 'User clicked Send button');
    
    // Debug log with extra data
    Log.d('frontend.chat_ui', 'ui/state/change', 'Chat state updated', extra: {
      'previous_state': 'idle',
      'new_state': 'typing',
      'message_count': 5,
    });
    
    // Warning log
    Log.w('frontend.connection', 'network/slow', 'Network response taking longer than expected');
  }

  /// Example: Error logging with exception handling
  static Future<void> errorLogging() async {
    try {
      // Some operation that might fail
      await someRiskyOperation();
    } catch (error, stackTrace) {
      // Log error with full context
      await Log.e(
        'frontend.api_client',
        'api/request/failed',
        'Failed to send message to backend',
        error: error,
        stackTrace: stackTrace,
        extra: {
          'endpoint': '/api/v1/messages',
          'retry_count': 2,
          'user_action': 'send_message',
        },
      );
    }
  }

  /// Example: BLoC integration
  static void blocLogging() {
    // In a BLoC event handler
    Log.i('frontend.chat_bloc', 'bloc/event/received', 'Processing SendMessage event');
    
    // State transition logging
    Log.d('frontend.chat_bloc', 'bloc/state/transition', 'State changed', extra: {
      'from': 'ChatInitial',
      'to': 'ChatLoading',
      'event': 'SendMessageEvent',
    });
  }

  /// Example: Repository pattern logging
  static Future<void> repositoryLogging() async {
    // Before API call
    Log.d('frontend.chat_repository', 'api/request/start', 'Sending message to backend');
    
    try {
      // API call here
      await Future.delayed(Duration(seconds: 1));
      
      // Success logging
      Log.i('frontend.chat_repository', 'api/request/success', 'Message sent successfully', extra: {
        'response_time_ms': 1000,
        'message_id': 'msg_123',
      });
    } catch (e) {
      // Error logging
      Log.e('frontend.chat_repository', 'api/request/error', 'Failed to send message', error: e);
    }
  }

  /// Example: User interaction logging
  static void userInteractionLogging() {
    // Button clicks
    Log.i('frontend.chat_ui', 'ui/interaction/click', 'User clicked avatar settings');
    
    // Navigation
    Log.d('frontend.navigation', 'ui/navigation/route', 'Navigated to settings screen', extra: {
      'from_route': '/chat',
      'to_route': '/settings',
      'navigation_type': 'push',
    });
    
    // Form interactions
    Log.d('frontend.settings_ui', 'ui/form/input', 'User updated theme preference', extra: {
      'field': 'theme',
      'old_value': 'light',
      'new_value': 'dark',
    });
  }

  /// Example: Performance logging
  static void performanceLogging() {
    final stopwatch = Stopwatch()..start();
    
    // Start operation
    Log.d('frontend.avatar_system', 'performance/operation/start', 'Starting avatar animation');
    
    // Simulate work
    // ... do work ...
    
    stopwatch.stop();
    
    // Log performance metrics
    Log.i('frontend.avatar_system', 'performance/operation/complete', 'Avatar animation completed', extra: {
      'duration_ms': stopwatch.elapsedMilliseconds,
      'animation_type': 'facial_expression',
      'frame_count': 60,
    });
  }

  /// Example: Connection state logging
  static void connectionLogging() {
    // Connection attempts
    Log.i('frontend.connection_manager', 'connection/attempt', 'Attempting to connect to backend');
    
    // Connection success
    Log.i('frontend.connection_manager', 'connection/established', 'Connected to backend', extra: {
      'protocol': 'websocket',
      'endpoint': 'ws://localhost:8772/ws',
      'connection_time_ms': 150,
    });
    
    // Connection issues
    Log.w('frontend.connection_manager', 'connection/degraded', 'Connection quality degraded', extra: {
      'latency_ms': 500,
      'packet_loss_percent': 2.5,
    });
  }

  /// Example: Setting up user context
  static void setupUserContext() {
    // Set user context when user logs in or is identified
    Log.setUser(userId: 'user_123', sessionId: 'session_456');
    
    // Set environment
    Log.setEnvironment('production');
    
    // Now all subsequent logs will include this context
    Log.i('frontend.auth', 'user/login/success', 'User logged in successfully');
  }

  /// Example: Flushing logs before app termination
  static Future<void> appTerminationLogging() async {
    Log.i('frontend.app', 'app/lifecycle/terminating', 'App is terminating');
    
    // Ensure all logs are sent before app closes
    await Log.flush();
  }

  /// Example: Checking buffer status for debugging
  static void bufferStatusExample() {
    final status = Log.bufferStatus;
    
    if (status['pending']! > 100) {
      Log.w('frontend.logging', 'logging/buffer/high', 'High number of pending logs', extra: status);
    }
  }

  // Dummy method for example
  static Future<void> someRiskyOperation() async {
    throw Exception('Something went wrong');
  }
}

/// Example widget showing logging integration
class ExampleChatWidget extends StatefulWidget {
  const ExampleChatWidget({super.key});

  @override
  State<ExampleChatWidget> createState() => _ExampleChatWidgetState();
}

class _ExampleChatWidgetState extends State<ExampleChatWidget> {
  final TextEditingController _controller = TextEditingController();

  @override
  void initState() {
    super.initState();
    Log.d('frontend.chat_widget', 'widget/lifecycle/init', 'Chat widget initialized');
  }

  @override
  void dispose() {
    Log.d('frontend.chat_widget', 'widget/lifecycle/dispose', 'Chat widget disposed');
    _controller.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final message = _controller.text.trim();
    
    if (message.isEmpty) {
      Log.w('frontend.chat_widget', 'ui/validation/empty_message', 'User tried to send empty message');
      return;
    }

    Log.i('frontend.chat_widget', 'ui/action/send_message', 'User sending message', extra: {
      'message_length': message.length,
      'has_emoji': message.contains(RegExp(r'[\u{1f600}-\u{1f64f}]', unicode: true)),
    });

    // Clear input
    _controller.clear();
    
    // Here you would typically call a BLoC or repository
    // which would have their own logging
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TextField(
          controller: _controller,
          decoration: InputDecoration(hintText: 'Type a message...'),
          onChanged: (text) {
            // Log typing activity (but not the actual content for privacy)
            Log.d('frontend.chat_widget', 'ui/input/typing', 'User typing', extra: {
              'text_length': text.length,
            });
          },
        ),
        ElevatedButton(
          onPressed: _sendMessage,
          child: Text('Send'),
        ),
      ],
    );
  }
}
