import 'package:flutter/material.dart';
import '../../core/utils/auth_validators.dart';

/// Live feedback under a "new password" field: a strength bar plus a checklist
/// of the rules the server enforces. Rebuilds as any of the controllers change
/// (the optional email / username controllers feed the "must not contain your
/// email or username" rule).
class PasswordStrengthMeter extends StatelessWidget {
  final TextEditingController controller;
  final TextEditingController? emailController;
  final TextEditingController? usernameController;

  const PasswordStrengthMeter({
    super.key,
    required this.controller,
    this.emailController,
    this.usernameController,
  });

  @override
  Widget build(BuildContext context) {
    final secondary =
        Theme.of(context).textTheme.bodySmall?.color ?? Colors.grey;

    return ListenableBuilder(
      listenable: Listenable.merge([
        controller,
        if (emailController != null) emailController!,
        if (usernameController != null) usernameController!,
      ]),
      builder: (context, _) {
        final password = controller.text;
        if (password.isEmpty) return const SizedBox.shrink();

        final level = AuthValidators.passwordStrength(
          password,
          email: emailController?.text,
          username: usernameController?.text,
        );
        final color = level >= 3
            ? Colors.green
            : level == 2
                ? Colors.orange
                : Colors.red;
        final label = level >= 3
            ? 'Strong'
            : level == 2
                ? 'Good'
                : 'Weak';

        Widget rule(bool ok, String text) => Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Row(
                children: [
                  Icon(
                    ok ? Icons.check_circle : Icons.radio_button_unchecked,
                    size: 14,
                    color: ok ? Colors.green : secondary,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    text,
                    style: TextStyle(
                      fontSize: 12,
                      color: ok ? Colors.green : secondary,
                    ),
                  ),
                ],
              ),
            );

        return Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: level / 3,
                        minHeight: 4,
                        color: color,
                        backgroundColor: color.withValues(alpha: 0.15),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: color,
                    ),
                  ),
                ],
              ),
              rule(AuthValidators.hasValidLength(password), '8–64 characters'),
              rule(AuthValidators.hasLetter(password), 'At least one letter'),
              rule(
                AuthValidators.hasNumberOrSymbol(password),
                'At least one number or symbol',
              ),
            ],
          ),
        );
      },
    );
  }
}
