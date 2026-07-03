import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../services/auth_state.dart';

class AgentWizardScreen extends StatefulWidget {
  const AgentWizardScreen({super.key});

  @override
  State<AgentWizardScreen> createState() => _AgentWizardScreenState();
}

class _AgentWizardScreenState extends State<AgentWizardScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _roleController = TextEditingController();
  final _personalityController = TextEditingController();
  final _goalController = TextEditingController();
  final _restrictionsController = TextEditingController();
  final _greetingController = TextEditingController(text: 'Привет! Чем могу помочь?');

  bool _saving = false;
  String? _error;

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final auth = context.read<AuthState>();
      await auth.api.createAgent(
        name: _nameController.text.trim(),
        role: _roleController.text.trim(),
        personality: _personalityController.text.trim(),
        goal: _goalController.text.trim(),
        restrictions: _restrictionsController.text.trim(),
        greeting: _greetingController.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = e is ApiException ? e.message : 'Не удалось создать агента.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _roleController.dispose();
    _personalityController.dispose();
    _goalController.dispose();
    _restrictionsController.dispose();
    _greetingController.dispose();
    super.dispose();
  }

  Widget _field({
    required TextEditingController controller,
    required String label,
    required String hint,
    int maxLines = 1,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: TextFormField(
        controller: controller,
        maxLines: maxLines,
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          border: const OutlineInputBorder(),
        ),
        validator: (value) =>
            (value == null || value.trim().isEmpty) ? 'Заполните это поле' : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Новый агент')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'Ответьте на несколько простых вопросов — и агент будет готов к общению.',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            _field(
              controller: _nameController,
              label: 'Как зовут агента?',
              hint: 'Например: Личный помощник Аня',
            ),
            _field(
              controller: _roleController,
              label: 'Кем он будет для вас?',
              hint: 'Например: персональный ассистент по планированию дня',
            ),
            _field(
              controller: _personalityController,
              label: 'Какой у него характер?',
              hint: 'Например: дружелюбный, краткий, без канцеляризмов',
              maxLines: 2,
            ),
            _field(
              controller: _goalController,
              label: 'В чём его главная задача?',
              hint: 'Например: помогать планировать задачи и напоминать о дедлайнах',
              maxLines: 2,
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: TextFormField(
                controller: _restrictionsController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Что ему нельзя делать? (необязательно)',
                  hintText: 'Например: не давать медицинских советов',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            _field(
              controller: _greetingController,
              label: 'Приветствие',
              hint: 'Первое сообщение, которое увидит пользователь',
            ),
            if (_error != null) ...[
              Text(_error!, style: const TextStyle(color: Colors.red)),
              const SizedBox(height: 12),
            ],
            FilledButton(
              onPressed: _saving ? null : _submit,
              child: _saving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Создать агента'),
            ),
          ],
        ),
      ),
    );
  }
}
