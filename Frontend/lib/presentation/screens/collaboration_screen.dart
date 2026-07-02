import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../widgets/collaboration_widgets.dart';

// ---------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------
class User {
  final String id;
  final String username;
  final String displayName;
  final String? avatarUrl;

  User({
    required this.id,
    required this.username,
    required this.displayName,
    this.avatarUrl,
  });
}

class FriendRequest {
  final String id;
  final User fromUser;
  final DateTime timestamp;

  FriendRequest({
    required this.id,
    required this.fromUser,
    required this.timestamp,
  });

  String get timeAgo {
    final diff = DateTime.now().difference(timestamp);
    if (diff.inDays > 0) return '${diff.inDays}d ago';
    if (diff.inHours > 0) return '${diff.inHours}h ago';
    if (diff.inMinutes > 0) return '${diff.inMinutes}m ago';
    return 'Just now';
  }
}

// ---------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------
class CollaborationScreen extends StatefulWidget {
  const CollaborationScreen({super.key});

  @override
  State<CollaborationScreen> createState() => _CollaborationScreenState();
}

class _CollaborationScreenState extends State<CollaborationScreen> {
  final TextEditingController _searchController = TextEditingController();

  // ─── Mock data ──────────────────────────────────────────────────────
  final User currentUser = User(
    id: 'me',
    username: 'johndoe',
    displayName: 'John Doe',
    avatarUrl: null,
  );

  String _quoteOfDay =
      '"Study hard, for the well is deep and our brains are shallow."';

  final List<User> _allUsers = [
    User(
      id: '1',
      username: 'alice',
      displayName: 'Alice Wonder',
      avatarUrl: 'https://i.pravatar.cc/150?img=1',
    ),
    User(
      id: '2',
      username: 'bob',
      displayName: 'Bob Builder',
      avatarUrl: 'https://i.pravatar.cc/150?img=2',
    ),
    User(
      id: '3',
      username: 'carol',
      displayName: 'Carol Danvers',
      avatarUrl: 'https://i.pravatar.cc/150?img=3',
    ),
    User(
      id: '4',
      username: 'dave',
      displayName: 'Dave Grohl',
      avatarUrl: 'https://i.pravatar.cc/150?img=4',
    ),
    User(
      id: '5',
      username: 'eve',
      displayName: 'Eve Online',
      avatarUrl: 'https://i.pravatar.cc/150?img=5',
    ),
  ];

  List<User> _friends = [];
  List<User> _blockedUsers = [];
  List<FriendRequest> _pendingRequests = [];

  // ─── Search state ──────────────────────────────────────────────────
  bool _isSearching = false;
  User? _searchResult;
  String _searchText = '';
  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    _friends = _allUsers.take(2).toList();
    _pendingRequests = [
      FriendRequest(
        id: 'req1',
        fromUser: _allUsers[2],
        timestamp: DateTime.now().subtract(const Duration(hours: 2)),
      ),
      FriendRequest(
        id: 'req2',
        fromUser: _allUsers[3],
        timestamp: DateTime.now().subtract(const Duration(minutes: 30)),
      ),
    ];
    _searchController.addListener(_onSearchTextChanged);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _searchController.removeListener(_onSearchTextChanged);
    _searchController.dispose();
    super.dispose();
  }

  // ─── Helpers ──────────────────────────────────────────────────────
  String _getInitials(String name) {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return parts[0][0].toUpperCase() + parts[1][0].toUpperCase();
    } else if (parts.isNotEmpty) {
      return parts[0][0].toUpperCase();
    }
    return '?';
  }

  bool _isFriend(User user) => _friends.contains(user);
  bool _isBlocked(User user) => _blockedUsers.contains(user);

  // ─── Avatar widget ─────────────────────────────────────────────────
  Widget _buildAvatar(User user, {double radius = 22}) {
    // If no avatar URL, show initials immediately.
    if (user.avatarUrl == null || user.avatarUrl!.isEmpty) {
      return CircleAvatar(
        radius: radius,
        backgroundColor: AppColors.primary.withOpacity(0.2),
        child: Text(
          _getInitials(user.displayName),
          style: TextStyle(
            fontSize: radius * 0.9,
            color: AppColors.primary,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
    }

    // If there is a URL, try to load the image with a fallback to initials.
    return CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary.withOpacity(0.2),
      child: ClipOval(
        child: Image.network(
          user.avatarUrl!,
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) {
            // When image fails, show initials instead.
            return Container(
              color: AppColors.primary.withOpacity(0.2),
              child: Center(
                child: Text(
                  _getInitials(user.displayName),
                  style: TextStyle(
                    fontSize: radius * 0.9,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  // ─── Search ──────────────────────────────────────────────────────
  void _onSearchTextChanged() {
    final text = _searchController.text;
    setState(() {
      _searchText = text;
    });
    _debounceTimer?.cancel();
    if (text.isEmpty) {
      setState(() {
        _searchResult = null;
        _isSearching = false;
      });
      return;
    }
    setState(() {
      _isSearching = true;
      _searchResult = null;
    });
    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      if (!mounted) return;
      _performSearch(text);
    });
  }

  void _performSearch(String query) {
    User? found;
    for (var user in _allUsers) {
      if (user.username.toLowerCase() == query.toLowerCase()) {
        found = user;
        break;
      }
    }
    setState(() {
      _isSearching = false;
      _searchResult = found;
    });
  }

  // ─── Actions ──────────────────────────────────────────────────────
  void _addFriend(User user) {
    setState(() {
      if (!_friends.contains(user)) _friends.add(user);
      _searchResult = null;
      _searchController.clear();
      _searchText = '';
    });
    _showSnackbar('${user.displayName} added as friend!', Colors.green);
  }

  void _removeFriend(User user) {
    setState(() => _friends.remove(user));
    _showSnackbar('${user.displayName} removed from friends.', Colors.orange);
  }

  void _blockFriend(User user) {
    setState(() {
      _friends.remove(user);
      if (!_blockedUsers.contains(user)) _blockedUsers.add(user);
    });
    _showSnackbar('${user.displayName} blocked.', Colors.red);
  }

  void _unblockFriend(User user) {
    setState(() => _blockedUsers.remove(user));
    _showSnackbar('${user.displayName} unblocked.', Colors.green);
  }

  void _acceptFriendRequest(FriendRequest request) {
    setState(() {
      _pendingRequests.remove(request);
      if (!_friends.contains(request.fromUser)) {
        _friends.add(request.fromUser);
      }
    });
    _showSnackbar(
      'Accepted request from ${request.fromUser.displayName}',
      Colors.green,
    );
  }

  void _declineFriendRequest(FriendRequest request) {
    setState(() => _pendingRequests.remove(request));
    _showSnackbar(
      'Declined request from ${request.fromUser.displayName}',
      Colors.grey,
    );
  }

  void _showSnackbar(String msg, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: color,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(12),
      ),
    );
  }

  // ─── Dialogs & Sheets ─────────────────────────────────────────────
  void _showFriendDetails(User friend) {
    final isBlocked = _isBlocked(friend);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            _buildAvatar(friend, radius: 30),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  friend.displayName,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(
                  '@${friend.username}',
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
              ],
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      Navigator.pop(ctx);
                      if (isBlocked)
                        _unblockFriend(friend);
                      else
                        _blockFriend(friend);
                    },
                    icon: Icon(isBlocked ? Icons.lock_open : Icons.block),
                    label: Text(isBlocked ? 'Unblock' : 'Block'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isBlocked ? Colors.green : Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _removeFriend(friend);
                    },
                    icon: const Icon(Icons.person_remove),
                    label: const Text('Remove'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.orange,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showFriendRequests() {
    if (_pendingRequests.isEmpty) {
      _showSnackbar('No pending friend requests.', Colors.grey);
      return;
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).cardColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.5,
        minChildSize: 0.3,
        maxChildSize: 0.7,
        expand: false,
        builder: (_, scrollController) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(
            children: [
              const SizedBox(height: 12),
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Friend Requests',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: ListView.builder(
                  controller: scrollController,
                  itemCount: _pendingRequests.length,
                  itemBuilder: (_, index) {
                    final request = _pendingRequests[index];
                    final user = request.fromUser;
                    return Card(
                      margin: const EdgeInsets.symmetric(vertical: 6),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: ListTile(
                        leading: _buildAvatar(user, radius: 24),
                        title: Text(
                          user.displayName,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        subtitle: Text(
                          '@${user.username} · ${request.timeAgo}',
                          style: const TextStyle(color: Colors.grey),
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(
                                Icons.check_circle,
                                color: Colors.green,
                              ),
                              onPressed: () {
                                Navigator.pop(ctx);
                                _acceptFriendRequest(request);
                              },
                            ),
                            IconButton(
                              icon: const Icon(Icons.cancel, color: Colors.red),
                              onPressed: () {
                                Navigator.pop(ctx);
                                _declineFriendRequest(request);
                              },
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
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
          setState(() {
            _quoteOfDay = val.trim().isEmpty ? _quoteOfDay : val.trim();
          });
        },
      ),
    );
  }

  // ─── Build ─────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final bgColor = Theme.of(context).scaffoldBackgroundColor;

    return Scaffold(
      drawer: const AppDrawer(),
      body: Container(
        color: bgColor,
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // ─── Header ────────────────────────────────────────────────
              _buildHeader(),
              const SizedBox(height: 8),

              // ─── Search row ────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Expanded(child: _buildSearchBar()),
              ),
              const SizedBox(height: 8),

              // ─── Search result ─────────────────────────────────────────
              if (_searchText.isNotEmpty) _buildSearchResult(),

              const SizedBox(height: 12),

              // ─── Profile + Quote ──────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(flex: 3, child: _buildUserProfileCard()),
                      const SizedBox(width: 12),
                      Expanded(flex: 5, child: _buildQuoteCard()),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // ─── Friends list ─────────────────────────────────────────
              Expanded(child: _buildFriendsList()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
      child: Text(
        'Friends & Collaboration',
        style: AppTextStyles.logo.copyWith(fontSize: 26, color: textColor),
      ),
    );
  }

  Widget _buildSearchBar() {
    return TextField(
      controller: _searchController,
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[a-z]'))],
      decoration: InputDecoration(
        hintText: 'Search by username...',
        prefixIcon: const Icon(Icons.search, size: 20),
        suffixIcon: _isSearching
            ? const Padding(
                padding: EdgeInsets.all(12.0),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              )
            : null,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        filled: true,
        fillColor: Theme.of(context).cardColor,
        contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 12),
      ),
    );
  }

  Widget _buildSearchResult() {
    if (_isSearching) return const SizedBox.shrink();

    final user = _searchResult;
    if (user != null) {
      final isFriend = _isFriend(user);
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Card(
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          child: ListTile(
            leading: _buildAvatar(user, radius: 24),
            title: Text(
              user.displayName,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              '@${user.username}',
              style: const TextStyle(color: Colors.grey),
            ),
            trailing: isFriend
                ? Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 18,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.green.shade100,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'Friends',
                      style: TextStyle(
                        color: Colors.green.shade800,
                        fontSize: 12,
                      ),
                    ),
                  )
                : ElevatedButton(
                    onPressed: () => _addFriend(user),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: const Text('Add Friend'),
                  ),
          ),
        ),
      );
    } else {
      // No user found
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.red.shade300),
          ),
          child: Row(
            children: [
              Icon(Icons.error_outline, color: Colors.red.shade300),
              const SizedBox(width: 8),
              Text(
                'No user found with that username.',
                style: TextStyle(color: Colors.red.shade300),
              ),
            ],
          ),
        ),
      );
    }
  }

  Widget _buildUserProfileCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildAvatar(currentUser, radius: 30),
          const SizedBox(height: 8),
          Text(
            currentUser.displayName,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            overflow: TextOverflow.ellipsis,
          ),
          Text(
            '@${currentUser.username}',
            style: const TextStyle(fontSize: 11, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _buildQuoteCard() {
    return GestureDetector(
      onTap: _onEditQuote,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Icon(
                  Icons.format_quote,
                  size: 18,
                  color: Colors.orange.shade700,
                ),
                const SizedBox(width: 4),
                Text(
                  'Quote of the Day',
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                const Spacer(),
                Icon(Icons.edit, size: 16, color: Theme.of(context).hintColor),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              _quoteOfDay,
              style: const TextStyle(
                fontSize: 13,
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFriendsList() {
    final hasFriends = _friends.isNotEmpty;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'My Friends',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Stack(
                children: [
                  IconButton(
                    icon: const Icon(Icons.notifications_outlined),
                    onPressed: _showFriendRequests,
                    tooltip: 'Friend Requests',
                  ),
                  if (_pendingRequests.isNotEmpty)
                    Positioned(
                      right: 6,
                      top: 6,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                          color: Colors.red,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(
                          minWidth: 18,
                          minHeight: 18,
                        ),
                        child: Text(
                          _pendingRequests.length.toString(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: hasFriends
                ? ListView.separated(
                    itemCount: _friends.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 6),
                    itemBuilder: (_, index) {
                      final friend = _friends[index];
                      return Card(
                        margin: EdgeInsets.zero,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: ListTile(
                          leading: _buildAvatar(friend, radius: 22),
                          title: Text(
                            friend.displayName,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          subtitle: Text(
                            '@${friend.username}',
                            style: const TextStyle(
                              color: Colors.grey,
                              fontSize: 12,
                            ),
                          ),
                          onTap: () => _showFriendDetails(friend),
                        ),
                      );
                    },
                  )
                : Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.people_outline,
                          size: 48,
                          color: Theme.of(context).hintColor,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'No friends yet',
                          style: TextStyle(
                            color: Theme.of(context).hintColor,
                            fontSize: 16,
                          ),
                        ),
                        Text(
                          'Search for friends above and add them!',
                          style: TextStyle(
                            color: Theme.of(context).hintColor,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
