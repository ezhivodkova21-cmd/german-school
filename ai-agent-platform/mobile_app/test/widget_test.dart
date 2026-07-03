import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:ai_agent_app/main.dart';

void main() {
  testWidgets('Shows login screen when logged out', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});

    await tester.pumpWidget(const AiAgentApp());
    await tester.pumpAndSettle();

    expect(find.text('Мой ИИ-агент'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Войти'), findsOneWidget);
  });
}
