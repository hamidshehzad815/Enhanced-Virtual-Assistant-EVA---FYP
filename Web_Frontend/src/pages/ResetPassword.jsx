import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, KeyRound, CheckCircle, Eye, EyeOff, ArrowLeft, AlertTriangle } from 'lucide-react';
import PasswordStrength from '../components/PasswordStrength';
import { validatePassword, validateConfirmPassword } from '../utils/authValidation';
import './Auth.css';

export const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { resetPassword } = useAuth();

  const token = searchParams.get('token');

  const [newPassword, setNewPassword]         = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPw, setShowNewPw]             = useState(false);
  const [showConfirmPw, setShowConfirmPw]     = useState(false);
  const [isLoading, setIsLoading]             = useState(false);
  const [alertMsg, setAlertMsg]               = useState({ type: '', text: '' });
  const [status, setStatus]                   = useState('form'); // 'form' | 'success'
  const [fieldErrors, setFieldErrors]         = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAlertMsg({ type: '', text: '' });
    setFieldErrors({});

    // No token in URL
    if (!token) {
      setAlertMsg({
        type: 'error',
        text: 'Reset token is missing from the link. Please click the reset link from your email again.',
      });
      return;
    }

    // Validate (same rules the server enforces)
    const errs = {};
    const passwordProblem = validatePassword(newPassword);
    if (passwordProblem) errs.newPassword = passwordProblem;
    const confirmProblem = validateConfirmPassword(newPassword, confirmPassword);
    if (!passwordProblem && confirmProblem) errs.confirmPassword = confirmProblem;
    else if (passwordProblem && !confirmPassword) errs.confirmPassword = confirmProblem;

    if (Object.keys(errs).length) {
      setFieldErrors(errs);
      return;
    }

    setIsLoading(true);
    const result = await resetPassword(token, newPassword, confirmPassword);
    setIsLoading(false);

    if (result.success) {
      setStatus('success');
      setTimeout(() => {
        navigate('/auth', { state: { initialIndex: 0 } });
      }, 3000);
    } else if (result.fieldErrors?.new_password || result.fieldErrors?.confirm_password) {
      // Show the server's specific message (e.g. "too common", "same as current") under the right input.
      setFieldErrors({
        ...(result.fieldErrors.new_password && { newPassword: result.fieldErrors.new_password }),
        ...(result.fieldErrors.confirm_password && { confirmPassword: result.fieldErrors.confirm_password }),
      });
    } else {
      setAlertMsg({
        type: 'error',
        text: result.message || 'Failed to reset password. The link may have expired.',
      });
    }
  };

  return (
    <div className="auth-screen animate-fade-in">
      {/* Left branding panel */}
      <div className="auth-branding-panel">
        <div className="branding-glow-mesh" />
        <div className="branding-content">
          <div className="branding-logo font-logo">Eva</div>
          <h1 className="branding-title font-logo">Set a New Password</h1>
          <p className="branding-subtitle font-body">
            Choose a strong, unique password to protect your Eva account and learning progress.
          </p>
          <div className="branding-feature-quote font-body">
            "Security is not a product, but a process."
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="auth-form-panel">
        <div className="auth-card">
          {/* Mobile logo */}
          <center>
            <span className="auth-logo font-logo mobile-only-logo">Eva</span>
          </center>

          {/* ── Missing token warning ── */}
          {!token && (
            <div className="verify-email-screen">
              <div className="verify-icon-ring" style={{ background: 'rgba(239,68,68,0.1)', borderColor: 'rgba(239,68,68,0.25)', animation: 'none' }}>
                <AlertTriangle size={32} style={{ color: 'var(--color-danger, #ef4444)' }} />
              </div>
              <h2 className="auth-card-title font-logo" style={{ color: 'var(--color-danger, #ef4444)' }}>
                Invalid Link
              </h2>
              <p className="auth-card-subtitle font-body">
                This reset link is missing its token. Please click the password reset link from your email again, or request a new one.
              </p>
              <button
                className="btn btn-primary auth-submit-btn"
                onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
              >
                Back to Login
              </button>
            </div>
          )}

          {/* ── Reset form ── */}
          {token && status === 'form' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: 'rgba(99,102,241,0.1)', border: '1.5px solid rgba(99,102,241,0.25)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14,
                }}>
                  <KeyRound size={18} style={{ color: '#6366f1' }} />
                </div>
                <div>
                  <h2 className="auth-card-title font-logo" style={{ textAlign: 'left', fontSize: 22, margin: 0 }}>
                    Reset Password
                  </h2>
                  <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', margin: 0 }}>
                    Choose a new password for your account
                  </p>
                </div>
              </div>

              {alertMsg.text && (
                <div className={`auth-alert auth-alert--${alertMsg.type}`}>{alertMsg.text}</div>
              )}

              <form className="auth-form" onSubmit={handleSubmit} noValidate>
                <div className="input-group">
                  <label className="input-label">New Password</label>
                  <div className="password-input-wrapper">
                    <input
                      id="new-password"
                      type={showNewPw ? 'text' : 'password'}
                      className={`input-field ${fieldErrors.newPassword ? 'error' : ''}`}
                      placeholder="At least 8 characters"
                      value={newPassword}
                      onChange={e => { setNewPassword(e.target.value); setFieldErrors(f => ({ ...f, newPassword: undefined })); }}
                      onBlur={() => newPassword && setFieldErrors(f => ({ ...f, newPassword: validatePassword(newPassword) || undefined }))}
                      autoComplete="new-password"
                      maxLength={64}
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowNewPw(!showNewPw)}>
                      {showNewPw ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {fieldErrors.newPassword && <span className="error-text">{fieldErrors.newPassword}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label">Confirm New Password</label>
                  <div className="password-input-wrapper">
                    <input
                      id="confirm-password"
                      type={showConfirmPw ? 'text' : 'password'}
                      className={`input-field ${fieldErrors.confirmPassword ? 'error' : ''}`}
                      placeholder="Re-enter your new password"
                      value={confirmPassword}
                      onChange={e => { setConfirmPassword(e.target.value); setFieldErrors(f => ({ ...f, confirmPassword: undefined })); }}
                      onBlur={() => confirmPassword && setFieldErrors(f => ({ ...f, confirmPassword: validateConfirmPassword(newPassword, confirmPassword) || undefined }))}
                      autoComplete="new-password"
                      maxLength={64}
                    />
                    <button type="button" className="password-toggle" onClick={() => setShowConfirmPw(!showConfirmPw)}>
                      {showConfirmPw ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                  {fieldErrors.confirmPassword && <span className="error-text">{fieldErrors.confirmPassword}</span>}
                </div>

                <PasswordStrength password={newPassword} />

                <button
                  id="reset-password-submit"
                  type="submit"
                  className="btn btn-primary auth-submit-btn"
                  style={{ marginTop: 8 }}
                  disabled={isLoading}
                >
                  {isLoading ? <Loader2 className="spinner" size={20} /> : 'Update Password'}
                </button>
              </form>

              <button
                type="button"
                className="back-link-btn"
                style={{ marginTop: 16 }}
                onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
              >
                <ArrowLeft size={14} /> Back to Login
              </button>
            </>
          )}

          {/* ── Success ── */}
          {status === 'success' && (
            <div className="verify-email-screen">
              <div className="verify-icon-ring verify-icon-ring--success" style={{ margin: '0 auto 24px' }}>
                <CheckCircle size={36} style={{ color: 'var(--color-success, #22c55e)' }} />
              </div>
              <h2 className="auth-card-title font-logo" style={{ color: 'var(--color-success, #22c55e)' }}>
                Password Updated!
              </h2>
              <p className="auth-card-subtitle font-body">
                Your password has been successfully reset. Redirecting you to login in a moment…
              </p>
              <div className="auth-alert auth-alert--success">
                You can now sign in with your new password.
              </div>
              <button
                className="btn btn-primary auth-submit-btn"
                onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
              >
                Go to Login
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResetPassword;
