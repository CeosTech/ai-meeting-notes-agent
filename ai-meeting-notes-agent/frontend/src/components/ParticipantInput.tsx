import { FormEvent, useState } from 'react';

interface Props {
  value: string[];
  onChange: (emails: string[]) => void;
}

const emailRegex = /^(?:[\w.!#$%&'*+/=?^`{|}~-]+@\w+(?:[.-]?\w+)*\.[A-Za-z]{2,})$/;

const ParticipantInput = ({ value, onChange }: Props) => {
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleAdd = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    if (!emailRegex.test(trimmed)) {
      setError('Invalid email address');
      return;
    }
    if (value.includes(trimmed)) {
      setError('Email already added');
      return;
    }
    setError(null);
    onChange([...value, trimmed]);
    setInput('');
  };

  const handleRemove = (email: string) => {
    onChange(value.filter((item) => item !== email));
  };

  return (
    <div className="grid">
      <label>Participants</label>
      <form className="grid" onSubmit={handleAdd} style={{ gridTemplateColumns: '1fr auto', gap: '0.75rem' }}>
        <input
          placeholder="participant@example.com"
          value={input}
          onChange={(evt) => setInput(evt.target.value)}
        />
        <button type="submit" className="btn-secondary">Add</button>
      </form>
      {error && <span style={{ color: '#dc2626' }}>{error}</span>}
      <div>
        {value.length === 0 && <p style={{ color: '#64748b' }}>Add at least one email address.</p>}
        {value.map((email) => (
          <span key={email} className="chip">
            {email}
            <button
              type="button"
              onClick={() => handleRemove(email)}
              style={{
                marginLeft: '0.5rem',
                border: 'none',
                background: 'transparent',
                color: '#0f172a',
                cursor: 'pointer',
                fontWeight: 700,
              }}
              aria-label={`Remove ${email}`}
            >
              ×
            </button>
          </span>
        ))}
      </div>
    </div>
  );
};

export default ParticipantInput;
