# EVA App - Refactored Architecture (Single Responsibility Principle)

## Overview
The app has been refactored to follow the **Single Responsibility Principle (SRP)** and **Clean Architecture** patterns. Each layer has a specific responsibility, making the code maintainable, testable, and ready for API integration.

## Architecture Layers

### 1. **Data Layer** (`lib/data/`)
Responsible for data access and management.

```
lib/data/
├── models/              # Data models with JSON serialization
│   ├── chat_message.dart
│   ├── task_data.dart
│   ├── focus_data.dart
│   ├── schedule_item.dart
│   └── user_profile.dart
├── repositories/        # Data access abstraction layer
│   ├── chat_repository.dart
│   └── home_screen_repository.dart
└── services/            # API communication layer
    └── chat_service.dart
```

#### Models
- **Purpose**: Define data structures with JSON serialization
- **Features**: 
  - `toJson()` - Convert to JSON for API requests
  - `fromJson()` - Create from API responses
  - `copyWith()` - Create modified copies (immutability)
- **Example**: `ChatMessage` stores message text, timestamp, and sender info

#### Repositories
- **Purpose**: Abstract data access from business logic
- **Pattern**: Repository pattern provides single point of data access
- **Benefits**: Easy to swap services (mock, API, database)
- **Example**: `ChatRepository` uses `ChatService` as data source

#### Services
- **Purpose**: Handle API communication and network requests
- **Current**: Mock data with TODO comments for API integration
- **Future**: Replace mock responses with actual HTTP calls

### 2. **Presentation Layer** (`lib/presentation/`)
Responsible for UI and state management.

```
lib/presentation/
├── providers/           # ViewModels/State Management
│   ├── chat_viewmodel.dart
│   └── home_screen_viewmodel.dart
├── screens/             # Full-screen widgets (UI only)
│   ├── chat_screen.dart
│   └── home_screen.dart
└── widgets/             # Reusable UI components
    ├── chat_bubble.dart (MessageBubble)
    └── message_input.dart
```

#### ViewModels (State Management)
- **Purpose**: Hold business logic and state
- **Framework**: `ChangeNotifier` + Provider
- **Responsibilities**:
  - Load data from repositories
  - Manage loading/error states
  - Notify UI of changes
  - Never know about UI details

#### Screens
- **Purpose**: Display UI only
- **Single Responsibility**: Render data from ViewModel
- **Pattern**: Use `Consumer<ViewModel>` to listen to state changes
- **No business logic**: All logic delegated to ViewModel

#### Widgets
- **Purpose**: Reusable UI components
- **Examples**: 
  - `MessageBubble` - Display single chat message
  - `MessageInput` - Handle message input UI

### 3. **Core Layer** (`lib/core/`)
Shared utilities and configurations.

```
lib/core/
├── theme/               # App theming
├── constants/           # App-wide constants
│   └── app_constants.dart
└── utils/               # Helper utilities
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ Presentation Layer (UI)                                 │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Screens (Display only)                           │   │
│ │  - ChatScreen, HomeScreen                        │   │
│ │  - Delegate to ViewModels                        │   │
│ └────────────┬─────────────────────────────────────┘   │
│              │ Uses & listens to                         │
│ ┌────────────▼─────────────────────────────────────┐   │
│ │ ViewModels (Business Logic)                      │   │
│ │  - ChatViewModel, HomeScreenViewModel            │   │
│ │  - Load data from repositories                   │   │
│ │  - Manage state (isLoading, error, data)         │   │
│ └────────────┬─────────────────────────────────────┘   │
│              │ Uses                                     │
│              │                                          │
│ ┌────────────▼─────────────────────────────────────┐   │
│ │ Widgets (Reusable UI Components)                 │   │
│ │  - MessageBubble, MessageInput                   │   │
│ │  - Pure UI, no logic                             │   │
│ └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Data Layer (Repositories & Services)                    │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Repositories                                     │   │
│ │  - ChatRepository, HomeScreenRepository          │   │
│ │  - Single access point for data                  │   │
│ └────────────┬─────────────────────────────────────┘   │
│              │ Uses                                     │
│ ┌────────────▼─────────────────────────────────────┐   │
│ │ Services                                         │   │
│ │  - ChatService, HomeScreenService                │   │
│ │  - Mock/API communication                        │   │
│ └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Core Layer (Utilities)                                  │
│ - Constants, Theme, Utils                              │
└─────────────────────────────────────────────────────────┘
```

## API Integration Guide

### How to Add API Calls

1. **Models**: Already have `toJson()` and `fromJson()` methods
   ```dart
   // Sending to API
   final json = message.toJson();
   await apiClient.post('/messages', data: json);
   
   // Receiving from API
   final response = await apiClient.get('/messages');
   final messages = response.map((m) => ChatMessage.fromJson(m)).toList();
   ```

2. **Services**: Replace mock data with API calls
   ```dart
   // Before (mock):
   return Future.value(List.from(_messages));
   
   // After (API):
   return await _apiClient.get('/chat/messages')
       .then((response) => (response as List)
           .map((m) => ChatMessage.fromJson(m))
           .toList());
   ```

3. **Add API Client Service**
   ```dart
   // Create lib/data/services/api_client.dart
   class ApiClient {
     final String baseUrl;
     
     Future<dynamic> get(String endpoint) async {
       final response = await http.get(Uri.parse('$baseUrl$endpoint'));
       if (response.statusCode == 200) {
         return jsonDecode(response.body);
       }
       throw Exception('API Error: ${response.statusCode}');
     }
     
     Future<dynamic> post(String endpoint, {required Map<String, dynamic> data}) async {
       final response = await http.post(
         Uri.parse('$baseUrl$endpoint'),
         headers: {'Content-Type': 'application/json'},
         body: jsonEncode(data),
       );
       if (response.statusCode == 200 || response.statusCode == 201) {
         return jsonDecode(response.body);
       }
       throw Exception('API Error: ${response.statusCode}');
     }
   }
   ```

4. **Inject API Client into Services**
   ```dart
   class ChatService {
     final ApiClient _apiClient;
     
     ChatService({required ApiClient apiClient}) 
         : _apiClient = apiClient;
     
     Future<List<ChatMessage>> fetchMessages() async {
       return await _apiClient.get('/chat/messages')
           .then((response) => (response as List)
               .map((m) => ChatMessage.fromJson(m))
               .toList());
     }
   }
   ```

5. **Update Providers Setup**
   ```dart
   // In providers_setup.dart
   final apiClient = ApiClient(baseUrl: 'https://api.example.com');
   
   ChangeNotifierProvider(
     create: (_) => ChatViewModel(
       repository: ChatRepository(
         service: ChatService(apiClient: apiClient)
       ),
     ),
   ),
   ```

## Benefits of This Architecture

✅ **Single Responsibility**: Each class has one reason to change
✅ **Testability**: Easy to mock services and repositories
✅ **Reusability**: ViewModels and widgets can be reused
✅ **Maintainability**: Clear separation of concerns
✅ **Scalability**: Easy to add new features without affecting existing code
✅ **API-Ready**: Models have JSON serialization, services ready for API calls
✅ **No Hardcoding**: All data comes from repositories/services

## Example: How ChatScreen Works

1. **ChatScreen** appears on screen
2. **initState()** calls `context.read<ChatViewModel>().loadMessages()`
3. **ChatViewModel**:
   - Calls `ChatRepository.getMessages()`
   - Repository calls `ChatService.fetchMessages()`
   - Service returns mock data (later: API data)
   - ViewModel sets state and notifies listeners
4. **ChatScreen** rebuilds using `Consumer<ChatViewModel>`
5. Displays `MessageBubble` for each message

All without hardcoding any data in the UI!

## File Organization Checklist

- [x] Models with JSON serialization (`data/models/`)
- [x] Repositories for data access (`data/repositories/`)
- [x] Services for API communication (`data/services/`)
- [x] ViewModels for state management (`presentation/providers/`)
- [x] Screens for UI only (`presentation/screens/`)
- [x] Reusable widgets (`presentation/widgets/`)
- [x] Constants centralized (`core/constants/`)
- [x] Provider setup (`providers_setup.dart`)

## Next Steps

1. Create `ApiClient` class for HTTP communication
2. Add your API endpoints to the services (replace TODOs)
3. Add error handling and retry logic
4. Consider using state management packages like Riverpod for more advanced features
5. Add unit tests for ViewModels and Repositories
6. Add integration tests for full flows

---

This architecture follows industry best practices and makes your app ready for production scaling!
