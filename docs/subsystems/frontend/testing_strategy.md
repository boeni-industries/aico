---
title: Testing Strategy
---

# Testing Strategy

## Overview

AICO's testing strategy ensures reliable, maintainable code through comprehensive coverage emphasizing BLoC testing, accessibility validation, and cross-platform compatibility while supporting offline-first operation.

## Testing Pyramid

- **Unit Tests (70%)**: BLoC logic, repositories, utilities, model serialization
- **Widget Tests (20%)**: Component behavior, UI interactions, accessibility, visual regression
- **Integration Tests (10%)**: End-to-end flows, cross-component communication, API integration, performance

## BLoC Testing

### Unit Testing
Use `bloc_test` package to test state transitions with mock dependencies. Test success and error scenarios for each event, verify repository calls, and ensure proper state emissions.

```dart
blocTest<ConversationBloc, ConversationState>(
  'emits [loading, success] when message sent',
  act: (bloc) => bloc.add(MessageSent(content: 'Hello')),
  expect: () => [ConversationState.loading(), ConversationState.success()],
);
```

### State Persistence Testing
Test HydratedBloc `fromJson()` and `toJson()` methods with mock storage. Verify state restoration after app restart and graceful handling of corrupted data.

## Widget Testing

### Component Testing
Test individual widgets in isolation using `testWidgets`. Verify text display, styling differences between user/AICO messages, and proper widget hierarchy.

### BLoC Integration Testing
Test widgets with mock BLoCs to verify state-driven UI updates and user interaction handling. Use `BlocProvider.value` with mock BLoCs and verify event dispatching.

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
Use `mockito` for repository, WebSocket, and API client mocks. Implement builder patterns for test data creation with fluent APIs.

### Test Configuration
Centralized test setup with dependency injection reset, platform overrides, and consistent test environment configuration.

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
