---
title: Testing Strategy
---

# Testing Strategy

## Overview

AICO's testing strategy ensures reliable, maintainable code through comprehensive coverage emphasizing Riverpod provider testing, accessibility validation, and cross-platform compatibility while supporting offline-first operation.

## Testing Pyramid

- **Unit Tests (70%)**: StateNotifier logic, repositories, use cases, model serialization
- **Widget Tests (20%)**: Component behavior, UI interactions, accessibility, visual regression
- **Integration Tests (10%)**: End-to-end flows, provider integration, API communication, performance

## Riverpod Provider Testing

### StateNotifier Testing
Test StateNotifier state transitions with provider overrides and mock dependencies. Test success and error scenarios for each method, verify repository calls, and ensure proper state updates.

```dart
testWidgets('conversation provider sends message successfully', (tester) async {
  final mockRepository = MockMessageRepository();
  when(mockRepository.sendMessage(any)).thenAnswer((_) async => testMessage);
  
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        messageRepositoryProvider.overrideWithValue(mockRepository),
      ],
      child: Consumer(
        builder: (context, ref, _) {
          final notifier = ref.read(conversationProvider.notifier);
          return ElevatedButton(
            onPressed: () => notifier.sendMessage('Hello'),
            child: Text('Send'),
          );
        },
      ),
    ),
  );
  
  await tester.tap(find.byType(ElevatedButton));
  await tester.pumpAndSettle();
  
  verify(mockRepository.sendMessage('Hello')).called(1);
});
```

### State Persistence Testing
Test secure storage and shared preferences persistence with mock storage providers. Verify state restoration on app restart and graceful handling of corrupted or missing data.

## Widget Testing

### Component Testing
Test individual widgets in isolation using `testWidgets`. Verify text display, styling differences between user/AICO messages, and proper widget hierarchy.

### Provider Integration Testing
Test widgets with provider overrides to verify state-driven UI updates and user interaction handling. Use `ProviderScope` with overridden providers and verify method calls on StateNotifiers.

```dart
testWidgets('home screen shows conversation messages', (tester) async {
  final mockConversationNotifier = MockConversationNotifier();
  when(mockConversationNotifier.state).thenReturn(
    ConversationState(messages: [testMessage1, testMessage2]),
  );
  
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        conversationProvider.overrideWith((ref) => mockConversationNotifier),
      ],
      child: MaterialApp(home: HomeScreen()),
    ),
  );
  
  expect(find.text(testMessage1.content), findsOneWidget);
  expect(find.text(testMessage2.content), findsOneWidget);
});
```

## Accessibility Testing

### Compliance Testing
Verify semantic labels, keyboard navigation, and screen reader support. Test high contrast mode compatibility and ensure WCAG AAA contrast ratios (>7.0).

### Screen Reader Support
Test proper semantic structure with headers, labels, and text field identification. Verify conversation history and input areas are properly announced.

## Integration Testing

### End-to-End Flows
Test complete user journeys from app launch through conversation flows. Verify offline mode functionality with network disconnection simulation and message queuing.

### Performance Testing
Test rendering performance with large message lists (<1000ms render time). Verify memory stability during scrolling operations and smooth 60fps animations.

## Visual Regression Testing

Use golden file testing with `matchesGoldenFile()` to detect unintended visual changes. Test key components like message bubbles and conversation interface across light/dark themes.

## Test Utilities

### Mock Implementations
Use `mockito` for repository, API client, and service mocks. Create mock StateNotifiers for testing widget interactions. Implement builder patterns for test data creation with fluent APIs.

```dart
// Mock StateNotifier for testing
class MockConversationNotifier extends Mock implements ConversationNotifier {}

// Mock repository
class MockMessageRepository extends Mock implements MessageRepository {}

// Test data builders
class MessageBuilder {
  String _content = 'Test message';
  String _userId = 'user123';
  
  MessageBuilder withContent(String content) {
    _content = content;
    return this;
  }
  
  MessageBuilder fromUser(String userId) {
    _userId = userId;
    return this;
  }
  
  Message build() => Message(
    id: 'test-id',
    content: _content,
    userId: _userId,
    timestamp: DateTime.now(),
    conversationId: 'test-conversation',
    type: MessageType.text,
    status: MessageStatus.sent,
  );
}
```

### Test Configuration
Centralized test setup with provider scope configuration, platform overrides, and consistent test environment setup.

```dart
// Test utilities for provider testing
class TestProviderScope {
  static Widget createApp({
    required Widget child,
    List<Override> overrides = const [],
  }) {
    return ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        home: child,
        theme: ThemeData.light(),
      ),
    );
  }
}
```

## Code Coverage

### Coverage Generation
Generate Flutter test coverage using the built-in coverage support:

```bash
# Generate coverage data
flutter test --coverage
# Output: coverage/lcov.info
```

### HTML Coverage Reports
Convert LCOV data to interactive HTML reports for detailed analysis:

```bash
# Install cross-platform LCOV viewer (one-time setup)
npm install -g @lcov-viewer/cli

# Generate HTML coverage report
lcov-viewer lcov coverage/lcov.info --output coverage/html

# Open report in browser
# Windows: start coverage/html/index.html
# macOS: open coverage/html/index.html
# Linux: xdg-open coverage/html/index.html
```

### Coverage Analysis Workflow
1. **Run tests with coverage**: `flutter test --coverage`
2. **Generate HTML report**: `lcov-viewer lcov coverage/lcov.info --output coverage/html`
3. **Review coverage gaps**: Open HTML report to identify untested code
4. **Add targeted tests**: Focus on uncovered critical paths
5. **Iterate**: Repeat process to improve coverage

### Known Coverage Limitations
Flutter's coverage instrumentation has limitations with certain code patterns:

- **Static factory methods**: Coverage may not be properly tracked for static methods in factory classes
- **Stream operations**: Complex stream subscriptions during coverage collection can cause timing issues
- **Widget constructors**: Some widget initialization code may not be tracked accurately

**Workaround**: Focus on functional testing over coverage metrics for these patterns. Ensure comprehensive unit tests exist even if coverage reports show gaps.

### Coverage Data Storage
Coverage data is stored in `frontend/coverage/` directory:
```
frontend/coverage/
├── lcov.info          # Raw LCOV coverage data
└── html/              # Generated HTML reports
    ├── index.html     # Main coverage report
    └── ...            # Supporting files
```

**Important**: The `coverage/` directory should be added to `.gitignore` as coverage data is generated locally and should not be committed.

## Continuous Integration

### Test Automation
GitHub Actions workflow running unit tests with coverage reporting, integration tests, and accessibility validation on every push and pull request.

### Coverage Requirements
- **Unit Tests**: Minimum 80% code coverage
- **Widget Tests**: All custom widgets tested  
- **Integration Tests**: Critical user flows covered
- **Accessibility Tests**: All interactive elements tested

This strategy ensures high quality, reliability, and accessibility standards while supporting continuous development practices.
