import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../core/utils/auth_validators.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../providers/auth_viewmodel.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _rememberMe = true;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _performLogin() async {
    final auth = context.read<AuthViewModel>();
    // Never trim the password: spaces are part of it.
    final result = await auth.login(
      _emailController.text.trim(),
      _passwordController.text,
      rememberMe: _rememberMe,
    );

    if (!mounted) return;

    if (result.success) {
      if (result.isVerified == false) {
        _showUnverifiedDialog();
      } else {
        context.go('/');
      }
    } else if (result.emailNotVerified) {
      // Correct password, but the account still needs verifying.
      _showUnverifiedDialog();
    } else if (result.errors.isEmpty && result.message.isNotEmpty) {
      // Field-level problems are shown under the inputs; everything else
      // (wrong credentials, deactivated account, no connection...) here.
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(result.message)));
    }
  }

  void _showUnverifiedDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Email Not Verified'),
        content: const Text(
          'Please verify your email first. Check your inbox (and spam folder) for the verification link.',
        ),
        actions: [
          TextButton(
            onPressed: () {
              context.go('/auth', extra: {'initialIndex': 0});
              Navigator.of(context).pop();
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showForgetPasswordDialog() {
    final dialogEmailController = TextEditingController();
    bool isSubmitting = false;
    String? dialogEmailError;

    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
              ),
              title: const Text('Reset Password'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Enter your email address and EVA will send you a link to reset your password.',
                    style: TextStyle(fontSize: 13, color: Colors.grey),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: dialogEmailController,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    onChanged: (_) {
                      if (dialogEmailError != null) {
                        setDialogState(() => dialogEmailError = null);
                      }
                    },
                    decoration: InputDecoration(
                      hintText: 'Email address',
                      errorText: dialogEmailError,
                      prefixIcon: const Icon(Icons.email_outlined),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSubmitting
                      ? null
                      : () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final email = dialogEmailController.text.trim();

                          final emailError = AuthValidators.email(email);
                          if (emailError != null) {
                            setDialogState(() => dialogEmailError = emailError);
                            return;
                          }
                          setDialogState(() => dialogEmailError = null);

                          setDialogState(() => isSubmitting = true);

                          final auth = context.read<AuthViewModel>();
                          final result = await auth.forgetPassword(email);

                          if (!mounted) return;

                          // Server rejected the address: keep the dialog open
                          // and show the message under the field.
                          if (!result.success && result.errors['email'] != null) {
                            setDialogState(() {
                              isSubmitting = false;
                              dialogEmailError = result.errors['email'];
                            });
                            return;
                          }

                          // Close dialog first
                          Navigator.pop(dialogContext);

                          // Then show result on the main screen
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                result.success
                                    ? 'If an account exists for $email, a reset link is on its way. Check your inbox and spam folder.'
                                    : result.message,
                              ),
                              backgroundColor: result.success
                                  ? Colors.green
                                  : Colors.red,
                              behavior: SnackBarBehavior.floating,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                          );
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Send'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Drop a server-side error as soon as the user edits the field again.
  void _clearServerErrors(AuthViewModel auth) {
    if (auth.emailError != null || auth.passwordError != null) {
      auth.clearErrors();
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

  Widget _label(String text, bool isDark) {
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
    final secondaryText = Theme.of(context).textTheme.bodySmall!.color!;
    final iconColor = secondaryText;

    return Form(
      child: Builder(
        builder: (context) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Email
              _label('Email Address', isDark),
              const SizedBox(height: 8),
              TextFormField(
                controller: _emailController,
                forceErrorText: auth.emailError,
                keyboardType: TextInputType.emailAddress,
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                decoration: _inputDecoration('Your email', isDark),
                autofillHints: const [AutofillHints.username, AutofillHints.email],
                onChanged: (_) => _clearServerErrors(auth),
                validator: AuthValidators.email,
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              const SizedBox(height: 16),

              // Password
              _label('Password', isDark),
              const SizedBox(height: 8),
              TextFormField(
                forceErrorText: auth.passwordError,
                controller: _passwordController,
                obscureText: _obscurePassword,
                style: AppTextStyles.body.copyWith(
                  fontSize: 14,
                  color: primaryText,
                ),
                decoration: _inputDecoration('Password', isDark).copyWith(
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
                autofillHints: const [AutofillHints.password],
                onChanged: (_) => _clearServerErrors(auth),
                // Login only requires a password to be typed; strength rules
                // apply when creating or resetting one.
                validator: AuthValidators.loginPassword,
                autovalidateMode: AutovalidateMode.onUnfocus,
              ),
              const SizedBox(height: 14),

              // Remember Me + Forgot Password
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: Checkbox(
                          value: _rememberMe,
                          onChanged: (val) =>
                              setState(() => _rememberMe = val ?? false),
                          activeColor: AppColors.primary,
                          checkColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(4),
                          ),
                          side: BorderSide(
                            color: isDark
                                ? AppColors.borderDark
                                : AppColors.borderLight,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Remember me',
                        style: AppTextStyles.subtitleSmall.copyWith(
                          fontSize: 13,
                          color: primaryText,
                        ),
                      ),
                    ],
                  ),
                  GestureDetector(
                    onTap: () {
                      _showForgetPasswordDialog();
                    },
                    child: Text(
                      'Forgot password?',
                      style: AppTextStyles.subtitleMedium.copyWith(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Sign In Button
              ElevatedButton(
                onPressed: auth.isLoading
                    ? null
                    : () {
                        if (Form.of(context).validate()) {
                          _performLogin();
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
                    : Text('Sign In', style: AppTextStyles.button),
              ),
            ],
          );
        },
      ),
    );
  }
}
