import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/agents_list_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_state.dart';

void main() {
  runApp(const AiAgentApp());
}

class AiAgentApp extends StatelessWidget {
  const AiAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthState()..load(),
      child: MaterialApp(
        title: 'Мой ИИ-агент',
        theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple)),
        home: const RootScreen(),
      ),
    );
  }
}

class RootScreen extends StatelessWidget {
  const RootScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthState>(
      builder: (context, auth, _) {
        if (!auth.loaded) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        return auth.isLoggedIn ? const AgentsListScreen() : const LoginScreen();
      },
    );
  }
}
