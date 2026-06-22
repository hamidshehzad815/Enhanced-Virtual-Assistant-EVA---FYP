import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import '../../core/theme/app_colours.dart';
import '../../router/app_router.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/conversation_model.dart';
import '../providers/chat_viewmodel.dart';
import '../widgets/demo_chat_bubble.dart';

// ── Placeholder data ──────────────────────────────────────────────────────────
final _kConversations = [
  ConversationModel(
    id: '1',
    title: 'NLP Exam Planning',
    lastMessage: 'Added exam for Monday 5pm',
    lastUpdated: DateTime.now().subtract(const Duration(minutes: 20)),
  ),
  ConversationModel(
    id: '2',
    title: 'Python Roadmap',
    lastMessage: 'Learning plan ready — 5 topics',
    lastUpdated: DateTime.now().subtract(const Duration(hours: 2)),
  ),
  ConversationModel(
    id: '3',
    title: 'Weekly Schedule',
    lastMessage: 'All classes added to calendar',
    lastUpdated: DateTime.now().subtract(const Duration(hours: 5)),
  ),
  ConversationModel(
    id: '4',
    title: 'Group Study Setup',
    lastMessage: 'Shared with 3 friends',
    lastUpdated: DateTime.now().subtract(const Duration(days: 1)),
  ),
  ConversationModel(
    id: '5',
    title: 'Physics Lab Prep',
    lastMessage: 'Reminder set for 12:45 PM',
    lastUpdated: DateTime.now().subtract(const Duration(days: 2)),
  ),
];

const _kSuggestions = [
  ' Add FYP meeting Friday 3pm',
  ' Make Python roadmap for 2 weeks',
  ' Remind me before NLP exam',
  ' Show my weekly progress',
];

// ═════════════════════════════════════════════════════════════════════════════
//  CHAT SCREEN
// ═════════════════════════════════════════════════════════════════════════════
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  // ── Message state ─────────────────────────────────────────────────────────
  final ScrollController _scrollController = ScrollController();
  bool _isEvaTyping = false;
  String? _activeConvoId;
  bool _disposed = false;
  bool _dotAnimationCancelled = false;

  // ── Input state ───────────────────────────────────────────────────────────
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _hasText = false;
  VoidCallback? _textListener; // stored to remove

  // ── Speech to text ────────────────────────────────────────────────────────
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechAvailable = false;
  bool _isListening = false;
  String _recognizedWords = '';

  // ── Mic pulse animation ───────────────────────────────────────────────────
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  // ── Typing indicator dot animations ──────────────────────────────────────
  late final List<AnimationController> _dotControllers;
  late final List<Animation<double>> _dotAnimations;

  // ─────────────────────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();

    // Mic pulse
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _pulseAnimation = Tween<double>(begin: 0.55, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Three-dot typing indicator
    _dotControllers = List.generate(
      3,
      (_) => AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 480),
      ),
    );
    _dotAnimations = _dotControllers
        .map(
          (c) => Tween<double>(
            begin: 0,
            end: -7,
          ).animate(CurvedAnimation(parent: c, curve: Curves.easeInOut)),
        )
        .toList();

    // ── Text field listener – stored and removed in dispose ──────────────
    _textListener = () {
      if (_disposed || !mounted) return;
      final has = _textController.text.trim().isNotEmpty;
      if (has != _hasText) setState(() => _hasText = has);
    };
    _textController.addListener(_textListener!);

    // Init speech
    _initSpeech();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_disposed || !mounted) return;
      context.read<ChatViewModel>().subscribeToMessages();
      context.read<ChatViewModel>().loadMessages();
    });
  }

  Future<void> _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onStatus: (status) {
        if (_disposed || !mounted) return;
        if (status == 'done' || status == 'notListening') {
          _stopListening();
        }
      },
      onError: (error) {
        if (_disposed || !mounted) return;
        _stopListening();
      },
    );
    if (!_disposed && mounted) setState(() {});
  }

  @override
  void dispose() {
    _disposed = true;
    _dotAnimationCancelled = true;

    // Remove text listener
    if (_textListener != null) {
      _textController.removeListener(_textListener!);
      _textListener = null;
    }

    _speech.stop();
    _textController.dispose();
    _focusNode.dispose();
    _scrollController.dispose();
    _pulseController.dispose();
    for (final c in _dotControllers) {
      c.dispose();
    }

    super.dispose();
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  SPEECH TO TEXT
  // ─────────────────────────────────────────────────────────────────────────
  void _startListening() async {
    if (!_speechAvailable || _isListening || _disposed || !mounted) return;
    _focusNode.unfocus();

    await _speech.listen(
      onResult: (result) {
        if (_disposed || !mounted) return;
        setState(() {
          _recognizedWords = result.recognizedWords;
          _textController.text = _recognizedWords;
          _textController.selection = TextSelection.fromPosition(
            TextPosition(offset: _textController.text.length),
          );
        });
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      localeId: 'en_US',
      cancelOnError: true,
      partialResults: true,
    );

    if (!_disposed && mounted) {
      setState(() => _isListening = true);
      _pulseController.repeat(reverse: true);
    }
  }

  void _stopListening() {
    _speech.stop();
    _pulseController.stop();
    _pulseController.reset();
    if (!_disposed && mounted) {
      setState(() => _isListening = false);
    }
  }

  void _toggleRecording() {
    if (_isListening) {
      _stopListening();
    } else {
      _startListening();
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  MESSAGING
  // ─────────────────────────────────────────────────────────────────────────
  void _sendMessage(String text) async {
    if (_disposed || !mounted) return;
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    _stopListening();
    _textController.clear();
    setState(() {
      _hasText = false;
      _isEvaTyping = true;
    });
    _scrollToBottom();
    _startDotAnimation();

    try {
      await context.read<ChatViewModel>().sendMessage(trimmed);
    } catch (e) {
      // ignore
    } finally {
      if (_disposed || !mounted) return;
      _stopDotAnimation();
      setState(() => _isEvaTyping = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom({bool animated = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_disposed || !mounted) return;
      if (!_scrollController.hasClients) return;
      final max = _scrollController.position.maxScrollExtent;
      animated
          ? _scrollController.animateTo(
              max,
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
            )
          : _scrollController.jumpTo(max);
    });
  }

  void _startDotAnimation() async {
    while (_isEvaTyping && !_disposed && !_dotAnimationCancelled && mounted) {
      for (int i = 0; i < 3; i++) {
        await Future.delayed(const Duration(milliseconds: 150));
        if (_disposed || _dotAnimationCancelled || !mounted || !_isEvaTyping)
          return;
        _dotControllers[i].forward().then((_) => _dotControllers[i].reverse());
      }
      await Future.delayed(const Duration(milliseconds: 350));
    }
  }

  void _stopDotAnimation() {
    _dotAnimationCancelled = true;
    for (final c in _dotControllers) {
      c.stop();
      c.reset();
    }
  }

  void _startNewChat() {
    if (_disposed || !mounted) return;
    final vm = context.read<ChatViewModel>();
    vm.clearMessages();
    vm.loadMessages();
    setState(() {
      _activeConvoId = null;
      _isEvaTyping = false;
    });
    _scrollToBottom(animated: false);
  }

  void _loadConversation(ConversationModel convo) {
    if (_disposed || !mounted) return;
    setState(() {
      _activeConvoId = convo.id;
    });
    context.read<ChatViewModel>().loadMessages();
    _scrollToBottom(animated: false);
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  BUILD
  // ─────────────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? Colors.grey[900] : Colors.white,
      drawer: _buildDrawer(isDark),
      appBar: _buildAppBar(isDark),
      body: Column(
        children: [
          Expanded(child: _buildMessageList(context, isDark)),
          _buildInputBar(isDark),
        ],
      ),
    );
  }

  // ── App Bar ────────────────────────────────────────────────────────────────
  PreferredSizeWidget _buildAppBar(bool isDark) {
    final barBg = isDark ? AppColors.cardDark : Colors.transparent;
    final border = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB);
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return PreferredSize(
      preferredSize: const Size.fromHeight(64),
      child: Container(
        decoration: BoxDecoration(
          color: barBg,
          border: Border(bottom: BorderSide(color: border)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.25 : 0.05),
              blurRadius: 12,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              children: [
                IconButton(
                  onPressed: () {
                    context.pop();
                  },
                  icon: Icon(
                    Icons.arrow_back_ios_new_rounded,
                    size: 18,
                    color: primary,
                  ),
                ),
                // EVA avatar
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.35),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text(
                      'E',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontStyle: FontStyle.italic,
                        fontSize: 16,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'EVA',
                        style: AppTextStyles.logo.copyWith(
                          fontSize: 16,
                          color: primary,
                        ),
                      ),
                      const SizedBox(height: 1),
                      Row(
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              color: Color(0xFF22C55E),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Online — ready to help',
                            style: TextStyle(
                              fontSize: 11,
                              color: const Color(0xFF22C55E),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                // ── HISTORY BUTTON – WRAPPED IN BUILDER ────────────────────
                Builder(
                  builder: (context) {
                    return IconButton(
                      onPressed: () {
                        final scaffold = Scaffold.maybeOf(context);
                        if (scaffold != null) {
                          scaffold.openDrawer();
                        } else {
                          // Fallback: maybe the drawer is not attached
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Drawer not available'),
                            ),
                          );
                        }
                      },
                      icon: Icon(
                        Icons.history_rounded,
                        size: 22,
                        color: secondary,
                      ),
                      tooltip: 'Chat history',
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Drawer ─────────────────────────────────────────────────────────────────
  Widget _buildDrawer(bool isDark) {
    final bg = isDark ? AppColors.cardDark : Colors.white;
    final border = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB);
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return Drawer(
      backgroundColor: bg,
      width: MediaQuery.of(context).size.width * 0.78,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topRight: Radius.circular(24),
          bottomRight: Radius.circular(24),
        ),
      ),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 8, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Conversations',
                    style: AppTextStyles.logo.copyWith(
                      fontSize: 18,
                      color: primary,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: Icon(Icons.close_rounded, color: secondary, size: 20),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: ElevatedButton.icon(
                onPressed: () {
                  context.go(AppRoutes.home);
                  _startNewChat();
                },
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('New Chat'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 44),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 0,
                ),
              ),
            ),
            const SizedBox(height: 14),
            Divider(color: border, height: 1),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(vertical: 8),
                itemCount: _kConversations.length,
                separatorBuilder: (_, __) => Divider(
                  color: border,
                  height: 1,
                  indent: 16,
                  endIndent: 16,
                ),
                itemBuilder: (_, i) {
                  final convo = _kConversations[i];
                  final isActive = convo.id == _activeConvoId;
                  return InkWell(
                    onTap: () {
                      context.go(AppRoutes.home);
                      _loadConversation(convo);
                    },
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: isActive
                            ? AppColors.primary.withOpacity(0.08)
                            : Colors.transparent,
                        border: isActive
                            ? const Border(
                                left: BorderSide(
                                  color: AppColors.primary,
                                  width: 3,
                                ),
                              )
                            : null,
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: isActive
                                  ? AppColors.primary.withOpacity(0.15)
                                  : (isDark
                                        ? AppColors.cardElevatedDark
                                        : const Color(0xFFF4F0E6)),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(
                              Icons.chat_bubble_outline_rounded,
                              size: 16,
                              color: isActive ? AppColors.primary : secondary,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  convo.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: AppTextStyles.subtitleSmall.copyWith(
                                    fontSize: 13,
                                    fontWeight: isActive
                                        ? FontWeight.w700
                                        : FontWeight.w500,
                                    color: isActive
                                        ? AppColors.primary
                                        : primary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  convo.lastMessage,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: AppTextStyles.subtitleSmall.copyWith(
                                    fontSize: 11,
                                    color: secondary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            convo.timeAgo,
                            style: AppTextStyles.subtitleSmall.copyWith(
                              fontSize: 10,
                              color: secondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            Divider(color: border, height: 1),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'EVA remembers your tasks\nacross all conversations.',
                style: AppTextStyles.subtitleSmall.copyWith(
                  color: secondary,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Message List ────────────────────────────────────────────────────────────
  Widget _buildMessageList(BuildContext context, bool isDark) {
    final vm = context.watch<ChatViewModel>();
    final messages = vm.messages;

    if (vm.isLoading && messages.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (messages.isEmpty) return _buildEmptyState(isDark);

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      itemCount: messages.length + (_isEvaTyping ? 1 : 0),
      itemBuilder: (_, index) {
        if (_isEvaTyping && index == messages.length) {
          return _buildTypingIndicator(isDark);
        }

        final msg = messages[index];
        bool showTime = index == 0;
        if (index > 0) {
          final gap = msg.timestamp
              .difference(messages[index - 1].timestamp)
              .inMinutes;
          if (gap >= 10) showTime = true;
        }

        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            children: [
              if (showTime) _buildTimestampDivider(msg.formattedTime, isDark),
              DemoChatBubble(
                text: msg.text,
                isEva: msg.isEva,
                userInitial: 'A',
              ),
            ],
          ),
        );
      },
    );
  }

  // ── Timestamp divider ─────────────────────────────────────────────────────
  Widget _buildTimestampDivider(String time, bool isDark) {
    final color = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(child: Divider(color: color.withOpacity(0.3), height: 1)),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Text(
              time,
              style: AppTextStyles.subtitleSmall.copyWith(
                fontSize: 10,
                color: color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(child: Divider(color: color.withOpacity(0.3), height: 1)),
        ],
      ),
    );
  }

  // ── Typing indicator ──────────────────────────────────────────────────────
  Widget _buildTypingIndicator(bool isDark) {
    final bubbleBg = isDark
        ? AppColors.cardElevatedDark
        : const Color(0xFFF2EFE9);
    final dotColor = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.primary,
            child: const Text(
              'E',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: bubbleBg,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(18),
                topRight: Radius.circular(18),
                bottomLeft: Radius.circular(4),
                bottomRight: Radius.circular(18),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                return AnimatedBuilder(
                  animation: _dotAnimations[i],
                  builder: (_, __) => Transform.translate(
                    offset: Offset(0, _dotAnimations[i].value),
                    child: Container(
                      width: 7,
                      height: 7,
                      margin: EdgeInsets.only(right: i < 2 ? 5 : 0),
                      decoration: BoxDecoration(
                        color: dotColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────
  Widget _buildEmptyState(bool isDark) {
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 48, 24, 24),
      child: Column(
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
              border: Border.all(
                color: AppColors.primary.withOpacity(0.3),
                width: 2,
              ),
            ),
            child: const Center(
              child: Text(
                'E',
                style: TextStyle(
                  color: AppColors.primary,
                  fontSize: 30,
                  fontWeight: FontWeight.bold,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'How can I help you today?',
            style: AppTextStyles.headline.copyWith(
              fontSize: 22,
              color: primary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'Type a command or try one of these:',
            style: AppTextStyles.subtitleSmall.copyWith(color: secondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 28),
          ..._kSuggestions.map((s) => _buildSuggestionChip(s, isDark)),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(String text, bool isDark) {
    final bg = isDark ? AppColors.cardElevatedDark : Colors.white;
    final border = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB);
    final color = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final prompt = text.substring(text.indexOf('  ') + 2).trim();

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: GestureDetector(
        onTap: () {
          _textController.text = prompt;
          _textController.selection = TextSelection.fromPosition(
            TextPosition(offset: prompt.length),
          );
          setState(() => _hasText = true);
          _focusNode.requestFocus();
        },
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: border),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Text(
            text,
            style: AppTextStyles.subtitleSmall.copyWith(
              fontSize: 13,
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }

  // ── Input bar ──────────────────────────────────────────────────────────────
  Widget _buildInputBar(bool isDark) {
    final border = isDark
        ? AppColors.borderDark
        : const Color.fromARGB(255, 158, 161, 167);
    final fieldBg = isDark
        ? AppColors.inputFillDark
        : const Color.fromARGB(255, 241, 237, 224);
    final hint = isDark ? AppColors.hintDark : AppColors.secondaryTextLight;
    final textCol = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(color: Colors.transparent),
      child: SafeArea(
        top: false,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                constraints: const BoxConstraints(maxHeight: 120),
                decoration: BoxDecoration(
                  color: fieldBg,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: border),
                ),
                child: TextField(
                  controller: _textController,
                  focusNode: _focusNode,
                  maxLines: null,
                  enabled: !_isEvaTyping,
                  textInputAction: TextInputAction.newline,
                  style: AppTextStyles.body.copyWith(
                    color: textCol,
                    fontSize: 14,
                    height: 1.4,
                  ),
                  decoration: InputDecoration(
                    hintText: _isListening
                        ? 'Listening...'
                        : _isEvaTyping
                        ? 'EVA is typing...'
                        : 'Ask EVA anything...',
                    hintStyle: AppTextStyles.subtitleSmall.copyWith(
                      color: _isListening ? AppColors.primary : hint,
                      fontSize: 14,
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    filled: false,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 10,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              transitionBuilder: (child, anim) =>
                  ScaleTransition(scale: anim, child: child),
              child: _hasText
                  ? GestureDetector(
                      key: const ValueKey('send'),
                      onTap: () => _sendMessage(_textController.text),
                      child: _buildActionButton(
                        icon: Icons.send_rounded,
                        color: AppColors.primary,
                      ),
                    )
                  : _isListening
                  ? AnimatedBuilder(
                      animation: _pulseAnimation,
                      builder: (_, __) => GestureDetector(
                        key: const ValueKey('mic_recording'),
                        onTap: _toggleRecording,
                        child: _buildActionButton(
                          icon: Icons.mic_rounded,
                          color: AppColors.primary.withOpacity(
                            _pulseAnimation.value,
                          ),
                          iconColor: Colors.white.withOpacity(
                            _pulseAnimation.value,
                          ),
                        ),
                      ),
                    )
                  : GestureDetector(
                      key: const ValueKey('mic_idle'),
                      onTap: _speechAvailable ? _toggleRecording : null,
                      child: _buildActionButton(
                        icon: Icons.mic_rounded,
                        color: _speechAvailable
                            ? AppColors.primary
                            : (isDark
                                  ? AppColors.borderDark
                                  : const Color(0xFFD1D5DB)),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required Color color,
    Color iconColor = Colors.white,
  }) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Icon(icon, color: iconColor, size: 20),
    );
  }
}
