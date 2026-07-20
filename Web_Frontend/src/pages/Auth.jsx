import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import apiRequest from '../services/api';
import { Player } from '@lottiefiles/react-lottie-player';
import { Eye, EyeOff, Loader2, Mail, ArrowLeft, RefreshCw, ShieldCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

// ─────────────────────────────────────────────
// Screen constants
// ─────────────────────────────────────────────
const SCREEN = {
  LOGIN: 'login',
  SIGNUP: 'signup',
  FORGOT_EMAIL: 'forgot_email',  // Step 1: enter email
  FORGOT_SENT: 'forgot_sent',    // Step 2: "check your email" (reset link sent)
  VERIFY_EMAIL: 'verify_email',  // Post-signup: email verification pending
};

export const Auth = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, signup, errors: apiErrors, forgotPassword, resetPassword, verifyEmailApi } = useAuth();

  // ── Screen / navigation ──────────────────────
  const [screen, setScreen] = useState(SCREEN.LOGIN);

  useEffect(() => {
    if (location.state?.initialIndex === 1) setScreen(SCREEN.SIGNUP);
  }, [location.state]);

  // ── Login form ───────────────────────────────
  const [loginEmail, setLoginEmail]       = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPw, setShowLoginPw]     = useState(false);
  const [rememberMe, setRememberMe]       = useState(true);

  // ── Signup form ──────────────────────────────
  const [signupName, setSignupName]       = useState('');
  const [signupUsername, setSignupUsername] = useState('');
  const [signupEmail, setSignupEmail]     = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [showSignupPw, setShowSignupPw]   = useState(false);

  // ── Forgot password ─────────────────────────
  const [forgotEmail, setForgotEmail]     = useState('');

  // ── Verification (post-signup) ───────────────
  const [verifyToken, setVerifyToken]     = useState('');
  const [resendTimer, setResendTimer]     = useState(0);
  const timerRef = useRef(null);

  // ── Shared UI state ──────────────────────────
  const [isLoading, setIsLoading]         = useState(false);
  const [fieldErrors, setFieldErrors]     = useState({});
  const [alertMsg, setAlertMsg]           = useState({ type: '', text: '' });
  const googleLoginButtonRef = useRef(null);
  const googleSignupButtonRef = useRef(null);

  // ── Helpers ──────────────────────────────────
  const clearAll = () => { setFieldErrors({}); setAlertMsg({ type: '', text: '' }); };

  const go = (s) => { clearAll(); setScreen(s); };

  const validateEmail = (e) => /\S+@\S+\.\S+/.test(e);
  const validateUsername = (value) => /^[a-z]+$/.test(value) && value.length >= 3 && value.length <= 30;

  // Resend timer countdown
  const startResendTimer = () => {
    setResendTimer(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setResendTimer(prev => {
        if (prev <= 1) { clearInterval(timerRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setIsLoading(true);
      clearAll();
      const token = credentialResponse?.credential;
      if (!token) {
        setAlertMsg({ type: 'error', text: 'Google sign-in was cancelled.' });
        setIsLoading(false);
        return;
      }

      const response = await apiRequest('/api/auth/google', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({
          id_token: token,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Karachi',
        }),
      });

      if (response.status === 'success' || response.success) {
        const tokens = response.data?.tokens;
        if (tokens) {
          localStorage.setItem('access_token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
        }
        navigate('/');
      } else {
        setAlertMsg({ type: 'error', text: response.message || 'Google sign-in failed.' });
      }
    } catch (err) {
      setAlertMsg({ type: 'error', text: err.message || 'Google sign-in failed.' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '654038676954-3up0qv4j6f8d2mtes31ktp0sp2q6h9cu.apps.googleusercontent.com';
    const initializeGoogleButtons = () => {
      if (!window.google?.accounts?.id) return;

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleSuccess,
        auto_select: false,
        ux_mode: 'popup',
        context: 'signin',
      });

      if (googleLoginButtonRef.current) {
        googleLoginButtonRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(googleLoginButtonRef.current, {
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'continue_with',
          shape: 'rectangular',
        });
      }

      if (googleSignupButtonRef.current) {
        googleSignupButtonRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(googleSignupButtonRef.current, {
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'continue_with',
          shape: 'rectangular',
        });
      }
    };

    if (!window.google?.accounts?.id) {
      const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
      if (existingScript) {
        existingScript.addEventListener('load', initializeGoogleButtons);
        return () => existingScript.removeEventListener('load', initializeGoogleButtons);
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleButtons;
      document.body.appendChild(script);
      return () => {
        document.body.removeChild(script);
      };
    }

    initializeGoogleButtons();
  }, [screen]);

  // ────────────────────────────────────────────────────
  // Handlers
  // ────────────────────────────────────────────────────

  // LOGIN
  const handleLogin = async (e) => {
    e.preventDefault();
    clearAll();
    const errs = {};
    if (!loginEmail) errs.loginEmail = 'Email is required';
    else if (!validateEmail(loginEmail)) errs.loginEmail = 'Enter a valid email';
    if (!loginPassword) errs.loginPassword = 'Password is required';
    else if (loginPassword.length < 6) errs.loginPassword = 'Min 6 characters';
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }

    setIsLoading(true);
    const result = await login(loginEmail, loginPassword);
    setIsLoading(false);

    if (result.success) {
      if (result.isVerified === false) {
        // Email not verified — push to verification screen
        setSignupEmail(loginEmail);
        startResendTimer();
        go(SCREEN.VERIFY_EMAIL);
      } else {
        navigate('/');
      }
    } else {
      setAlertMsg({ type: 'error', text: result.message || 'Invalid credentials' });
    }
  };

  // SIGNUP
  const handleSignup = async (e) => {
    e.preventDefault();
    clearAll();

    const errs = {};
    if (!signupName.trim()) errs.signupName = 'Full name is required';
    if (!signupUsername.trim()) {
      errs.signupUsername = 'Username is required';
    } else if (!validateUsername(signupUsername.trim())) {
      errs.signupUsername = 'Username must be 3-30 lowercase letters only';
    }
    if (!signupEmail.trim()) {
      errs.signupEmail = 'Email is required';
    } else if (!validateEmail(signupEmail.trim())) {
      errs.signupEmail = 'Enter a valid email';
    }
    if (!signupPassword) {
      errs.signupPassword = 'Password is required';
    } else if (signupPassword.length < 6) {
      errs.signupPassword = 'Password must be at least 6 characters';
    }
    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    let result;
    try {
      const normalizedUsername = String(signupUsername || '').trim().toLowerCase();
      const normalizedEmail = String(signupEmail || '').trim().toLowerCase();
      const normalizedName = String(signupName || '').trim();

      result = await signup({
        name: normalizedName,
        username: normalizedUsername,
        email: normalizedEmail,
        password: signupPassword,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Karachi',
      });
    } catch {
      setIsLoading(false);
      setAlertMsg({ type: 'error', text: 'Network error — please check your connection.' });
      return;
    }

    setIsLoading(false);

    if (result && result.success) {
      startResendTimer();
      setScreen(SCREEN.VERIFY_EMAIL);
    } else {
      setAlertMsg({ type: 'error', text: result?.message || 'Signup failed. Please try again.' });
    }
  };

  // VERIFY EMAIL (post-signup / post-login for unverified)
  const handleVerify = async (e) => {
    e.preventDefault();
    clearAll();
    if (!verifyToken.trim()) { setFieldErrors({ verifyToken: 'Please paste the token or full link from your email' }); return; }

    setIsLoading(true);
    let tokenVal = verifyToken.trim();
    if (tokenVal.includes('token=')) {
      const match = tokenVal.match(/token=([^&]+)/);
      if (match) tokenVal = match[1];
    }
    const result = await verifyEmailApi(tokenVal);
    setIsLoading(false);

    if (result.success) {
      setAlertMsg({ type: 'success', text: 'Email verified! Redirecting to login…' });
      setTimeout(() => {
        setLoginEmail(signupEmail || '');
        go(SCREEN.LOGIN);
        setVerifyToken('');
      }, 2000);
    } else {
      setAlertMsg({ type: 'error', text: result.message || 'Invalid or expired token' });
    }
  };

  // RESEND verification email — calls real backend endpoint
  const handleResend = async () => {
    if (resendTimer > 0 || !signupEmail) return;
    setAlertMsg({ type: 'info', text: 'Sending verification email…' });
    try {
      await apiRequest('/api/auth/resend-verification', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ email: signupEmail }),
      });
      startResendTimer();
      setAlertMsg({ type: 'success', text: 'Verification email resent! Check your inbox and spam folder.' });
    } catch {
      startResendTimer();
      setAlertMsg({ type: 'error', text: 'Network error — please try again.' });
    }
  };

  // FORGOT PASSWORD — enter email, backend sends the reset link
  const handleForgotEmail = async (e) => {
    e.preventDefault();
    clearAll();
    if (!forgotEmail || !validateEmail(forgotEmail)) {
      setFieldErrors({ forgotEmail: 'Enter a valid email address' });
      return;
    }
    setIsLoading(true);
    await forgotPassword(forgotEmail); // backend always returns generic success
    setIsLoading(false);
    // Always navigate to FORGOT_SENT — never reveal whether email exists
    go(SCREEN.FORGOT_SENT);
  };

  // ────────────────────────────────────────────────────
  // Branded left panel
  // ────────────────────────────────────────────────────
  const BrandingPanel = () => (
    <div className="auth-branding-panel">
      <div className="branding-glow-mesh" />
      <div className="branding-content">
        <div className="branding-logo font-logo">Eva</div>
        <h1 className="branding-title font-logo">Supercharge Your Learning Journey</h1>
        <p className="branding-subtitle font-body">
          Your personal academic assistant designed to optimize study routines, schedule tasks dynamically, and build guided learning paths.
        </p>
        <div className="branding-lottie">
          <Player autoplay loop src="/lottie/coding.json" style={{ height: '280px', width: '280px' }} />
        </div>
        <div className="branding-feature-quote font-body">
          "The secret of getting ahead is getting started."
        </div>
      </div>
    </div>
  );

  // ────────────────────────────────────────────────────
  // Alert component
  // ────────────────────────────────────────────────────
  const Alert = ({ type, text }) => {
    if (!text) return null;
    return <div className={`auth-alert auth-alert--${type}`}>{text}</div>;
  };

  // ────────────────────────────────────────────────────
  // Render
  // ────────────────────────────────────────────────────
  return (
    <div className="auth-screen animate-fade-in">
      <BrandingPanel />

      <div className="auth-form-panel">
        <div className="auth-card">

          {/* Mobile logo */}
          <center>
            <span className="auth-logo font-logo mobile-only-logo">Eva</span>
          </center>

          {/* ═══════════════════════════════════ LOGIN ══ */}
          {screen === SCREEN.LOGIN && (
            <>
              <h2 className="auth-card-title font-logo">Welcome back</h2>
              <p className="auth-card-subtitle font-body">Log in to continue your progress.</p>

              <div className="tab-strip">
                <button className="tab-btn active">Log In</button>
                <button className="tab-btn" onClick={() => go(SCREEN.SIGNUP)}>Sign Up</button>
              </div>

              <Alert type={alertMsg.type} text={alertMsg.text} />

              <form className="auth-form" onSubmit={handleLogin} noValidate>
                <div className="input-group">
                  <label className="input-label">Email Address</label>
                  <input
                    id="login-email"
                    type="email"
                    className={`input-field ${fieldErrors.loginEmail || apiErrors.email ? 'error' : ''}`}
                    placeholder="Your email"
                    value={loginEmail}
                    onChange={e => setLoginEmail(e.target.value)}
                    autoComplete="email"
                  />
                  {(fieldErrors.loginEmail || apiErrors.email) && (
                    <span className="error-text">{fieldErrors.loginEmail || apiErrors.email}</span>
                  )}
                </div>

                <div className="input-group">
                  <label className="input-label">Password</label>
                  <div className="password-input-wrapper">
                    <input
                      id="login-password"
                      type={showLoginPw ? 'text' : 'password'}
                      className={`input-field ${fieldErrors.loginPassword || apiErrors.password ? 'error' : ''}`}
                      placeholder="Your password"
                      value={loginPassword}
                      onChange={e => setLoginPassword(e.target.value)}
                      autoComplete="current-password"
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowLoginPw(!showLoginPw)}>
                      {showLoginPw ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {(fieldErrors.loginPassword || apiErrors.password) && (
                    <span className="error-text">{fieldErrors.loginPassword || apiErrors.password}</span>
                  )}
                </div>

                <div className="form-options">
                  <label className="checkbox-container">
                    <input type="checkbox" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} />
                    <div className="checkbox-box" />
                    <span>Remember me</span>
                  </label>
                  <button type="button" className="forgot-password-btn" onClick={() => go(SCREEN.FORGOT_EMAIL)}>
                    Forgot password?
                  </button>
                </div>

                <button id="login-submit" type="submit" className="btn btn-primary auth-submit-btn" disabled={isLoading}>
                  {isLoading ? <Loader2 className="spinner" size={20} /> : 'Sign In'}
                </button>
              </form>

              <div className="social-login-section">
                <div className="divider-row">
                  <span className="divider-line" />
                  <span className="divider-text">Or continue with</span>
                  <span className="divider-line" />
                </div>
                <div className="google-coming-soon-wrapper">
                  <div ref={googleLoginButtonRef} id="google-login-btn" />
                </div>
              </div>
            </>
          )}

          {/* ═══════════════════════════════════ SIGNUP ══ */}
          {screen === SCREEN.SIGNUP && (
            <>
              <h2 className="auth-card-title font-logo">Create Account</h2>
              <p className="auth-card-subtitle font-body">Join Eva to supercharge your studies.</p>

              <div className="tab-strip">
                <button className="tab-btn" onClick={() => go(SCREEN.LOGIN)}>Log In</button>
                <button className="tab-btn active">Sign Up</button>
              </div>

              <Alert type={alertMsg.type} text={alertMsg.text} />

              <form className="auth-form" onSubmit={handleSignup} noValidate>
                <div className="input-group">
                  <label className="input-label">Full Name</label>
                  <input
                    id="signup-name"
                    type="text"
                    className={`input-field ${fieldErrors.signupName || apiErrors.name ? 'error' : ''}`}
                    placeholder="Your full name"
                    value={signupName}
                    onChange={e => setSignupName(e.target.value)}
                    autoComplete="name"
                  />
                  {(fieldErrors.signupName || apiErrors.name) && (
                    <span className="error-text">{fieldErrors.signupName || apiErrors.name}</span>
                  )}
                </div>

                <div className="input-group">
                  <label className="input-label">Username</label>
                  <input
                    id="signup-username"
                    type="text"
                    className={`input-field ${fieldErrors.signupUsername || apiErrors.username || apiErrors.userName ? 'error' : ''}`}
                    placeholder="e.g. johndoe"
                    value={signupUsername}
                    onChange={e => setSignupUsername(e.target.value.toLowerCase())}
                    autoComplete="username"
                  />
                  {(fieldErrors.signupUsername || apiErrors.username || apiErrors.userName) && (
                    <span className="error-text">
                      {fieldErrors.signupUsername || apiErrors.username || apiErrors.userName}
                    </span>
                  )}
                </div>

                <div className="input-group">
                  <label className="input-label">Email Address</label>
                  <input
                    id="signup-email"
                    type="email"
                    className={`input-field ${fieldErrors.signupEmail || apiErrors.email ? 'error' : ''}`}
                    placeholder="Your email"
                    value={signupEmail}
                    onChange={e => setSignupEmail(e.target.value)}
                    autoComplete="email"
                  />
                  {(fieldErrors.signupEmail || apiErrors.email) && (
                    <span className="error-text">{fieldErrors.signupEmail || apiErrors.email}</span>
                  )}
                </div>

                <div className="input-group">
                  <label className="input-label">Password</label>
                  <div className="password-input-wrapper">
                    <input
                      id="signup-password"
                      type={showSignupPw ? 'text' : 'password'}
                      className={`input-field ${fieldErrors.signupPassword || apiErrors.password ? 'error' : ''}`}
                      placeholder="8 characters minimum"
                      value={signupPassword}
                      onChange={e => setSignupPassword(e.target.value)}
                      autoComplete="new-password"
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowSignupPw(!showSignupPw)}>
                      {showSignupPw ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {(fieldErrors.signupPassword || apiErrors.password) && (
                    <span className="error-text">{fieldErrors.signupPassword || apiErrors.password}</span>
                  )}
                </div>

                <button id="signup-submit" type="submit" className="btn btn-primary auth-submit-btn" disabled={isLoading}>
                  {isLoading ? <Loader2 className="spinner" size={20} /> : 'Create Account'}
                </button>
              </form>

              <div className="social-login-section">
                <div className="divider-row">
                  <span className="divider-line" />
                  <span className="divider-text">Or continue with</span>
                  <span className="divider-line" />
                </div>
                <div className="google-coming-soon-wrapper">
                  <div ref={googleSignupButtonRef} id="google-signup-btn" />
                </div>
              </div>
            </>
          )}

          {/* ═══════════════════════════════ VERIFY EMAIL ══ */}
          {screen === SCREEN.VERIFY_EMAIL && (
            <div className="verify-email-screen">
              {/* Animated envelope icon */}
              <div className="verify-icon-ring">
                <Mail size={32} className="verify-icon" />
              </div>

              <h2 className="auth-card-title font-logo">Verify Your Email</h2>

              {/* Success banner — email was just sent */}
              <div className="auth-alert auth-alert--success" style={{ width: '100%', textAlign: 'left', marginBottom: 16 }}>
                <strong>✓ Verification email sent!</strong><br />
                We emailed a verification link to <strong>{signupEmail || 'your inbox'}</strong>.
                Click that link to activate your account.
              </div>

              <p className="auth-card-subtitle font-body" style={{ marginBottom: 20 }}>
                We emailed a verification link to <strong>{signupEmail || 'your inbox'}</strong>.
                Check your <strong>spam / junk</strong> folder if you do not see it.
              </p>

              <Alert type={alertMsg.type} text={alertMsg.text} />

              <button
                id="resend-email-only-btn"
                type="button"
                className="btn btn-primary auth-submit-btn"
                onClick={handleResend}
                disabled={isLoading || resendTimer > 0}
              >
                {isLoading
                  ? <Loader2 className="spinner" size={20} />
                  : `Resend verification email${resendTimer > 0 ? ` (${resendTimer}s)` : ''}`}
              </button>

              {/* Resend row */}
              <div className="verify-resend-row">
                <span className="verify-resend-label">Didn't receive it?</span>
                <button
                  id="resend-email-btn"
                  type="button"
                  className="resend-btn"
                  onClick={handleResend}
                  disabled={resendTimer > 0}
                >
                  <RefreshCw size={14} />
                  {resendTimer > 0 ? `Resend in ${resendTimer}s` : 'Resend Email'}
                </button>
              </div>

              <button
                type="button"
                className="back-link-btn"
                onClick={() => go(SCREEN.LOGIN)}
              >
                <ArrowLeft size={14} /> Back to Login
              </button>
            </div>
          )}

          {/* ═══════════════════════════ FORGOT — ENTER EMAIL ══ */}
          {screen === SCREEN.FORGOT_EMAIL && (
            <>
              <button className="back-link-btn" onClick={() => go(SCREEN.LOGIN)}>
                <ArrowLeft size={14} /> Back to Login
              </button>
              <h2 className="auth-card-title font-logo" style={{ marginTop: 12 }}>Forgot Password</h2>
              <p className="auth-card-subtitle font-body">
                Enter your registered email and we'll send reset instructions.
              </p>

              <Alert type={alertMsg.type} text={alertMsg.text} />

              <form className="auth-form" onSubmit={handleForgotEmail} noValidate>
                <div className="input-group">
                  <label className="input-label">Email Address</label>
                  <input
                    id="forgot-email-input"
                    type="email"
                    className={`input-field ${fieldErrors.forgotEmail ? 'error' : ''}`}
                    placeholder="Your registered email"
                    value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)}
                    autoComplete="email"
                  />
                  {fieldErrors.forgotEmail && <span className="error-text">{fieldErrors.forgotEmail}</span>}
                </div>

                <button id="forgot-submit-btn" type="submit" className="btn btn-primary auth-submit-btn" disabled={isLoading}>
                  {isLoading ? <Loader2 className="spinner" size={20} /> : 'Send Reset Link'}
                </button>
              </form>
            </>
          )}

          {/* ═══════════════════════════ FORGOT — EMAIL SENT ══ */}
          {screen === SCREEN.FORGOT_SENT && (
            <div className="verify-email-screen">
              <div className="verify-icon-ring verify-icon-ring--success">
                <Mail size={32} className="verify-icon" style={{ color: 'var(--color-success, #22c55e)' }} />
              </div>
              <h2 className="auth-card-title font-logo">Check Your Email</h2>
              <p className="auth-card-subtitle font-body">
                If <strong>{forgotEmail}</strong> is registered with Eva, you'll receive a
                password reset link in your inbox shortly.
              </p>

              <div className="auth-alert auth-alert--info" style={{ textAlign: 'left' }}>
                <strong>What to do next:</strong>
                <ol className="forgot-steps-list">
                  <li>Open the email from Eva</li>
                  <li>Click the <strong>Reset Password</strong> link</li>
                  <li>Choose a new password on the page that opens</li>
                </ol>
                <span style={{ fontSize: 12, marginTop: 8, display: 'block', opacity: 0.8 }}>
                  Don't see it? Check your spam / junk folder.
                </span>
              </div>

              <button
                id="back-to-login-from-sent"
                className="btn btn-primary auth-submit-btn"
                style={{ marginTop: 8 }}
                onClick={() => go(SCREEN.LOGIN)}
              >
                Back to Login
              </button>

              <button type="button" className="back-link-btn" style={{ marginTop: 12 }} onClick={() => go(SCREEN.FORGOT_EMAIL)}>
                <ArrowLeft size={14} /> Try a Different Email
              </button>
            </div>
          )}

        </div>{/* auth-card */}
      </div>{/* auth-form-panel */}
    </div>
  );
};

export default Auth;
