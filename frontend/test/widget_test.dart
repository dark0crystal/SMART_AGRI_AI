import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('MaterialApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(child: Text('Smart Agri AI')),
        ),
      ),
    );

    expect(find.text('Smart Agri AI'), findsOneWidget);
  });
}
