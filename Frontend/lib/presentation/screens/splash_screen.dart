import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_colours.dart';
import '../../data/services/storage_service.dart';
import '../../data/services/api_client.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../data/services/push_notification_service.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  /// One-shot entrance: fade + scale "pop".
  late final AnimationController _entranceCtrl;
  late final Animation<double> _fade;
  late final Animation<double> _scale;

  /// Fast loop that drives the orb's breathing and the waveform bars.
  late final AnimationController _pulseCtrl;

  /// Slow loop that rotates the light sheen inside the orb.
  late final AnimationController _rotateCtrl;

  @override
  void initState() {
    super.initState();

    _entranceCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _fade = CurvedAnimation(parent: _entranceCtrl, curve: Curves.easeOut);
    _scale = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _entranceCtrl, curve: Curves.easeOutBack),
    );

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    )..repeat();

    _rotateCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 5000),
    )..repeat();

    _entranceCtrl.forward();

    _checkRoute();
  }

  @override
  void dispose() {
    _entranceCtrl.dispose();
    _pulseCtrl.dispose();
    _rotateCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkRoute() async {
    await Future.delayed(const Duration(seconds: 2));

    final prefs = await SharedPreferences.getInstance();
    final onboardingDone = prefs.getBool('onboarding_completed') ?? false;

    final token = await StorageService.getAccessToken();
    var hasValidSession = token != null;

    if (hasValidSession) {
      hasValidSession = await ApiClient.ensureValidSession();
      if (hasValidSession) {
        try {
          await PushNotificationService.init();
        } catch (_) {
          // Best effort; don't block splash navigation.
        }
      }
    }

    if (!mounted) return;

    if (!onboardingDone) {
      context.go('/welcome');
    } else if (!hasValidSession) {
      context.go('/auth', extra: {'initialIndex': 0});
    } else {
      context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: Center(
        child: AnimatedBuilder(
          animation: Listenable.merge([_entranceCtrl, _pulseCtrl, _rotateCtrl]),
          builder: (context, _) {
            return Opacity(
              opacity: _fade.value,
              child: Transform.scale(
                scale: _scale.value,
                child: SizedBox(
                  width: 280,
                  height: 280,
                  child: CustomPaint(
                    painter: _VoiceOrbPainter(
                      pulse: _pulseCtrl.value,
                      rotation: _rotateCtrl.value,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Paints a breathing amber orb with a rotating inner light sheen, ringed by a
/// circular audio waveform whose bars pulse like a listening voice assistant.
class _VoiceOrbPainter extends CustomPainter {
  _VoiceOrbPainter({required this.pulse, required this.rotation});

  /// 0..1 fast loop — breathing + waveform.
  final double pulse;

  /// 0..1 slow loop — sheen rotation.
  final double rotation;

  static const _baseRadius = 58.0;
  static const _barCount = 52;
  static const _barMinLen = 6.0;
  static const _barMaxLen = 30.0;

  // A brighter amber for the orb's highlight core / bar tips.
  static const _amberLight = Color(0xFFFCD34D);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    final breathe = math.sin(pulse * 2 * math.pi);
    final orbRadius = _baseRadius * (1 + 0.04 * breathe);

    _paintGlow(canvas, center, orbRadius, breathe);
    _paintWaveform(canvas, center, orbRadius);
    _paintOrb(canvas, center, orbRadius);
    _paintSheen(canvas, center, orbRadius);
  }

  /// Soft blurred halo behind everything.
  void _paintGlow(Canvas canvas, Offset center, double orbRadius, double b) {
    final glowPaint = Paint()
      ..color = AppColors.primary.withValues(alpha: 0.28 + 0.12 * b)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 30);
    canvas.drawCircle(center, orbRadius * 1.15, glowPaint);
  }

  /// Circular equalizer: bars radiating outward, each pulsing organically.
  void _paintWaveform(Canvas canvas, Offset center, double orbRadius) {
    final inner = orbRadius + 10;
    for (var i = 0; i < _barCount; i++) {
      final angle = 2 * math.pi * i / _barCount;

      // Blend two frequencies so neighbouring bars ripple naturally (0..1).
      final a = math.sin(pulse * 2 * math.pi * 2.0 + i * 0.55);
      final c = math.sin(pulse * 2 * math.pi * 1.3 - i * 0.30);
      final t = ((a + c) / 2 + 1) / 2;

      final len = _barMinLen + (_barMaxLen - _barMinLen) * t;
      final dir = Offset(math.cos(angle), math.sin(angle));
      final p1 = center + dir * inner;
      final p2 = center + dir * (inner + len);

      final barPaint = Paint()
        ..strokeCap = StrokeCap.round
        ..strokeWidth = 3.0
        ..color = Color.lerp(
          AppColors.primaryDark,
          _amberLight,
          t,
        )!.withValues(alpha: 0.55 + 0.4 * t);
      canvas.drawLine(p1, p2, barPaint);
    }
  }

  /// The orb: a radial amber gradient with a bright, off-centre core.
  void _paintOrb(Canvas canvas, Offset center, double orbRadius) {
    final rect = Rect.fromCircle(center: center, radius: orbRadius);
    final orbPaint = Paint()
      ..shader = const RadialGradient(
        center: Alignment(-0.3, -0.4),
        colors: [_amberLight, AppColors.primary, AppColors.primaryDark],
        stops: [0.0, 0.55, 1.0],
      ).createShader(rect);
    canvas.drawCircle(center, orbRadius, orbPaint);
  }

  /// A soft light streak that slowly sweeps around inside the orb.
  void _paintSheen(Canvas canvas, Offset center, double orbRadius) {
    final rect = Rect.fromCircle(center: center, radius: orbRadius);

    canvas.save();
    canvas.clipPath(Path()..addOval(rect));
    final sheenPaint = Paint()
      ..shader = SweepGradient(
        center: Alignment.center,
        colors: [
          Colors.white.withValues(alpha: 0.0),
          Colors.white.withValues(alpha: 0.0),
          Colors.white.withValues(alpha: 0.35),
          Colors.white.withValues(alpha: 0.0),
          Colors.white.withValues(alpha: 0.0),
        ],
        stops: const [0.0, 0.35, 0.5, 0.65, 1.0],
        transform: GradientRotation(rotation * 2 * math.pi),
      ).createShader(rect);
    canvas.drawCircle(center, orbRadius, sheenPaint);
    canvas.restore();

    // Crisp rim highlight.
    final rimPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5
      ..color = _amberLight.withValues(alpha: 0.5);
    canvas.drawCircle(center, orbRadius, rimPaint);
  }

  @override
  bool shouldRepaint(_VoiceOrbPainter oldDelegate) =>
      oldDelegate.pulse != pulse || oldDelegate.rotation != rotation;
}
