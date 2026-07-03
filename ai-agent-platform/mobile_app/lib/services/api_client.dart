import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/agent.dart';
import '../models/message.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}

class ApiClient {
  final String baseUrl;
  final String? token;

  ApiClient({required this.baseUrl, this.token});

  Map<String, String> get _jsonHeaders => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Never _throwFromResponse(http.Response response) {
    String detail = response.body;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['detail'] != null) {
        detail = decoded['detail'].toString();
      }
    } catch (_) {
      // body wasn't JSON, keep raw text
    }
    throw ApiException(detail);
  }

  Future<String> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': email, 'password': password},
    );
    if (response.statusCode != 200) _throwFromResponse(response);
    return (jsonDecode(response.body) as Map<String, dynamic>)['access_token'] as String;
  }

  Future<void> register(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (response.statusCode != 201) _throwFromResponse(response);
  }

  Future<List<Agent>> listAgents() async {
    final response = await http.get(Uri.parse('$baseUrl/agents'), headers: _jsonHeaders);
    if (response.statusCode != 200) _throwFromResponse(response);
    final list = jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    return list.map((e) => Agent.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Agent> createAgent({
    required String name,
    required String role,
    required String personality,
    required String goal,
    required String restrictions,
    required String greeting,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/agents'),
      headers: _jsonHeaders,
      body: jsonEncode({
        'name': name,
        'role': role,
        'personality': personality,
        'goal': goal,
        'restrictions': restrictions,
        'greeting': greeting,
      }),
    );
    if (response.statusCode != 201) _throwFromResponse(response);
    return Agent.fromJson(jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>);
  }

  Future<void> deleteAgent(int agentId) async {
    final response = await http.delete(Uri.parse('$baseUrl/agents/$agentId'), headers: _jsonHeaders);
    if (response.statusCode != 204) _throwFromResponse(response);
  }

  Future<void> uploadKnowledge(int agentId, String title, String content) async {
    final response = await http.post(
      Uri.parse('$baseUrl/agents/$agentId/knowledge'),
      headers: _jsonHeaders,
      body: jsonEncode({'title': title, 'content': content}),
    );
    if (response.statusCode != 201) _throwFromResponse(response);
  }

  Future<List<ChatMessage>> getMessages(int agentId) async {
    final response = await http.get(Uri.parse('$baseUrl/agents/$agentId/messages'), headers: _jsonHeaders);
    if (response.statusCode != 200) _throwFromResponse(response);
    final list = jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    return list.map((e) => ChatMessage.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<String> sendChatMessage(int agentId, String message) async {
    final response = await http.post(
      Uri.parse('$baseUrl/agents/$agentId/chat'),
      headers: _jsonHeaders,
      body: jsonEncode({'message': message}),
    );
    if (response.statusCode != 200) _throwFromResponse(response);
    return (jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>)['reply'] as String;
  }
}
