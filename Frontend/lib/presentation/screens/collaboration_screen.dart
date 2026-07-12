// collaboration_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colours.dart';
import '../../core/theme/app_text_style.dart';
import '../providers/friends_viewmodel.dart';
import '../providers/profile_viewmodel.dart';
import 'package:lottie/lottie.dart';
import '../../data/models/friend_model.dart';

class CollaborationScreen extends StatefulWidget {
  const CollaborationScreen({super.key});

  @override
  State<CollaborationScreen> createState() => _CollaborationScreenState();
}

class _CollaborationScreenState extends State<CollaborationScreen> {
  final TextEditingController _searchController = TextEditingController();
  Timer? _debounceTimer;
  String _searchText = '';

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchTextChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final friendsVm = context.read<FriendsViewModel>();
      friendsVm.loadFriends();
      friendsVm.loadPendingRequests(type: 'all');
    });
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

  // ─── Generic Avatar Builder ──────────────────────────────────────
  Widget _buildAvatar(
    String name,
    String? profilePicture, {
    double radius = 22,
  }) {
    final hasImage = profilePicture != null && profilePicture.isNotEmpty;
    return CircleAvatar(
      radius: radius,
      backgroundColor: AppColors.primary,
      child: hasImage
          ? ClipOval(
              child: Image.network(
                profilePicture,
                fit: BoxFit.cover,
                width: radius * 2,
                height: radius * 2,
                errorBuilder: (context, error, stackTrace) {
                  return Container(
                    color: AppColors.primary,
                    child: Center(
                      child: Text(
                        _getInitials(name),
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: radius * 0.8,
                        ),
                      ),
                    ),
                  );
                },
              ),
            )
          : Text(
              _getInitials(name),
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: radius * 0.8,
              ),
            ),
    );
  }

  // ─── Search ──────────────────────────────────────────────────────
  void _onSearchTextChanged() {
    final text = _searchController.text;
    setState(() => _searchText = text);
    _debounceTimer?.cancel();
    if (text.isEmpty) {
      context.read<FriendsViewModel>().searchUsers('');
      return;
    }
    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      if (!mounted) return;
      context.read<FriendsViewModel>().searchUsers(text.trim());
    });
  }

  // ─── Actions ──────────────────────────────────────────────────────
  void _addFriend(String username) async {
    try {
      await context.read<FriendsViewModel>().sendFriendRequest(
        username: username,
      );
      _showSnackbar('Friend request sent!', Colors.green);
      _searchController.clear();
    } catch (e) {
      _showSnackbar(e.toString(), Colors.red);
    }
  }

  void _unfriend(String friendshipId, String name) async {
    try {
      await context.read<FriendsViewModel>().unfriend(friendshipId);
      _showSnackbar('$name removed from friends.', Colors.orange);
    } catch (e) {
      _showSnackbar(e.toString(), Colors.red);
    }
  }

  void _acceptFriendRequest(String friendshipId, String name) async {
    try {
      await context.read<FriendsViewModel>().respondFriendRequest(
        friendshipId,
        'accept',
      );
      _showSnackbar('Accepted request from $name', Colors.green);
    } catch (e) {
      _showSnackbar(e.toString(), Colors.red);
    }
  }

  void _declineFriendRequest(String friendshipId, String name) async {
    try {
      await context.read<FriendsViewModel>().respondFriendRequest(
        friendshipId,
        'reject',
      );
      _showSnackbar('Declined request from $name', Colors.grey);
    } catch (e) {
      _showSnackbar(e.toString(), Colors.red);
    }
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

  // ─── Helper to extract friend from Friendship ──────────────────
  FriendUser _getFriend(Friendship friendship) {
    return friendship.friend ??
        (friendship.direction == 'outgoing'
            ? friendship.recipient
            : friendship.requester)!;
  }

  // ─── Show friend details ────────────────────────────────────────
  void _showFriendDetails(Friendship friendship) {
    final friend = _getFriend(friendship);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            _buildAvatar(friend.name, friend.profilePicture, radius: 30),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  friend.name,
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
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _unfriend(friendship.id, friend.name);
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

  // ─── Friend Requests Sheet ──────────────────────────────────────────
  void _showFriendRequests() {
    final vm = context.read<FriendsViewModel>();
    if (vm.pendingRequests.isEmpty) {
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
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, sheetSetState) {
          return DraggableScrollableSheet(
            initialChildSize: 0.5,
            minChildSize: 0.3,
            maxChildSize: 0.75,
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
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        'Friend Requests',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (vm.pendingRequests.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${vm.pendingRequests.length}',
                            style: const TextStyle(
                              color: AppColors.primary,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: vm.pendingRequests.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SizedBox(
                                  width: 180,
                                  height: 180,
                                  child: Lottie.asset(
                                    'assets/lottie/notification.json',
                                    fit: BoxFit.contain,
                                  ),
                                ),
                                Text(
                                  'No more pending requests',
                                  style: TextStyle(
                                    color: Theme.of(context).hintColor,
                                  ),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            controller: scrollController,
                            itemCount: vm.pendingRequests.length,
                            itemBuilder: (_, index) {
                              final request = vm.pendingRequests[index];
                              final user = _getFriend(request);
                              final isIncoming =
                                  request.direction == 'incoming';
                              return Card(
                                margin: const EdgeInsets.symmetric(vertical: 6),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: ListTile(
                                  leading: _buildAvatar(
                                    user.name,
                                    user.profilePicture,
                                    radius: 24,
                                  ),
                                  title: Text(
                                    user.name,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  subtitle: Text(
                                    isIncoming
                                        ? 'Wants to be friends'
                                        : 'Request sent',
                                    style: TextStyle(
                                      color: isIncoming
                                          ? Colors.green
                                          : Theme.of(context).hintColor,
                                      fontSize: 12,
                                    ),
                                  ),
                                  trailing: isIncoming
                                      ? Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            IconButton(
                                              icon: const Icon(
                                                Icons.check_circle,
                                                color: Colors.green,
                                              ),
                                              onPressed: () {
                                                _acceptFriendRequest(
                                                  request.id,
                                                  user.name,
                                                );
                                                sheetSetState(() {});
                                              },
                                            ),
                                            IconButton(
                                              icon: const Icon(
                                                Icons.cancel,
                                                color: Colors.red,
                                              ),
                                              onPressed: () {
                                                _declineFriendRequest(
                                                  request.id,
                                                  user.name,
                                                );
                                                sheetSetState(() {});
                                              },
                                            ),
                                          ],
                                        )
                                      : const Text(
                                          'Pending',
                                          style: TextStyle(color: Colors.grey),
                                        ),
                                ),
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ─── Build ─────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final friendsVm = context.watch<FriendsViewModel>();
    final profileVm = context.watch<ProfileViewModel>();
    final bgColor = Theme.of(context).scaffoldBackgroundColor;

    return Scaffold(
      body: Container(
        color: bgColor,
        child: SafeArea(
          child: SingleChildScrollView(
            // 👈 Make whole screen scrollable
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.only(bottom: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildHeader(),
                const SizedBox(height: 10),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _buildSearchBar(friendsVm),
                ),
                if (_searchText.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  ConstrainedBox(
                    constraints: BoxConstraints(maxHeight: 120),
                    child: _buildSearchResult(friendsVm),
                  ),
                ],
                const SizedBox(height: 16),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: IntrinsicHeight(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          flex: 3,
                          child: _buildUserProfileCard(profileVm),
                        ),
                        const SizedBox(width: 12),
                        Expanded(flex: 5, child: _buildQuoteCard(friendsVm)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                _buildFriendsList(friendsVm), // 👈 No longer Expanded
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Header ─────────────────────────────────────────────────────────
  Widget _buildHeader() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textColor = isDark
        ? AppColors.primaryTextDark
        : AppColors.primaryTextLight;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Friends & Collaboration',
            style: AppTextStyles.logo.copyWith(fontSize: 22, color: textColor),
          ),
          const SizedBox(height: 4),
          Text(
            'Stay connected and study together',
            style: TextStyle(
              fontSize: 12.5,
              color: Theme.of(context).hintColor,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Search bar ─────────────────────────────────────────────────────
  Widget _buildSearchBar(FriendsViewModel vm) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: TextField(
        controller: _searchController,
        inputFormatters: [
          FilteringTextInputFormatter.allow(RegExp(r'[a-zA-Z0-9]')),
        ],
        style: const TextStyle(fontSize: 14),
        decoration: InputDecoration(
          hintText: 'Search by username...',
          hintStyle: TextStyle(color: Theme.of(context).hintColor),
          prefixIcon: Icon(Icons.search, size: 20, color: AppColors.primary),
          suffixIcon: vm.isSearching
              ? const Padding(
                  padding: EdgeInsets.all(14.0),
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                )
              : (_searchText.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () => _searchController.clear(),
                      )
                    : null),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide.none,
          ),
          filled: true,
          fillColor: Theme.of(context).cardColor,
          contentPadding: const EdgeInsets.symmetric(
            vertical: 14,
            horizontal: 12,
          ),
        ),
      ),
    );
  }

  // ─── Search result ──────────────────────────────────────────────────
  Widget _buildSearchResult(FriendsViewModel vm) {
    if (vm.isSearching) return const SizedBox.shrink();

    final results = vm.searchResults;
    if (results.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.red.shade200),
          ),
          child: Row(
            children: [
              Icon(Icons.error_outline, color: Colors.red.shade300, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'No user found with that username.',
                  style: TextStyle(color: Colors.red.shade400, fontSize: 12.5),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final user = results.first;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            _buildAvatar(user.name, user.profilePicture, radius: 22),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user.name,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  Text(
                    '@${user.username}',
                    style: TextStyle(
                      color: Theme.of(context).hintColor,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            if (user.relationshipStatus == 'accepted')
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.check_circle,
                      size: 14,
                      color: Colors.green.shade700,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Friends',
                      style: TextStyle(
                        color: Colors.green.shade700,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              )
            else if (user.relationshipStatus == 'pending')
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  'Requested',
                  style: TextStyle(
                    color: Colors.orange.shade700,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              )
            else
              GestureDetector(
                onTap: () => _addFriend(user.username),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.3),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Text(
                    'Add Friend',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ─── User Profile Card ──────────────────────────────────────────────
  Widget _buildUserProfileCard(ProfileViewModel profileVm) {
    final profile = profileVm.profile;
    final name = profile?.name ?? 'User';
    final username = profile?.username ?? 'username';
    final avatarUrl = profile?.profilePicture;

    final avatar = CircleAvatar(
      radius: 28,
      backgroundColor: AppColors.primary,
      backgroundImage: avatarUrl != null && avatarUrl.isNotEmpty
          ? NetworkImage(avatarUrl)
          : null,
      child: avatarUrl == null || avatarUrl.isEmpty
          ? Text(
              _getInitials(name),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 20,
              ),
            )
          : null,
    );

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: avatar,
          ),
          const SizedBox(height: 10),
          Text(
            name,
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
          Text(
            '@$username',
            style: TextStyle(fontSize: 11, color: Theme.of(context).hintColor),
          ),
          const SizedBox(height: 8),
          Consumer<FriendsViewModel>(
            builder: (context, friendsVm, child) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${friendsVm.friends.length} friends',
                style: const TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w600,
                  color: AppColors.primary,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Quote Card ──────────────────────────────────────────────────────
  Widget _buildQuoteCard(FriendsViewModel vm) {
    final quote = vm.dailyQuote;
    final text = quote?.text ?? 'Loading quote...';
    final author = quote?.author ?? '';

    final snackBar = SnackBar(
      content: Text('Custom quote coming soon!'),
      backgroundColor: AppColors.hintDark,
    );

    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(snackBar);
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(18),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    Icons.format_quote_rounded,
                    size: 16,
                    color: Colors.orange.shade700,
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'Quote of the Day',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                ),
                const Spacer(),
                Icon(
                  Icons.edit_outlined,
                  size: 15,
                  color: Theme.of(context).hintColor,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              text,
              style: const TextStyle(
                fontSize: 13,
                fontStyle: FontStyle.italic,
                height: 1.45,
              ),
              maxLines: 5,
              overflow: TextOverflow.ellipsis,
            ),
            if (author.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '— $author',
                  style: TextStyle(
                    fontSize: 11,
                    color: Theme.of(context).hintColor,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ─── Friends List ────────────────────────────────────────────────────
  Widget _buildFriendsList(FriendsViewModel vm) {
    final hasFriends = vm.friends.isNotEmpty;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'My Friends',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: Theme.of(context).cardColor,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.04),
                          blurRadius: 6,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.notifications_outlined, size: 22),
                      onPressed: _showFriendRequests,
                      tooltip: 'Friend Requests',
                    ),
                  ),
                  if (vm.pendingRequests.isNotEmpty)
                    Positioned(
                      right: 4,
                      top: 4,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                          color: Colors.red,
                          shape: BoxShape.circle,
                        ),
                        constraints: const BoxConstraints(
                          minWidth: 17,
                          minHeight: 17,
                        ),
                        child: Text(
                          vm.pendingRequests.length.toString(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9.5,
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
          const SizedBox(height: 10),
          hasFriends
              ? ListView.separated(
                  shrinkWrap:
                      true, // 👈 Important: makes ListView size to its content
                  physics:
                      const NeverScrollableScrollPhysics(), // 👈 Prevents nested scrolling
                  itemCount: vm.friends.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, index) {
                    final friendship = vm.friends[index];
                    final friend = _getFriend(friendship);
                    return InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => _showFriendDetails(friendship),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(context).cardColor,
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.04),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          children: [
                            _buildAvatar(
                              friend.name,
                              friend.profilePicture,
                              radius: 22,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    friend.name,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '@${friend.username}',
                                    style: TextStyle(
                                      color: Theme.of(context).hintColor,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              icon: Icon(
                                Icons.more_vert,
                                color: Theme.of(context).hintColor,
                              ),
                              onPressed: () => _showFriendDetails(friendship),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                )
              : Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 180,
                        height: 180,
                        child: Lottie.asset(
                          'assets/lottie/nothing.json',
                          fit: BoxFit.contain,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'No friends yet',
                        style: TextStyle(
                          color: Theme.of(context).hintColor,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
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
        ],
      ),
    );
  }
}
