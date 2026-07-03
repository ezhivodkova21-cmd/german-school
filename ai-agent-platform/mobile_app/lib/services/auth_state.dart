import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

const _defaultBaseUrl = 'http://localhost:8000';
const _tokenKey = 'auth_token';
const _baseUrlKey = 'base_url';

class AuthState extends ChangeNotifier {
  String? _token;
  String _baseUrl = _defaultBaseUrl;
  bool _loaded = false;

  String? get token => _token;
  String get baseUrl => _baseUrl;
  bool get isLoggedIn => _token != null;
  bool get loaded => _loaded;

  ApiClient get api => ApiClient(baseUrl: _baseUrl, token: _token);

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    _baseUrl = prefs.getString(_baseUrlKey) ?? _defaultBaseUrl;
    _loaded = true;
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, url);
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final token = await ApiClient(baseUrl: _baseUrl).login(email, password);
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    notifyListeners();
  }

  Future<void> register(String email, String password) async {
    await ApiClient(baseUrl: _baseUrl).register(email, password);
  }

  Future<void> logout() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    notifyListeners();
  }
}
