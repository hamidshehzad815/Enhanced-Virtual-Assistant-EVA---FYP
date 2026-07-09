import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, CheckCircle, XCircle, ArrowLeft } from 'lucide-react';
import './Auth.css';

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyEmailApi } = useAuth();

  const token = searchParams.get('token');
  const [status, setStatus] = useState('verifying'); // 'verifying' | 'success' | 'error'
  const [message, setMessage] = useState('');

  useEffect(() => {
    const doVerify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Verification token is missing from the link.');
        return;
      }

      const result = await verifyEmailApi(token);
      if (result.success) {
        setStatus('success');
        setMessage(result.message || 'Your email has been successfully verified. You can now log in.');
      } else {
        setStatus('error');
        setMessage(result.message || 'This verification link is invalid or has expired.');
      }
    };

    doVerify();
  }, [token, verifyEmailApi]);

  return (
    <div className="auth-screen animate-fade-in">
      {/* Branding panel (desktop only) */}
      <div className="auth-branding-panel">
        <div className="branding-glow-mesh" />
        <div className="branding-content">
          <div className="branding-logo font-logo">Eva</div>
          <h1 className="branding-title font-logo">Almost There!</h1>
          <p className="branding-subtitle font-body">
            One last step — confirm your email to unlock your personal learning dashboard.
          </p>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          {/* Mobile logo */}
          <center>
            <span className="auth-logo font-logo mobile-only-logo">Eva</span>
          </center>

          {/* ── Verifying ── */}
          {status === 'verifying' && (
            <div style={{ padding: '32px 0' }}>
              <Loader2
                className="spinner"
                size={52}
                style={{ color: 'var(--color-primary)', margin: '0 auto 24px', display: 'block' }}
              />
              <h2 className="auth-card-title font-logo">Verifying Email</h2>
              <p className="auth-card-subtitle font-body">
                Please wait while we confirm your account…
              </p>
            </div>
          )}

          {/* ── Success ── */}
          {status === 'success' && (
            <div style={{ padding: '24px 0' }}>
              <div className="verify-icon-ring verify-icon-ring--success" style={{ margin: '0 auto 24px' }}>
                <CheckCircle size={36} style={{ color: 'var(--color-success, #22c55e)' }} />
              </div>
              <h2 className="auth-card-title font-logo" style={{ color: 'var(--color-success, #22c55e)', marginBottom: 12 }}>
                Email Verified!
              </h2>
              <p className="auth-card-subtitle font-body" style={{ marginBottom: 28 }}>
                {message}
              </p>
              <button
                id="goto-login-after-verify"
                className="btn btn-primary auth-submit-btn"
                onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
              >
                Go to Login
              </button>
            </div>
          )}

          {/* ── Error ── */}
          {status === 'error' && (
            <div style={{ padding: '24px 0' }}>
              <div
                className="verify-icon-ring"
                style={{
                  margin: '0 auto 24px',
                  background: 'rgba(239,68,68,0.1)',
                  borderColor: 'rgba(239,68,68,0.25)',
                  animation: 'none',
                }}
              >
                <XCircle size={36} style={{ color: 'var(--color-danger, #ef4444)' }} />
              </div>
              <h2
                className="auth-card-title font-logo"
                style={{ color: 'var(--color-danger, #ef4444)', marginBottom: 12 }}
              >
                Verification Failed
              </h2>
              <p className="auth-card-subtitle font-body" style={{ marginBottom: 28 }}>
                {message}
              </p>

              <button
                id="back-to-auth-btn"
                className="btn btn-primary auth-submit-btn"
                onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
              >
                Back to Login
              </button>

              <button
                type="button"
                className="back-link-btn"
                style={{ margin: '14px auto 0', justifyContent: 'center' }}
                onClick={() => navigate('/auth', { state: { initialIndex: 1 } })}
              >
                <ArrowLeft size={14} /> Register a new account
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;
