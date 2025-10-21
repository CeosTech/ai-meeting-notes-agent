import { ChangeEvent, FormEvent, useMemo, useState } from 'react';
import type { CreateJobPayload } from '../lib/api';
import ParticipantInput from './ParticipantInput';

interface Props {
  onSubmit: (payload: CreateJobPayload) => Promise<void> | void;
  isSubmitting: boolean;
}

const sourceTypeLabels: Record<CreateJobPayload['sourceType'], string> = {
  text: 'Transcript (paste or upload)',
  audio: 'Audio file (mp3, wav, m4a...)',
  video: 'Video file (mp4, webm...)',
};

const UploadForm = ({ onSubmit, isSubmitting }: Props) => {
  const [sourceType, setSourceType] = useState<CreateJobPayload['sourceType']>('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [targetLanguage, setTargetLanguage] = useState('');
  const [emailLocale, setEmailLocale] = useState('');
  const [languageHint, setLanguageHint] = useState('');

  const isFileRequired = useMemo(() => sourceType !== 'text', [sourceType]);

  const handleFileChange = (evt: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = evt.target.files?.[0] ?? null;
    setFile(selectedFile);
  };

  const handleSubmit = async (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();

    const payload: CreateJobPayload = {
      sourceType,
      participants,
      targetLanguage: targetLanguage || undefined,
      emailLocale: emailLocale || undefined,
      language: languageHint || undefined,
      text: text || undefined,
      file,
      sourceKey: file ? 'pending' : undefined,
    };

    await onSubmit(payload);
  };

  return (
    <form className="grid" onSubmit={handleSubmit}>
      <div className="grid">
        <label htmlFor="sourceType">Content Type</label>
        <select
          id="sourceType"
          value={sourceType}
          onChange={(evt) => setSourceType(evt.target.value as CreateJobPayload['sourceType'])}
        >
          <option value="text">Transcript (plain text)</option>
          <option value="audio">Audio recording</option>
          <option value="video">Video recording</option>
        </select>
        <p style={{ color: '#64748b', marginTop: '0.25rem' }}>{sourceTypeLabels[sourceType]}</p>
      </div>

      {sourceType === 'text' && (
        <div className="grid">
          <label htmlFor="textContent">Transcript text (optional)</label>
          <textarea
            id="textContent"
            rows={6}
            placeholder="Paste your transcript here or upload a file below."
            value={text}
            onChange={(evt) => setText(evt.target.value)}
          />
        </div>
      )}

      <div className="grid">
        <label htmlFor="fileUpload">Upload file {isFileRequired ? '(required)' : '(optional)'}</label>
        <input
          id="fileUpload"
          type="file"
          accept={sourceType === 'text' ? '.txt,.md,.docx,.pdf' : sourceType === 'audio' ? 'audio/*' : 'video/*'}
          onChange={handleFileChange}
          required={isFileRequired}
        />
      </div>

      <ParticipantInput value={participants} onChange={setParticipants} />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div>
          <label htmlFor="targetLanguage">Target Language (optional)</label>
          <input
            id="targetLanguage"
            placeholder="e.g. en, fr, es"
            value={targetLanguage}
            onChange={(evt) => setTargetLanguage(evt.target.value)}
          />
        </div>
        <div>
          <label htmlFor="emailLocale">Email Locale (optional)</label>
          <input
            id="emailLocale"
            placeholder="Override email locale (e.g. fr-CA)"
            value={emailLocale}
            onChange={(evt) => setEmailLocale(evt.target.value)}
          />
        </div>
        <div>
          <label htmlFor="languageHint">Language Hint (optional)</label>
          <input
            id="languageHint"
            placeholder="Skip detection (e.g. en-US)"
            value={languageHint}
            onChange={(evt) => setLanguageHint(evt.target.value)}
          />
        </div>
      </div>

      <button
        className="btn-primary"
        type="submit"
        disabled={
          isSubmitting ||
          participants.length === 0 ||
          (isFileRequired && !file)
        }
      >
        {isSubmitting ? 'Submitting…' : 'Generate Summary'}
      </button>
    </form>
  );
};

export default UploadForm;
