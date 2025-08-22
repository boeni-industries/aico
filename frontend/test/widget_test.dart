// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/core/theme/theme_data_factory.dart';

void main() {
  testWidgets('AICO theme system smoke test', (WidgetTester tester) async {
    // Test that we can create a basic app with AICO themes
    await tester.pumpWidget(MaterialApp(
      title: 'AICO Theme Test',
      theme: AicoThemeDataFactory.generateLightTheme(),
      darkTheme: AicoThemeDataFactory.generateDarkTheme(),
      home: Scaffold(
        appBar: AppBar(title: const Text('AICO')),
        body: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('AICO Theme System'),
              ElevatedButton(
                onPressed: null,
                child: Text('Toggle Theme'),
              ),
              ElevatedButton(
                onPressed: null,
                child: Text('Toggle High Contrast'),
              ),
              ElevatedButton(
                onPressed: null,
                child: Text('Reset to System Theme'),
              ),
            ],
          ),
        ),
      ),
    ));

    // Verify that the app loads with AICO branding
    expect(find.text('AICO'), findsOneWidget);
    expect(find.text('AICO Theme System'), findsOneWidget);

    // Verify theme toggle buttons are present
    expect(find.text('Toggle Theme'), findsOneWidget);
    expect(find.text('Toggle High Contrast'), findsOneWidget);
    expect(find.text('Reset to System Theme'), findsOneWidget);
  });
}
