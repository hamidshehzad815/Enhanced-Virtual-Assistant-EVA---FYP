import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/utils/auth_validators.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../../data/models/user_model.dart';
import '../providers/auth_viewmodel.dart';
import '../widgets/password_strength_meter.dart';
import 'package:lottie/lottie.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _nameController = TextEditingController();
  final _userNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _nameController.dispose();
    _userNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _performSignup() async {
    final auth = context.read<AuthViewModel>();
    final user = UserModel(
      name: _nameController.text.trim(),
      username: _userNameController.text.trim().toLowerCase(),
      email: _emailController.text.trim(),
      // Never trim the password: spaces are part of it.
      password: _passwordController.text,
    );

    final result = await auth.signup(user);
    if (!mounted) return;

    if (result.success) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          backgroundColor: Theme.of(context).brightness == Brightness.dark
              ? AppColors.cardDark
              : Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: Column(
            children: [
              SizedBox(
                height: 120,
                child: Lottie.asset(
                  'assets/lottie/email.json',
                  fit: BoxFit.contain,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Verify Your Email',
                style: AppTextStyles.headline.copyWith(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).textTheme.titleLarge?.color,
                ),
              ),
            ],
          ),
          content: Text(
            'A verification link has been sent to your email. Please verify to log in.',
            style: AppTextStyles.body.copyWith(
              fontSize: 14,
              color: Theme.of(context).textTheme.bodyMedium?.color,
            ),
            textAlign: TextAlign.center,
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context, rootNavigator: true).pop();

                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (!context.mounted) return;
                  context.go('/auth', extra: {'initialindex': 0});
                });
              },
              style: TextButton.styleFrom(
                foregroundColor: AppColors.primary,
                minimumSize: const Size(100, 40),
              ),
              child: Text(
                'OK',
                style: AppTextStyles.button.copyWith(color: AppColors.primary),
              ),
            ),
          ],
          actionsAlignment: MainAxisAlignment.center,
        ),
      );
    } else if (result.message.isNotEmpty) {
      // Field-level problems are already shown under their inputs.
      if (result.field == null && result.errors.isEmpty) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(result.message)));
      }
    }
  }

  InputDecoration _inputDecoration(String hint, bool isDark) {
    return InputDecoration(
      hintText: hint,
      hintStyle: AppTextStyles.subtitleSmall.copyWith(
        fontSize: 14,
        color: isDark ? AppColors.hintDark : AppColors.secondaryTextLight,
      ),
      filled: true,
      fillColor: isDark
          ? AppColors.inputFillDark
          : AppColors.scaffoldColorLight,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(
          color: isDark ? AppColors.borderDark : AppColors.borderLight,
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.red, width: 1),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.red, width: 1.5),
      ),
    );
  }

  /// Drop a server-side error as soon as the user edits a field again.
  void _clearServerErrors(AuthViewModel auth) {
    if (auth.nameError != null ||
        auth.userNameError != null ||
        auth.emailError != null ||
        auth.passwordError != null) {
      auth.clearErrors();
    }
  }

  Widget _label(String text) {
    return Text(
      text,
      style: AppTextStyles.subtitleMedium.copyWith(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: Theme.of(context).textTheme.bodyMedium!.color,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthViewModel>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final primaryText = Theme.of(context).textTheme.bodyMedium!.color!;
    final iconColor = Theme.of(context).textTheme.bodySmall!.color!;

    return Form(
      child: Builder(
        builder: (context) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Full Name
              _label('Full Name'),
              const SizedBox(height: 8),
              TextFormField(
                controller: _nameController,
                forceErrorText: auth.nameError,
                textCapitalization: TextCapitalization.words,
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                decoration: _inputDecoration('Enter your name', isDark),
                autofillHints: const [AutofillHints.name],
                onChanged: (_) => _clearServerErrors(auth),
                validator: AuthValidators.name,
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              const SizedBox(height: 16),
          
              //username instead of major
          
              // User Name
              _label('User Name'),
              const SizedBox(height: 8),
              TextFormField(
                controller: _userNameController,
                forceErrorText: auth.userNameError,
                textCapitalization: TextCapitalization.none,
                autocorrect: false,
                enableSuggestions: false,
                autofillHints: const [AutofillHints.newUsername],
                onChanged: (_) => _clearServerErrors(auth),
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                decoration: _inputDecoration('e.g. john_doe', isDark).copyWith(
                  helperText:
                      'Letters, numbers, periods and underscores. 3–30 characters.',
                  helperMaxLines: 2,
                ),
                validator: AuthValidators.username,
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              const SizedBox(height: 16),
              //username small , no char
          
              // Email
              _label('Email Address'),
              const SizedBox(height: 8),
              TextFormField(
                forceErrorText: auth.emailError,
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                decoration: _inputDecoration('Your email', isDark),
                autofillHints: const [AutofillHints.email],
                onChanged: (_) => _clearServerErrors(auth),
                validator: AuthValidators.email,
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              const SizedBox(height: 16),
          
              // Password
              _label('Password'),
              const SizedBox(height: 8),
              TextFormField(
                controller: _passwordController,
                forceErrorText: auth.passwordError,
                obscureText: _obscurePassword,
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                autofillHints: const [AutofillHints.newPassword],
                onChanged: (_) => _clearServerErrors(auth),
                decoration: _inputDecoration('At least 8 characters', isDark)
                    .copyWith(
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                          color: iconColor,
                          size: 20,
                        ),
                        onPressed: () =>
                            setState(() => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                validator: (value) => AuthValidators.password(
                  value,
                  email: _emailController.text,
                  username: _userNameController.text,
                ),
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              PasswordStrengthMeter(
                controller: _passwordController,
                emailController: _emailController,
                usernameController: _userNameController,
              ),
              const SizedBox(height: 24),
          
              // Create Account Button
              ElevatedButton(
                onPressed: auth.isLoading
                    ? null
                    : () {
                        if (Form.of(context).validate()) {
                          _performSignup();
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  elevation: 0,
                ),
                child: auth.isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(Colors.white),
                        ),
                      )
                    : Text('Create Account', style: AppTextStyles.button),
              ),
            ],
          );
        }
      ),
    );
  }
}
