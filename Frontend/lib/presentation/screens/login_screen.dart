import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:validation_helper/validation_helper.dart';
import '../../core/theme/app_text_style.dart';
import '../../core/theme/app_colours.dart';
import '../providers/auth_viewmodel.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();

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
    final result = await auth.login(
      _emailController.text.trim(),
      _passwordController.text.trim(),
    );

    if (!mounted) return;

    if (result.success) {
      if (result.isVerified == false) {
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Email Not Verified'),
            content: const Text(
              'Please verify your email first. Check your inbox!',
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
      } else {
        context.go('/');
      }
    } else if (result.message.isNotEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(result.message)));
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
      key: _formKey,
      child: Column(
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
            validator: Validations.emailValidation,
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
            validator: (value) => Validations.strongPassword(value),
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
                onTap: () {},
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
                    if (_formKey.currentState!.validate()) {
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
      ),
    );
  }
}
