import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../providers/profile_viewmodel.dart';
import '../../core/theme/app_colours.dart';

class EditProfileScreen extends StatefulWidget {
  final ProfileViewModel viewModel;

  const EditProfileScreen({super.key, required this.viewModel});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>(); // ✅ ADD THIS

  late TextEditingController _nameController;
  late TextEditingController _usernameController;
  late TextEditingController _timezoneController;
  bool _isUploading = false;
  bool _isDeletingPicture = false;

  @override
  void initState() {
    super.initState();
    final profile = widget.viewModel.profile;
    _nameController = TextEditingController(text: profile?.name ?? '');
    _usernameController = TextEditingController(text: profile?.username ?? '');
    _timezoneController = TextEditingController(
      text: profile?.timezone ?? 'Asia/Karachi',
    );
    widget.viewModel.addListener(_onProfileChanged);
  }

  @override
  void dispose() {
    widget.viewModel.removeListener(_onProfileChanged);
    _nameController.dispose();
    _usernameController.dispose();
    _timezoneController.dispose();
    super.dispose();
  }

  void _onProfileChanged() {
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final XFile? picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() => _isUploading = true);
      try {
        await widget.viewModel.uploadAvatar(picked);
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Upload failed: $e')));
      } finally {
        if (mounted) setState(() => _isUploading = false);
      }
    }
  }

  Future<void> _saveChanges() async {
    // ✅ Use the key to validate
    if (_formKey.currentState?.validate() ?? false) {
      try {
        await widget.viewModel.updateProfile(
          name: _nameController.text.trim(),
          username: _usernameController.text.trim().toLowerCase(),
          timezone: _timezoneController.text.trim(),
        );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Profile updated successfully')),
          );
          Navigator.pop(context);
        }
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Update failed: $e')));
      }
    }
  }

  Future<void> _removeProfilePicture() async {
    final confirm = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('Remove Profile Picture'),
        content: const Text(
          'Are you sure you want to remove your profile picture?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Remove', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isDeletingPicture = true);
    try {
      await widget.viewModel.deleteAvatar();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile picture removed successfully')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to remove: $e')));
      }
    } finally {
      if (mounted) setState(() => _isDeletingPicture = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = widget.viewModel.profile;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Profile'),
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey, // ✅ ADD THIS
          child: Column(
            children: [
              // ─── Avatar ──────────────────────────────────────────
              Stack(
                alignment: Alignment.bottomRight,
                children: [
                  CircleAvatar(
                    radius: 60,
                    backgroundImage: profile?.profilePicture != null
                        ? NetworkImage(profile!.profilePicture!)
                        : null,
                    child: profile?.profilePicture == null
                        ? Text(
                            profile?.initial ?? '?',
                            style: const TextStyle(fontSize: 40),
                          )
                        : null,
                  ),
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: IconButton(
                      icon: const Icon(
                        Icons.camera_alt,
                        color: Colors.white,
                        size: 20,
                      ),
                      onPressed: _pickImage,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints.tightFor(
                        width: 40,
                        height: 40,
                      ),
                    ),
                  ),
                  if (_isUploading)
                    Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.black54,
                      ),
                      child: const Center(child: CircularProgressIndicator()),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Tap camera icon to change photo',
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              ),
              if (profile?.profilePicture != null)
                TextButton(
                  onPressed: _isDeletingPicture ? null : _removeProfilePicture,
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                  child: _isDeletingPicture
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Remove Picture'),
                ),
              const SizedBox(height: 16),

              // ─── Email (read‑only) ─────────────────────────────
              TextFormField(
                initialValue: profile?.email ?? '',
                decoration: const InputDecoration(
                  labelText: 'Email',
                  prefixIcon: Icon(Icons.email),
                  border: OutlineInputBorder(),
                ),
                enabled: false,
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 16),

              // ─── Name ───────────────────────────────────────────
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: 'Full Name',
                  prefixIcon: Icon(Icons.person),
                  border: OutlineInputBorder(),
                ),
                validator: (v) =>
                    v == null || v.isEmpty ? 'Name is required' : null,
              ),
              const SizedBox(height: 16),

              // ─── Username ───────────────────────────────────────
              TextFormField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  labelText: 'Username',
                  prefixIcon: Icon(Icons.alternate_email),
                  border: OutlineInputBorder(),
                  helperText: '3-30 chars, letters only',
                ),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Username required';
                  if (v.length < 3 || v.length > 30) return '3-30 characters';
                  if (!RegExp(r'^[a-z]+$').hasMatch(v)) {
                    return 'Only lowercase letters allowed';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // ─── Timezone (read‑only) ──────────────────────────
              TextFormField(
                initialValue: profile?.timezone ?? '',
                decoration: const InputDecoration(
                  labelText: 'Timezone',
                  prefixIcon: Icon(Icons.access_time),
                  border: OutlineInputBorder(),
                ),
                enabled: false,
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 30),

              // ─── Save Button ────────────────────────────────────
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _saveChanges,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    textStyle: const TextStyle(fontSize: 16),
                  ),
                  child: const Text('Save Changes'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
