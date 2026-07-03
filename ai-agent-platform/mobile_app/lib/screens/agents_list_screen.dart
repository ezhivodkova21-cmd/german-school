import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/agent.dart';
import '../services/api_client.dart';
import '../services/auth_state.dart';
import 'agent_wizard_screen.dart';
import 'chat_screen.dart';

class AgentsListScreen extends StatefulWidget {
  const AgentsListScreen({super.key});

  @override
  State<AgentsListScreen> createState() => _AgentsListScreenState();
}

class _AgentsListScreenState extends State<AgentsListScreen> {
  List<Agent> _agents = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final agents = await context.read<AuthState>().api.listAgents();
      setState(() => _agents = agents);
    } catch (e) {
      setState(() => _error = e is ApiException ? e.message : 'Не удалось загрузить агентов.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _deleteAgent(Agent agent) async {
    try {
      await context.read<AuthState>().api.deleteAgent(agent.id);
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'Не удалось удалить агента.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Мои агенты'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthState>().logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
                : _agents.isEmpty
                    ? ListView(
                        children: const [
                          Padding(
                            padding: EdgeInsets.all(32),
                            child: Text(
                              'У вас пока нет ни одного агента.\nНажмите "+", чтобы создать первого.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.grey),
                            ),
                          ),
                        ],
                      )
                    : ListView.builder(
                        itemCount: _agents.length,
                        itemBuilder: (context, index) {
                          final agent = _agents[index];
                          return ListTile(
                            leading: const CircleAvatar(child: Icon(Icons.smart_toy)),
                            title: Text(agent.name),
                            subtitle: Text(agent.role, maxLines: 1, overflow: TextOverflow.ellipsis),
                            onTap: () => Navigator.of(context).push(
                              MaterialPageRoute(builder: (_) => ChatScreen(agent: agent)),
                            ),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete_outline),
                              onPressed: () => _deleteAgent(agent),
                            ),
                          );
                        },
                      ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final created = await Navigator.of(context).push<bool>(
            MaterialPageRoute(builder: (_) => const AgentWizardScreen()),
          );
          if (created == true) _load();
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
