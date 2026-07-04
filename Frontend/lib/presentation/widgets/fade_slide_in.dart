import 'package:flutter/material.dart';

/// Reusable fade + slide-up entrance wrapper.
///
/// Toggle [visible] to `true` to reveal the child with a smooth fade-in
/// and upward slide. Used across onboarding-style screens (Features,
/// Get Started) so every staggered reveal shares the same feel.
///
/// Usage:
/// ```dart
/// FadeSlideIn(
///   visible: _logoVisible,
///   child: Text('EVA'),
/// )
/// ```
class FadeSlideIn extends StatelessWidget {
  final bool visible;
  final Widget child;
  final Duration duration;
  final double slideOffset;
  final Curve curve;

  const FadeSlideIn({
    super.key,
    required this.visible,
    required this.child,
    this.duration = const Duration(milliseconds: 450),
    this.slideOffset = 0.15,
    this.curve = Curves.easeOutCubic,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      duration: duration,
      curve: curve,
      opacity: visible ? 1.0 : 0.0,
      child: AnimatedSlide(
        duration: duration,
        curve: curve,
        offset: visible ? Offset.zero : Offset(0, slideOffset),
        child: child,
      ),
    );
  }
}
