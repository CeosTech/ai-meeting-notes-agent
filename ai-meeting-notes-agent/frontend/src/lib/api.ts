export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface MeetingJob {
  id: string;
  status: JobStatus;
  sourceType: 'text' | 'audio' | 'video';
  sourceKey: string;
  targetLanguage?: string;
  emailLocale?: string;
  detectedLanguage?: string;
  finalLanguage?: string;
  translationApplied?: boolean;
  summary?: string;
  message?: string;
  participants: string[];
  createdAt: string;
  updatedAt?: string;
}

export interface PresignRequest {
  filename: string;
  contentType: string;
}

export interface PresignResponse {
  uploadUrl: string;
  objectKey: string;
  fields?: Record<string, string>;
}

export interface CreateJobPayload {
  sourceType: 'text' | 'audio' | 'video';
  sourceKey?: string;
  participants: string[];
  targetLanguage?: string;
  emailLocale?: string;
  language?: string;
  text?: string;
  file?: File | null;
}

const API_BASE = '/api';

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || `API request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function getPresignedUpload(payload: PresignRequest): Promise<PresignResponse> {
  return request<PresignResponse>('/presign', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

interface UploadArgs {
  file: File;
  uploadUrl: string;
  fields?: Record<string, string>;
}

export async function uploadFileToS3({ file, uploadUrl, fields }: UploadArgs): Promise<void> {
  if (fields && Object.keys(fields).length > 0) {
    const formData = new FormData();
    Object.entries(fields).forEach(([key, value]) => formData.append(key, value));
    formData.append('file', file);
    const res = await fetch(uploadUrl, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      throw new Error('File upload failed');
    }
    return;
  }

  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
    },
    body: file,
  });
  if (!res.ok) {
    throw new Error('File upload failed');
  }
}

type CreateJobRequest = Omit<CreateJobPayload, 'file'>;

export async function createJob(payload: CreateJobRequest): Promise<MeetingJob> {
  return request<MeetingJob>('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchJob(jobId: string): Promise<MeetingJob> {
  return request<MeetingJob>(`/jobs/${jobId}`, {
    method: 'GET',
  });
}
