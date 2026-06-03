// collaboration_screen.dart
import 'package:flutter/material.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/collaboration_conversation.dart';
import 'collaboration_data.dart';
import '../widgets/collaboration_widgets.dart';

class CollaborationScreen extends StatefulWidget {
  const CollaborationScreen({super.key});

  @override
  State<CollaborationScreen> createState() => _CollaborationScreenState();
}

class _CollaborationScreenState extends State<CollaborationScreen> {
  final TextEditingController _searchController = TextEditingController();
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  String _quoteOfDay =
      '"Study hard, for the well is deep and our brains are shallow."';
  late final List<ConversationModel> _conversations;

  @override
  void initState() {
    super.initState();
    _conversations = List.from(sampleConversations);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _onEditQuote() {
    final ctrl = TextEditingController(text: _quoteOfDay);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => EditQuoteSheet(
        controller: ctrl,
        onSave: (val) {
          setState(
            () => _quoteOfDay = val.trim().isEmpty ? _quoteOfDay : val.trim(),
          );
        },
      ),
    );
  }

  void _onConversationTap(ConversationModel conv) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Opening chat with ${conv.displayName}…')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      key: _scaffoldKey,
      drawer: const AppDrawer(),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeader(isDark),
            const SizedBox(height: 15),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  GestureDetector(
                    onTap: () => _scaffoldKey.currentState?.openDrawer(),
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: Theme.of(context).cardColor,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: Theme.of(context).dividerColor,
                        ),
                      ),
                      child: Icon(
                        Icons.menu_rounded,
                        size: 22,
                        color: Theme.of(context).hintColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: CollaborationSearchBar(
                      controller: _searchController,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ProfileQuoteRow(quote: _quoteOfDay, onEditQuote: _onEditQuote),
            Expanded(
              child: MessagesSection(
                conversations: _conversations,
                onConversationTap: _onConversationTap,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

Widget _buildHeader(bool isDark) {
  final primary = isDark
      ? AppColors.primaryTextDark
      : AppColors.primaryTextLight;

  return Padding(
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 4),
    child: Row(
      children: [
        Text(
          'Friends & Collaboration',
          style: AppTextStyles.logo.copyWith(fontSize: 26, color: primary),
        ),
      ],
    ),
  );
}
