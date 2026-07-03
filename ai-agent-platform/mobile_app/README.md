# Mobile app (Flutter)

Мобильное приложение для конструктора ИИ-агентов: регистрация/вход, анкетный
мастер создания агента и экран чата. Обращается к `ru-backend` (см.
`../ru-backend`) по HTTP.

## Запуск

```bash
flutter pub get

# Платформенные папки (android/, ios/) сгенерированы стандартным шаблоном
# Flutter и не хранятся в репозитории — создайте их один раз:
flutter create --platforms=android,ios .

flutter run
```

По умолчанию приложение обращается к `http://localhost:8000` — адрес backend
можно поменять на экране настроек (значок шестерёнки на экране входа), он
сохраняется на устройстве.

## Структура

```
lib/
  main.dart                 # точка входа, роутинг по статусу авторизации
  models/                   # Agent, ChatMessage
  services/
    api_client.dart         # HTTP-клиент ru-backend
    auth_state.dart         # хранение токена, base URL (shared_preferences)
  screens/
    login_screen.dart
    register_screen.dart
    settings_screen.dart    # адрес backend-сервера
    agents_list_screen.dart # список агентов пользователя
    agent_wizard_screen.dart# анкетный мастер создания агента
    chat_screen.dart        # переписка с агентом
```
