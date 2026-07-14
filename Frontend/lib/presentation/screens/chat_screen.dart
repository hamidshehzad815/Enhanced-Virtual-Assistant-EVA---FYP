import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'package:lottie/lottie.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../../data/models/chat_model.dart';
import '../providers/chat_viewmodel.dart';
import '../providers/profile_viewmodel.dart';
import '../providers/task_refresh_notifier.dart';

const _kSuggestions = [
  ' Add FYP meeting Friday 3pm',
  ' Make Python roadmap for 2 weeks',
  ' Remind me before NLP exam',
  ' Show my weekly progress',
];

class ChatBubbleShape extends StatelessWidget {
  final bool isUser;
  final Color color;
  final Widget child;
  final EdgeInsets padding;

  const ChatBubbleShape({
    super.key,
    required this.isUser,
    required this.color,
    required this.child,
    this.padding = const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _BubblePainter(isUser: isUser, color: color),
      child: Padding(
        // extra side padding to leave room for the tail notch
        padding: padding.add(
          EdgeInsets.only(right: isUser ? 6 : 0, left: isUser ? 0 : 6),
        ),
        child: child,
      ),
    );
  }
}

class _BubblePainter extends CustomPainter {
  final bool isUser;
  final Color color;
  _BubblePainter({required this.isUser, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    const radius = 18.0;
    const tailSize = 7.0;

    final path = Path();

    if (isUser) {
      // tail on bottom-right
      path.moveTo(radius, 0);
      path.lineTo(size.width - tailSize, 0);
      path.quadraticBezierTo(size.width, 0, size.width, tailSize);
      path.lineTo(size.width, size.height - radius);
      // little peak
      path.lineTo(size.width + tailSize, size.height);
      path.lineTo(size.width - 4, size.height - 2);
      path.quadraticBezierTo(
        size.width - radius,
        size.height,
        size.width - radius,
        size.height,
      );
      path.lineTo(radius, size.height);
      path.quadraticBezierTo(0, size.height, 0, size.height - radius);
      path.lineTo(0, radius);
      path.quadraticBezierTo(0, 0, radius, 0);
    } else {
      // tail on bottom-left
      path.moveTo(radius, 0);
      path.lineTo(size.width - radius, 0);
      path.quadraticBezierTo(size.width, 0, size.width, radius);
      path.lineTo(size.width, size.height - radius);
      path.quadraticBezierTo(
        size.width,
        size.height,
        size.width - radius,
        size.height,
      );
      path.lineTo(tailSize, size.height);
      path.lineTo(4, size.height - 2);
      path.lineTo(-tailSize, size.height);
      path.lineTo(0, size.height - radius);
      path.lineTo(0, radius);
      path.quadraticBezierTo(0, 0, radius, 0);
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _BubblePainter oldDelegate) =>
      oldDelegate.color != color || oldDelegate.isUser != isUser;
}

// ─── Typing Indicator ──────────────────────────────────────────────────
class TypingIndicator extends StatefulWidget {
  final bool isDark;
  const TypingIndicator({super.key, required this.isDark});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with TickerProviderStateMixin {
  late final List<AnimationController> _dotControllers;
  late final List<Animation<double>> _dotAnimations;

  @override
  void initState() {
    super.initState();
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

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _startAnimation();
    });
  }

  void _startAnimation() {
    for (int i = 0; i < 3; i++) {
      _dotControllers[i].forward().then((_) => _dotControllers[i].reverse());
    }
  }

  @override
  void dispose() {
    for (final c in _dotControllers) c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
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
}

// ─── Main Chat Screen ──────────────────────────────────────────────────
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  // ─── TTS ──────────────────────────────────────────────────────────────
  final FlutterTts _flutterTts = FlutterTts();
  bool _isTtsEnabled = false;

  // ─── Scroll ──────────────────────────────────────────────────────────
  final ScrollController _scrollController = ScrollController();
  bool _isEvaTyping = false;
  bool _messagesReady = false;
  // ─── Input ───────────────────────────────────────────────────────────
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _hasText = false;
  VoidCallback? _textListener;

  // ─── Speech-to-text ─────────────────────────────────────────────────
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechAvailable = false;
  bool _isListening = false;
  String _recognizedWords = '';

  // ─── Mic pulse animation ────────────────────────────────────────────
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  // ─────────────────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();

    _loadTtsPreference();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _pulseAnimation = Tween<double>(begin: 0.55, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _textListener = () {
      if (!mounted) return;
      final has = _textController.text.trim().isNotEmpty;
      if (has != _hasText) setState(() => _hasText = has);
    };
    _textController.addListener(_textListener!);

    _initSpeech();
    _setupTts();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final vm = context.read<ChatViewModel>();
      vm.loadSessions();
      if (vm.messages.isNotEmpty) {
        _scrollToBottom(animated: false);
      } else {
        setState(() => _messagesReady = true);
      }
    });
  }

  // ─── TTS methods ─────────────────────────────────────────────────────
  Future<void> _loadTtsPreference() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _isTtsEnabled = prefs.getBool('tts_enabled') ?? false);
  }

  Future<void> _saveTtsPreference(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('tts_enabled', value);
  }

  void _setupTts() async {
    await _flutterTts.setLanguage("en-US");
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setPitch(1.0);
  }

  Future<void> _speak(String text) async {
    if (!_isTtsEnabled || text.isEmpty) return;
    await _flutterTts.speak(text);
  }

  void _toggleTts() {
    setState(() => _isTtsEnabled = !_isTtsEnabled);
    _saveTtsPreference(_isTtsEnabled);
    if (_isTtsEnabled)
      _speak("Voice output enabled");
    else
      _flutterTts.stop();
  }

  // ─── Speech-to-text ─────────────────────────────────────────────────
  Future<void> _initSpeech() async {
    _speechAvailable = await _speech.initialize(
      onStatus: (status) {
        if (!mounted) return;
        if (status == 'done' || status == 'notListening') _stopListening();
      },
      onError: (_) => _stopListening(),
    );
    if (mounted) setState(() {});
  }

  void _startListening() async {
    if (!_speechAvailable || _isListening || !mounted) return;
    _focusNode.unfocus();

    await _speech.listen(
      onResult: (result) {
        if (!mounted) return;
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

    if (mounted) {
      setState(() => _isListening = true);
      _pulseController.repeat(reverse: true);
    }
  }

  void _stopListening() {
    _speech.stop();
    _pulseController.stop();
    _pulseController.reset();
    if (mounted) setState(() => _isListening = false);
  }

  void _toggleRecording() {
    if (_isListening)
      _stopListening();
    else
      _startListening();
  }

  @override
  void dispose() {
    if (_textListener != null) {
      _textController.removeListener(_textListener!);
      _textListener = null;
    }
    _speech.stop();
    _flutterTts.stop();
    _textController.dispose();
    _focusNode.dispose();
    _scrollController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  // ─── Messaging ──────────────────────────────────────────────────────
  Future<void> _sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    final vm = context.read<ChatViewModel>();
    final refreshNotifier = context.read<TaskRefreshNotifier>(); // <-- ADD
    _stopListening();
    _textController.clear();
    setState(() {
      _hasText = false;
      _isEvaTyping = true;
    });
    _scrollToBottom();

    try {
      final response = await vm.sendMessage(
        trimmed,
        sessionId: vm.currentSessionId,
        inputType: _isListening ? 'voice' : 'text',
      );
      if (response.responseText.isNotEmpty) _speak(response.responseText);
      vm.loadSessions();
      refreshNotifier.refresh();
    } catch (e) {
      /* ignore */
    } finally {
      if (!mounted) return;
      setState(() => _isEvaTyping = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom({bool animated = true}) {
    // Safety net: never let the screen stay hidden longer than this,
    // no matter how long extents take to settle (e.g. slow avatar images).
    Future.delayed(const Duration(milliseconds: 250), () {
      if (mounted && !_messagesReady && !animated) {
        setState(() => _messagesReady = true);
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _settleScroll(attempt: 0, animated: animated);
    });
  }

  void _settleScroll({
    required int attempt,
    required bool animated,
    double? lastMax,
  }) {
    if (!mounted || !_scrollController.hasClients) return;

    final max = _scrollController.position.maxScrollExtent;

    // Fewer retries + we now have the timeout above as a backstop,
    // so this only needs to try briefly.
    if (attempt < 3 && (lastMax == null || (max - lastMax).abs() > 0.5)) {
      _scrollController.jumpTo(max);
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _settleScroll(attempt: attempt + 1, animated: animated, lastMax: max);
      });
      return;
    }

    if (animated) {
      _scrollController.animateTo(
        max,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    } else {
      _scrollController.jumpTo(max);
      if (!_messagesReady) {
        setState(() => _messagesReady = true);
      }
    }
  }

  // ─── Drawer ──────────────────────────────────────────────────────────
  Widget _buildDrawer(ChatViewModel vm, bool isDark) {
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
                  vm.startNewChat();
                  Navigator.pop(context);
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
              child: vm.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : vm.sessions.isEmpty
                  ? Center(
                      child: Column(
                        children: [
                          SizedBox(
                            width: 180,
                            height: 180,
                            child: Lottie.asset(
                              'assets/lottie/chat.json',
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => Icon(
                                Icons.chat_bubble_outline_rounded,
                                size: 80,
                                color: secondary,
                              ),
                            ),
                          ),
                          Text(
                            'No conversations yet',
                            style: TextStyle(color: secondary),
                          ),
                        ],
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      itemCount: vm.sessions.length,
                      separatorBuilder: (_, __) => Divider(
                        color: border,
                        height: 1,
                        indent: 16,
                        endIndent: 16,
                      ),
                      itemBuilder: (_, i) {
                        final session = vm.sessions[i];
                        final isActive = session.id == vm.currentSessionId;
                        return InkWell(
                          onTap: () async {
                            Navigator.pop(context);
                            setState(() => _messagesReady = false);
                            await vm.loadMessages(session.id);
                            if (!mounted) return;
                            _scrollToBottom(animated: false);
                          },
                          child: Container(
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
                                    color: isActive
                                        ? AppColors.primary
                                        : secondary,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        session.title,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: AppTextStyles.subtitleSmall
                                            .copyWith(
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
                                        session.lastMessagePreview,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: AppTextStyles.subtitleSmall
                                            .copyWith(
                                              fontSize: 11,
                                              color: secondary,
                                            ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  _timeAgo(session.lastMessageAt),
                                  style: AppTextStyles.subtitleSmall.copyWith(
                                    fontSize: 10,
                                    color: secondary,
                                  ),
                                ),
                                IconButton(
                                  icon: Icon(
                                    Icons.delete_outline,
                                    size: 16,
                                    color: secondary,
                                  ),
                                  onPressed: () {
                                    showDialog(
                                      context: context,
                                      builder: (ctx) => AlertDialog(
                                        title: const Text(
                                          'Delete conversation?',
                                        ),
                                        content: const Text(
                                          'This cannot be undone.',
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.pop(ctx),
                                            child: const Text('Cancel'),
                                          ),
                                          TextButton(
                                            onPressed: () {
                                              vm.deleteSession(session.id);
                                              Navigator.pop(ctx);
                                            },
                                            child: const Text(
                                              'Delete',
                                              style: TextStyle(
                                                color: Colors.red,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
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

  String _timeAgo(DateTime? dt) {
    if (dt == null) return '';
    final diff = DateTime.now().difference(dt);
    if (diff.inDays > 0) return '${diff.inDays}d';
    if (diff.inHours > 0) return '${diff.inHours}h';
    if (diff.inMinutes > 0) return '${diff.inMinutes}m';
    return 'Just now';
  }

  // ─── Build ──────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final vm = context.watch<ChatViewModel>();
    final profileVm = context.watch<ProfileViewModel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final messages = vm.messages;

    // ─── User avatar data ─────────────────────────────────────────────
    final userInitial = _getUserInitial(profileVm);
    final userAvatar = _getUserAvatar(profileVm);

    return Scaffold(
      backgroundColor: isDark ? Colors.grey[900] : Colors.white,
      drawer: _buildDrawer(vm, isDark),
      appBar: _buildAppBar(vm, isDark),
      body: Column(
        children: [
          Expanded(
            child: messages.isEmpty
                ? _buildEmptyState(isDark)
                : _buildMessageList(vm, isDark, userInitial, userAvatar),
          ),
          _buildInputBar(vm, isDark),
        ],
      ),
    );
  }

  // ─── App Bar ──────────────────────────────────────────────────────────
  PreferredSizeWidget _buildAppBar(ChatViewModel vm, bool isDark) {
    final barBg = isDark ? AppColors.cardDark : Colors.transparent;
    final border = isDark ? AppColors.borderDark : const Color(0xFFE5E7EB);
    final primary = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    final secondary = isDark
        ? AppColors.secondaryTextDark
        : AppColors.secondaryTextLight;

    final title = vm.currentSessionId != null
        ? vm.sessions
              .firstWhere(
                (s) => s.id == vm.currentSessionId,
                orElse: () => SessionSummary(
                  id: '',
                  title: 'Chat',
                  lastMessagePreview: '',
                  createdAt: DateTime.now(),
                  updatedAt: DateTime.now(),
                ),
              )
              .title
        : 'New Chat';

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
                  onPressed: () => context.pop(),
                  icon: Icon(
                    Icons.arrow_back_ios_new_rounded,
                    size: 18,
                    color: primary,
                  ),
                ),
                // Avatar
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
                // TTS toggle
                IconButton(
                  onPressed: _toggleTts,
                  icon: Icon(
                    _isTtsEnabled
                        ? Icons.volume_up_rounded
                        : Icons.volume_off_rounded,
                    size: 22,
                    color: _isTtsEnabled ? AppColors.primary : secondary,
                  ),
                  tooltip: _isTtsEnabled
                      ? 'Disable voice output'
                      : 'Enable voice output',
                ),
                // History button
                Builder(
                  builder: (context) => IconButton(
                    onPressed: () => Scaffold.of(context).openDrawer(),
                    icon: Icon(
                      Icons.history_rounded,
                      size: 22,
                      color: secondary,
                    ),
                    tooltip: 'Chat history',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Empty State ──────────────────────────────────────────────────────
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
          SizedBox(
            width: 220,
            height: 220,
            child: Lottie.asset('assets/lottie/robo.json', fit: BoxFit.contain),
          ),
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

  // ─── Message List ─────────────────────────────────────────────────────
  Widget _buildMessageList(
    ChatViewModel vm,
    bool isDark,
    String userInitial,
    String? userAvatar,
  ) {
    final messages = vm.messages;
    final isSending = vm.isSending;

    return Stack(
      children: [
        // List is always built so the ScrollController attaches and
        // heights get measured — just hidden via opacity until ready.
        Opacity(
          opacity: _messagesReady ? 1 : 0,
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            itemCount: messages.length + (isSending ? 1 : 0),
            itemBuilder: (_, index) {
              if (isSending && index == messages.length) {
                return TypingIndicator(isDark: isDark);
              }

              final msg = messages[index];
              bool showTime = index == 0;
              if (index > 0) {
                final gap = msg.createdAt
                    .difference(messages[index - 1].createdAt)
                    .inMinutes;
                if (gap >= 10) showTime = true;
              }

              final isUser = msg.role == 'user';
              final bubbleColor = isUser
                  ? AppColors.primary
                  : (isDark
                        ? AppColors.cardElevatedDark
                        : const Color(0xFFF2EFE9));
              final textColor = isUser
                  ? Colors.white
                  : (isDark ? Colors.white : Colors.black87);

              final avatar = isUser
                  ? _buildUserAvatar(userInitial, userAvatar, radius: 18)
                  : _buildEvaAvatar(radius: 18);

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  children: [
                    if (showTime)
                      _buildTimestampDivider(
                        _formatTime(msg.createdAt),
                        isDark,
                      ),
                    Row(
                      mainAxisAlignment: isUser
                          ? MainAxisAlignment.end
                          : MainAxisAlignment.start,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (!isUser) avatar,
                        if (!isUser) const SizedBox(width: 8),
                        Flexible(
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 10,
                            ),
                            decoration: BoxDecoration(
                              color: bubbleColor,
                              borderRadius: isUser
                                  ? const BorderRadius.only(
                                      topLeft: Radius.circular(18),
                                      bottomLeft: Radius.circular(18),
                                      bottomRight: Radius.circular(18),
                                    )
                                  : const BorderRadius.only(
                                      topRight: Radius.circular(18),
                                      bottomLeft: Radius.circular(18),
                                      bottomRight: Radius.circular(18),
                                    ),
                            ),
                            child: Text(
                              msg.content,
                              style: TextStyle(color: textColor, fontSize: 14),
                            ),
                          ),
                        ),
                        if (isUser) const SizedBox(width: 8),
                        if (isUser) avatar,
                      ],
                    ),
                  ],
                ),
              );
            },
          ),
        ),
        if (!_messagesReady) const Center(child: CircularProgressIndicator()),
      ],
    );
  }

  // ─── Avatar builders ──────────────────────────────────────────────────
  Widget _buildUserAvatar(
    String initial,
    String? avatarUrl, {
    double radius = 18,
  }) {
    return CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary,
      backgroundImage: avatarUrl != null && avatarUrl.isNotEmpty
          ? NetworkImage(avatarUrl)
          : null,
      child: (avatarUrl == null || avatarUrl.isEmpty)
          ? Text(
              initial,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            )
          : null,
    );
  }

  Widget _buildEvaAvatar({double radius = 18}) {
    return CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary,
      child: const Text(
        'E',
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: 14,
          fontStyle: FontStyle.italic,
        ),
      ),
    );
  }

  // ─── Timestamp divider ───────────────────────────────────────────────
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

  String _formatTime(DateTime dt) => DateFormat('h:mm a').format(dt);

  // ─── Input Bar ────────────────────────────────────────────────────────
  Widget _buildInputBar(ChatViewModel vm, bool isDark) {
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
                  enabled: !vm.isSending,
                  textInputAction: TextInputAction.newline,
                  style: AppTextStyles.body.copyWith(
                    color: textCol,
                    fontSize: 14,
                    height: 1.4,
                  ),
                  decoration: InputDecoration(
                    hintText: _isListening
                        ? 'Listening...'
                        : vm.isSending
                        ? 'EVA is typing...'
                        : 'Ask EVA anything...',
                    hintStyle: AppTextStyles.subtitleSmall.copyWith(
                      color: _isListening ? AppColors.primary : hint,
                      fontSize: 14,
                    ),
                    border: InputBorder.none,
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

  // ─── Profile helpers ──────────────────────────────────────────────────
  String _getUserInitial(ProfileViewModel profileVm) {
    final profile = profileVm.profile;
    if (profile == null) return 'A';
    final name = profile.name ?? 'User';
    final parts = name.trim().split(' ');
    if (parts.length >= 2)
      return parts[0][0].toUpperCase() + parts[1][0].toUpperCase();
    return parts.isNotEmpty ? parts[0][0].toUpperCase() : '?';
  }

  String? _getUserAvatar(ProfileViewModel profileVm) {
    return profileVm.profile?.profilePicture;
  }
}
