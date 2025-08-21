---
title: Testing Strategy
---

# Testing Strategy

## Overview

AICO's frontend testing strategy ensures reliable, maintainable code through comprehensive test coverage across unit, widget, integration, and end-to-end testing. The strategy emphasizes BLoC testing, accessibility validation, and cross-platform compatibility while supporting the offline-first and reactive programming paradigms.

## Testing Pyramid

### Unit Tests (70%)
- **BLoC/Cubit logic testing**
- **Repository and service testing**
- **Utility and helper function testing**
- **Model serialization/deserialization testing**

### Widget Tests (20%)
- **Component behavior testing**
- **UI interaction testing**
- **Accessibility testing**
- **Visual regression testing**

### Integration Tests (10%)
- **End-to-end user flow testing**
- **Cross-component communication testing**
- **API integration testing**
- **Performance testing**

## BLoC Testing Strategy

### BLoC Unit Testing
```dart
// Comprehensive BLoC testing with bloc_test
group('ChatBloc', () {
  late ChatBloc chatBloc;
  late MockChatRepository mockRepository;
  late MockWebSocketClient mockWebSocket;

  setUp(() {
    mockRepository = MockChatRepository();
    mockWebSocket = MockWebSocketClient();
    chatBloc = ChatBloc(
      repository: mockRepository,
      webSocketClient: mockWebSocket,
    );
  });

  tearDown(() {
    chatBloc.close();
  });

  group('MessageSent', () {
    blocTest<ChatBloc, ChatState>(
      'emits [loading, success] when message is sent successfully',
      build: () {
        when(() => mockRepository.sendMessage(any()))
            .thenAnswer((_) async => Message.sent());
        return chatBloc;
      },
      act: (bloc) => bloc.add(MessageSent(content: 'Hello')),
      expect: () => [
        ChatState.loading(),
        ChatState.success(messages: [Message.sent()]),
      ],
      verify: (_) {
        verify(() => mockRepository.sendMessage(any())).called(1);
      },
    );

    blocTest<ChatBloc, ChatState>(
      'emits [loading, error] when message sending fails',
      build: () {
        when(() => mockRepository.sendMessage(any()))
            .thenThrow(ApiException(message: 'Network error'));
        return chatBloc;
      },
      act: (bloc) => bloc.add(MessageSent(content: 'Hello')),
      expect: () => [
        ChatState.loading(),
        ChatState.error(message: 'Network error'),
      ],
    );
  });

  group('ConnectionStateChanged', () {
    blocTest<ChatBloc, ChatState>(
      'updates connection status when connection changes',
      build: () => chatBloc,
      act: (bloc) => bloc.add(ConnectionStateChanged(isConnected: false)),
      expect: () => [
        ChatState.disconnected(),
      ],
    );
  });
});
```

### State Persistence Testing
```dart
// HydratedBloc testing
group('ChatBloc Persistence', () {
  late ChatBloc chatBloc;
  
  setUp(() {
    HydratedBloc.storage = MockStorage();
    chatBloc = ChatBloc();
  });

  test('fromJson returns correct state', () {
    final json = {
      'messages': [
        {'id': '1', 'content': 'Hello', 'timestamp': '2023-01-01T00:00:00Z'}
      ],
      'isLoading': false,
    };

    final state = chatBloc.fromJson(json);
    
    expect(state?.messages.length, equals(1));
    expect(state?.messages.first.content, equals('Hello'));
    expect(state?.isLoading, equals(false));
  });

  test('toJson returns correct map', () {
    final state = ChatState(
      messages: [Message(id: '1', content: 'Hello')],
      isLoading: false,
    );

    final json = chatBloc.toJson(state);
    
    expect(json?['messages'], isA<List>());
    expect(json?['isLoading'], equals(false));
  });
});
```

## Widget Testing

### Component Testing
```dart
// Widget testing with testWidgets
group('MessageBubble Widget', () {
  testWidgets('displays user message correctly', (tester) async {
    final message = Message(
      id: '1',
      content: 'Hello AICO',
      isFromUser: true,
      timestamp: DateTime.now(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MessageBubble(message: message),
        ),
      ),
    );

    expect(find.text('Hello AICO'), findsOneWidget);
    expect(find.byType(MessageBubble), findsOneWidget);
    
    // Verify styling for user messages
    final container = tester.widget<Container>(
      find.descendant(
        of: find.byType(MessageBubble),
        matching: find.byType(Container),
      ),
    );
    
    expect(container.decoration, isA<BoxDecoration>());
  });

  testWidgets('displays AICO message correctly', (tester) async {
    final message = Message(
      id: '2',
      content: 'Hello! How can I help you?',
      isFromUser: false,
      timestamp: DateTime.now(),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MessageBubble(message: message),
        ),
      ),
    );

    expect(find.text('Hello! How can I help you?'), findsOneWidget);
    
    // Verify different styling for AICO messages
    final messageBubble = tester.widget<MessageBubble>(find.byType(MessageBubble));
    expect(messageBubble.message.isFromUser, isFalse);
  });
});
```

### BLoC Integration Widget Testing
```dart
// Widget testing with BLoC integration
group('ChatInterface Widget', () {
  late MockChatBloc mockChatBloc;

  setUp(() {
    mockChatBloc = MockChatBloc();
  });

  testWidgets('displays messages from BLoC state', (tester) async {
    final messages = [
      Message(id: '1', content: 'Hello', isFromUser: true),
      Message(id: '2', content: 'Hi there!', isFromUser: false),
    ];

    when(() => mockChatBloc.state).thenReturn(
      ChatState.success(messages: messages),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: BlocProvider<ChatBloc>.value(
          value: mockChatBloc,
          child: ChatInterface(),
        ),
      ),
    );

    expect(find.text('Hello'), findsOneWidget);
    expect(find.text('Hi there!'), findsOneWidget);
    expect(find.byType(MessageBubble), findsNWidgets(2));
  });

  testWidgets('sends message when send button is tapped', (tester) async {
    when(() => mockChatBloc.state).thenReturn(ChatState.initial());

    await tester.pumpWidget(
      MaterialApp(
        home: BlocProvider<ChatBloc>.value(
          value: mockChatBloc,
          child: ChatInterface(),
        ),
      ),
    );

    // Enter text in input field
    await tester.enterText(find.byType(TextField), 'Test message');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pump();

    verify(() => mockChatBloc.add(MessageSent(content: 'Test message'))).called(1);
  });
});
```

## Accessibility Testing

### Accessibility Compliance Testing
```dart
// Accessibility testing
group('Accessibility Tests', () {
  testWidgets('ChatInterface meets accessibility guidelines', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: BlocProvider(
          create: (_) => ChatBloc(),
          child: ChatInterface(),
        ),
      ),
    );

    // Test semantic labels
    expect(find.bySemanticsLabel('Send message'), findsOneWidget);
    expect(find.bySemanticsLabel('Message input'), findsOneWidget);
    
    // Test keyboard navigation
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    
    final focused = tester.binding.focusManager.primaryFocus;
    expect(focused, isNotNull);

    // Test screen reader support
    final semantics = tester.getSemantics(find.byType(ChatInterface));
    expect(semantics.hasFlag(SemanticsFlag.isTextField), isTrue);
  });

  testWidgets('supports high contrast mode', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(
          brightness: Brightness.dark,
          colorScheme: ColorScheme.highContrast(),
        ),
        home: MessageBubble(
          message: Message(id: '1', content: 'Test'),
        ),
      ),
    );

    // Verify high contrast colors are applied
    final theme = Theme.of(tester.element(find.byType(MessageBubble)));
    expect(theme.colorScheme.contrast, greaterThan(7.0)); // WCAG AAA
  });
});
```

### Screen Reader Testing
```dart
// Screen reader simulation testing
group('Screen Reader Support', () {
  testWidgets('provides proper semantic structure', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              Semantics(
                header: true,
                child: Text('Chat with AICO'),
              ),
              Expanded(
                child: Semantics(
                  label: 'Conversation history',
                  child: ConversationList(),
                ),
              ),
              Semantics(
                textField: true,
                label: 'Type your message',
                child: ChatInput(),
              ),
            ],
          ),
        ),
      ),
    );

    // Verify semantic structure
    expect(find.bySemanticsLabel('Chat with AICO'), findsOneWidget);
    expect(find.bySemanticsLabel('Conversation history'), findsOneWidget);
    expect(find.bySemanticsLabel('Type your message'), findsOneWidget);
  });
});
```

## Integration Testing

### End-to-End Flow Testing
```dart
// Integration testing for complete user flows
group('End-to-End Tests', () {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('complete conversation flow', (tester) async {
    // Launch app
    app.main();
    await tester.pumpAndSettle();

    // Wait for app to load
    await tester.pumpAndSettle(Duration(seconds: 2));

    // Navigate to chat
    await tester.tap(find.byIcon(Icons.chat));
    await tester.pumpAndSettle();

    // Send a message
    await tester.enterText(find.byType(TextField), 'Hello AICO');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    // Verify message appears
    expect(find.text('Hello AICO'), findsOneWidget);

    // Wait for AICO response
    await tester.pumpAndSettle(Duration(seconds: 3));

    // Verify AICO responded
    expect(find.byType(MessageBubble), findsAtLeastNWidgets(2));
  });

  testWidgets('offline mode functionality', (tester) async {
    app.main();
    await tester.pumpAndSettle();

    // Simulate network disconnection
    await tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      const MethodChannel('connectivity_plus'),
      (call) async => 'none',
    );

    // Send message while offline
    await tester.enterText(find.byType(TextField), 'Offline message');
    await tester.tap(find.byIcon(Icons.send));
    await tester.pumpAndSettle();

    // Verify offline indicator
    expect(find.text('Offline'), findsOneWidget);
    expect(find.byIcon(Icons.cloud_off), findsOneWidget);

    // Verify message queued
    expect(find.text('Offline message'), findsOneWidget);
  });
});
```

### Performance Testing
```dart
// Performance testing
group('Performance Tests', () {
  testWidgets('chat interface renders smoothly with many messages', (tester) async {
    final messages = List.generate(1000, (index) => 
      Message(id: '$index', content: 'Message $index')
    );

    final stopwatch = Stopwatch()..start();

    await tester.pumpWidget(
      MaterialApp(
        home: ConversationList(messages: messages),
      ),
    );

    await tester.pumpAndSettle();
    stopwatch.stop();

    // Verify render time is acceptable
    expect(stopwatch.elapsedMilliseconds, lessThan(1000));
  });

  testWidgets('memory usage remains stable during scrolling', (tester) async {
    final messages = List.generate(10000, (index) => 
      Message(id: '$index', content: 'Message $index')
    );

    await tester.pumpWidget(
      MaterialApp(
        home: ConversationList(messages: messages),
      ),
    );

    // Simulate scrolling
    final listFinder = find.byType(ListView);
    await tester.fling(listFinder, Offset(0, -500), 1000);
    await tester.pumpAndSettle();

    await tester.fling(listFinder, Offset(0, 500), 1000);
    await tester.pumpAndSettle();

    // Memory usage should remain stable (tested via external monitoring)
    expect(find.byType(ListView), findsOneWidget);
  });
});
```

## Golden File Testing

### Visual Regression Testing
```dart
// Golden file testing for visual consistency
group('Golden Tests', () {
  testWidgets('message bubble golden test', (tester) async {
    final message = Message(
      id: '1',
      content: 'This is a test message for golden file testing',
      isFromUser: true,
      timestamp: DateTime(2023, 1, 1, 12, 0, 0),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.light(),
        home: Scaffold(
          body: MessageBubble(message: message),
        ),
      ),
    );

    await expectLater(
      find.byType(MessageBubble),
      matchesGoldenFile('golden/message_bubble_user.png'),
    );
  });

  testWidgets('chat interface golden test', (tester) async {
    final messages = [
      Message(id: '1', content: 'Hello', isFromUser: true),
      Message(id: '2', content: 'Hi there! How can I help?', isFromUser: false),
    ];

    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.light(),
        home: BlocProvider(
          create: (_) => ChatBloc()..add(MessagesLoaded(messages)),
          child: ChatInterface(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    await expectLater(
      find.byType(ChatInterface),
      matchesGoldenFile('golden/chat_interface.png'),
    );
  });
});
```

## Test Utilities and Helpers

### Mock Implementations
```dart
// Mock classes for testing
class MockChatRepository extends Mock implements ChatRepository {}
class MockWebSocketClient extends Mock implements WebSocketClient {}
class MockApiClient extends Mock implements ApiClient {}

// Test data builders
class MessageBuilder {
  String _id = '1';
  String _content = 'Test message';
  bool _isFromUser = true;
  DateTime _timestamp = DateTime.now();

  MessageBuilder withId(String id) {
    _id = id;
    return this;
  }

  MessageBuilder withContent(String content) {
    _content = content;
    return this;
  }

  MessageBuilder fromAico() {
    _isFromUser = false;
    return this;
  }

  Message build() => Message(
    id: _id,
    content: _content,
    isFromUser: _isFromUser,
    timestamp: _timestamp,
  );
}
```

### Test Configuration
```dart
// Test setup and configuration
class TestConfig {
  static void setupTests() {
    // Configure test environment
    TestWidgetsFlutterBinding.ensureInitialized();
    
    // Set up dependency injection for tests
    GetIt.instance.reset();
    GetIt.instance.registerLazySingleton<ChatRepository>(() => MockChatRepository());
    
    // Configure test-specific settings
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
  }

  static void tearDownTests() {
    GetIt.instance.reset();
    debugDefaultTargetPlatformOverride = null;
  }
}
```

## Continuous Integration

### Test Automation
```yaml
# GitHub Actions workflow for testing
name: Flutter Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
      
      - name: Install dependencies
        run: flutter pub get
        
      - name: Run unit tests
        run: flutter test --coverage
        
      - name: Run integration tests
        run: flutter test integration_test/
        
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage/lcov.info
```

### Coverage Requirements
- **Unit Tests**: Minimum 80% code coverage
- **Widget Tests**: All custom widgets tested
- **Integration Tests**: Critical user flows covered
- **Accessibility Tests**: All interactive elements tested

This comprehensive testing strategy ensures AICO's frontend maintains high quality, reliability, and accessibility standards while supporting continuous development and deployment practices.
