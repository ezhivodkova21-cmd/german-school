class Agent {
  final int id;
  final String name;
  final String role;
  final String personality;
  final String goal;
  final String restrictions;
  final String greeting;
  final String modelProvider;

  Agent({
    required this.id,
    required this.name,
    required this.role,
    required this.personality,
    required this.goal,
    required this.restrictions,
    required this.greeting,
    required this.modelProvider,
  });

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      id: json['id'] as int,
      name: json['name'] as String,
      role: json['role'] as String,
      personality: json['personality'] as String,
      goal: json['goal'] as String,
      restrictions: (json['restrictions'] as String?) ?? '',
      greeting: (json['greeting'] as String?) ?? '',
      modelProvider: (json['model_provider'] as String?) ?? 'claude',
    );
  }
}
