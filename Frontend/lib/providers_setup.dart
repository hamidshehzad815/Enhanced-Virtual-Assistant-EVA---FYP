import 'package:provider/provider.dart';
import 'data/repositories/home_screen_repository.dart';
import 'presentation/providers/home_screen_viewmodel.dart';

class AppProviders {
  static List<ChangeNotifierProvider> getProviders() {
    return [
      // ChangeNotifierProvider(
      //   create: (_) => ChatViewModel(repository: ChatRepository()),
      // ),
      ChangeNotifierProvider(
        create: (_) => HomeScreenViewModel(repository: HomeScreenRepository()),
      ),
    ];
  }
}
