# Testing Architecture & Infrastructure

This document outlines AICO's testing strategy, architecture, and infrastructure for the polyglot monorepo.

## Overview

AICO uses a comprehensive testing approach across all subsystems (`/cli`, `/backend`, `/frontend`, `/studio`) with consistent patterns and tooling. The testing strategy emphasizes reliability, maintainability, and developer productivity.

## Testing Philosophy

- **Quality First**: Tests are first-class citizens, not afterthoughts
- **Fast Feedback**: Quick test execution for rapid development cycles  
- **Comprehensive Coverage**: Unit, integration, and end-to-end testing
- **Polyglot Consistency**: Consistent patterns across different technologies
- **Real-World Validation**: Tests use actual AICO configuration and data

## Directory Structure

Each subsystem follows a consistent testing structure that mirrors the source code organization:

```
/{subsystem}/tests/
├── unit/                    # Unit tests (mirror source structure)
│   ├── api/
│   ├── services/
│   └── models/
├── integration/             # Integration tests
│   ├── test_auth_cycle.py
│   └── test_api_endpoints.py
├── fixtures/                # Test data and utilities
│   ├── mock_data.py
│   └── test_config.py
└── conftest.py              # Test configuration
```

**Unit Tests** mirror the source code structure, making it easy to find and maintain tests alongside the code they validate.

**Integration Tests** focus on component interactions and full workflow validation, including authentication flows and API endpoint testing.

**Test Support** includes reusable fixtures, mock objects, and shared configuration that reduces duplication across test suites.

## Test Categories

### Unit Tests
- **Purpose**: Test individual components in isolation
- **Scope**: Functions, classes, methods
- **Characteristics**: Fast, isolated, mocked dependencies
- **Tools**: pytest (Python), Jest (React), Flutter test framework

### Integration Tests  
- **Purpose**: Test component interactions
- **Scope**: API endpoints, database operations, service integration
- **Characteristics**: Real dependencies, database transactions
- **Current Examples**: Authentication flows, session management

### End-to-End Tests
- **Purpose**: Test complete user workflows
- **Scope**: Full system interactions across subsystems
- **Characteristics**: Real environment, user scenarios
- **Future**: Cross-subsystem workflows

### Performance Tests
- **Purpose**: Validate system performance characteristics
- **Scope**: Load testing, stress testing, benchmarks
- **Tools**: pytest-benchmark, Artillery, Flutter performance tests

## Current Implementation

### Backend Integration Tests

The backend currently implements comprehensive integration tests that validate critical authentication and session management functionality:

```bash
# Run from project root
backend/.venv/Scripts/python.exe backend/tests/integration/test_auth_dependency.py
backend/.venv/Scripts/python.exe backend/tests/integration/test_full_auth_cycle.py
backend/.venv/Scripts/python.exe backend/tests/integration/test_session_endpoints.py
```

**Authentication Dependency Testing** validates JWT token generation, validation, and integration between authentication services and the API gateway.

**Full Authentication Lifecycle Testing** provides end-to-end validation covering user login, token generation, protected resource access, session management, and proper logout/token revocation for both REST and WebSocket protocols.

**Session Endpoint Testing** focuses on session creation, validation, renewal, and cleanup, including edge cases like concurrent sessions and timeouts.

**Key Features:**
- Real AICO configuration and encrypted database (not mocked)
- Multi-protocol coverage (REST + WebSocket)
- Complete token lifecycle verification
- Database session auditing and cleanup validation

## Future Testing Infrastructure

### Test Framework Strategy

The future testing infrastructure will leverage industry-standard frameworks tailored to each subsystem's technology stack, ensuring optimal developer experience and robust test execution.

#### Backend Testing Framework

The backend will use pytest with configuration emphasizing strict test discovery and comprehensive coverage:

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--strict-markers", "--cov=backend", "--cov-report=html"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "auth: Authentication tests"
]
```

This enables developers to run specific test subsets (`pytest -m unit`) during development while ensuring comprehensive validation in CI/CD.

#### Frontend Testing Framework

Flutter's built-in testing framework provides widget testing and integration with Dart's ecosystem:

```dart
// test/flutter_test_config.dart
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  setUpAll(() => /* Global test setup */);
  await testMain();
}
```

#### Studio Testing Framework

Jest with React Testing Library for component and integration testing:

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch"
  },
  "jest": {
    "testEnvironment": "jsdom"
  }
}
```

### Test Data Management Strategy

Effective test data management is crucial for maintaining reliable, fast, and maintainable tests across the AICO ecosystem. The strategy balances realism with test isolation and performance.

#### Fixture-Based Data Management

Reusable test fixtures organized by domain reduce duplication and ensure consistency:

```python
# backend/tests/fixtures/auth_fixtures.py
@pytest.fixture
def mock_user():
    return User(user_uuid="test-uuid", username="testuser", roles=["admin"])

@pytest.fixture
def test_db():
    conn = get_connection(":memory:")  # In-memory for speed
    yield conn
    conn.close()
```

#### Database Testing Strategy

**Unit Tests** use in-memory SQLite for maximum speed and isolation.

**Integration Tests** use dedicated test database instances with controlled test data that mirrors production schema.

The infrastructure includes automatic schema setup/teardown, transaction-based isolation, and utilities for creating realistic test data.

#### Mock and Stub Management

External dependencies are mocked to balance test isolation with realistic behavior simulation, including external APIs, file operations, and network communications.

### CI/CD Integration Strategy

The continuous integration and deployment pipeline will provide automated testing across all subsystems, ensuring that changes are validated before integration and deployment. The strategy emphasizes parallel execution, comprehensive coverage, and fast feedback.

#### Multi-Subsystem Testing Pipeline

The CI/CD pipeline will run tests for all four subsystems (CLI, Backend, Frontend, Studio) in parallel, maximizing efficiency and providing rapid feedback to developers. Each subsystem will have its own optimized testing environment with appropriate language runtimes and dependencies.

#### Quality Gates and Coverage

The pipeline will enforce quality gates including minimum code coverage thresholds, successful test execution, and performance benchmarks. Coverage reports will be automatically generated and tracked over time, providing visibility into testing effectiveness and identifying areas that need additional test coverage.

#### Test Result Integration

Test results will be integrated with the development workflow through pull request status checks, coverage reporting services, and notification systems. This ensures that test failures are immediately visible to developers and that code quality standards are maintained.

#### Environment Management

The CI/CD system will manage multiple testing environments, including isolated database instances, mock external services, and realistic configuration scenarios. This approach ensures that tests run in consistent, predictable environments while avoiding interference between parallel test runs.

## Testing Best Practices

### General Principles
- **AAA Pattern**: Arrange, Act, Assert
- **Single Responsibility**: One test, one concern
- **Descriptive Names**: Test names describe behavior
- **Independent Tests**: No test dependencies
- **Fast Execution**: Quick feedback loops

### Authentication Testing
- **Real Credentials**: Use actual user credentials for integration tests
- **Session Lifecycle**: Test complete authentication flows
- **Security Validation**: Verify token revocation and session cleanup
- **Protocol Coverage**: Test both REST and WebSocket authentication

### Database Testing
- **Transaction Isolation**: Each test in its own transaction
- **Cleanup**: Proper test data cleanup
- **Audit Trails**: Verify session and audit logging
- **Migration Testing**: Test schema migrations

### API Testing
- **Contract Testing**: Verify API contracts
- **Error Handling**: Test error conditions
- **Authorization**: Test role-based access control
- **Rate Limiting**: Test API limits and throttling

## Performance Considerations

### Test Execution Speed
- **Parallel Execution**: Run tests in parallel where possible
- **Test Categorization**: Separate fast and slow tests
- **Database Optimization**: Use in-memory databases for unit tests
- **Mock External Services**: Avoid network calls in unit tests

### Resource Management
- **Memory Usage**: Monitor test memory consumption
- **Database Connections**: Proper connection pooling and cleanup
- **File Handles**: Clean up temporary files and resources
- **Process Isolation**: Avoid test interference

## Monitoring and Reporting

### Test Metrics
- **Coverage Reports**: Code coverage tracking
- **Test Duration**: Monitor test execution times
- **Flaky Tests**: Identify and fix unreliable tests
- **Failure Analysis**: Root cause analysis of test failures

### Quality Gates
- **Minimum Coverage**: Enforce coverage thresholds
- **Test Success Rate**: Require passing tests for deployment
- **Performance Benchmarks**: Maintain performance standards
- **Security Scans**: Automated security testing

## Future Enhancements

### Planned Improvements
- [ ] Complete pytest framework setup for backend
- [ ] Flutter test framework configuration
- [ ] React/Jest setup for studio
- [ ] CLI test framework (Python/pytest)
- [ ] Cross-subsystem end-to-end tests
- [ ] Performance testing infrastructure
- [ ] Test data management system
- [ ] Automated test generation tools

### Advanced Features
- [ ] Property-based testing with Hypothesis
- [ ] Mutation testing for test quality
- [ ] Visual regression testing for UI
- [ ] Load testing with realistic scenarios
- [ ] Chaos engineering tests
- [ ] Security penetration testing automation

## Running Tests

### Current Test Execution

Current integration tests use direct Python execution with detailed output:

```bash
# Backend integration tests
backend/.venv/Scripts/python.exe backend/tests/integration/test_full_auth_cycle.py
backend/.venv/Scripts/python.exe backend/tests/integration/test_auth_dependency.py
backend/.venv/Scripts/python.exe backend/tests/integration/test_session_endpoints.py
```

Each test provides comprehensive output including database session analysis and detailed failure reporting.

### Future Framework-Based Execution

Streamlined execution through framework-specific commands:

```bash
# Backend
pytest tests/                    # All tests
pytest tests/unit/              # Unit tests only
pytest -m auth                  # Authentication tests

# Frontend
flutter test

# Studio
npm test

# All subsystems
make test-all
```

This approach supports both targeted execution during development and comprehensive validation in CI/CD pipelines.

## Conclusion

AICO's testing architecture provides a solid foundation for reliable software development across the polyglot monorepo. The current integration tests validate critical authentication and session management functionality, while the planned infrastructure will support comprehensive testing at all levels.

The emphasis on real-world validation, consistent patterns, and developer productivity ensures that testing remains an enabler rather than a bottleneck in the development process.
