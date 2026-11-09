import { Check, Circle } from 'lucide-react';
import { passwordChecks, passwordStrength } from '../utils/authValidation';

/**
 * Live password feedback shown under a "new password" input:
 * a strength bar plus a checklist of the rules the server enforces.
 */
export const PasswordStrength = ({ password, context }) => {
  if (!password) return null;

  const checks = passwordChecks(password);
  const strength = passwordStrength(password, context);
  const tone = strength.level >= 3 ? 'strong' : strength.level === 2 ? 'medium' : 'weak';

  const rules = [
    { ok: checks.length, text: '8–64 characters' },
    { ok: checks.letter, text: 'At least one letter' },
    { ok: checks.numberOrSymbol, text: 'At least one number or symbol' },
  ];

  return (
    <div className="pw-feedback" aria-live="polite">
      <div className="pw-strength-hint">
        <div className={`pw-strength-bar ${tone}`} />
        <span>{strength.label}</span>
      </div>
      <ul className="pw-rules">
        {rules.map((rule) => (
          <li key={rule.text} className={rule.ok ? 'ok' : ''}>
            {rule.ok ? <Check size={13} /> : <Circle size={11} />}
            {rule.text}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PasswordStrength;
