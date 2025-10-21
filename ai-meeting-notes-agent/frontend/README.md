# Hackathon Demo Frontend

React + Vite single-page app to showcase the AI Meeting Notes Agent.

## Prerequisites
- Node.js 18+
- Backend endpoints (API Gateway/AppSync) exposing:
  - `POST /api/presign`
  - `POST /api/jobs`
  - `GET /api/jobs/{id}`

## Getting Started
```bash
npm install
npm run dev
```

The dev server proxies `/api` calls to `http://localhost:4000`. Update `vite.config.ts` if your backend lives elsewhere.

## Build
```bash
npm run build
```

Outputs static assets under `dist/`, deployable to S3 + CloudFront or Amplify Hosting.

## Customization
- Update `src/components/UploadForm.tsx` to tweak form fields.
- Adjust branding/styling in `src/styles.css` and `public/logo.svg`.
- Extend `src/lib/api.ts` if you add new backend routes.
