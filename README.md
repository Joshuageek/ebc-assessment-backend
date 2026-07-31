# EBC Assessment Backend — Clean Vercel Deploy

## What Went Wrong

Your `vercel.json` contained a `builds` array that forced Vercel to use an
outdated build system. The logs showed:

```
WARNING! Due to `builds` existing in your configuration file...
WARNING! Build output contains no "functions" or "static" directory...
Build Completed in /vercel/output [5ms]
```

5ms build = nothing was built. That's why every route returns 404.

## The Fix

### Step 1: Delete vercel.json

Remove `vercel.json` from your repository completely.
Vercel auto-detects Python files in the `api/` folder. You don't need any config file.

Your repo must look EXACTLY like this:

```
ebc-assessment-backend/
├── api/
│   └── index.py          ← Flask app
├── requirements.txt      ← Python dependencies
└── .gitignore            ← optional, but recommended
```

NO vercel.json. NO other config files.

### Step 2: Make sure your file paths are correct

- `api/index.py` must exist (not `api.py` at root, not `app.py`)
- `requirements.txt` must be at the root level

### Step 3: Commit and push

```bash
git rm vercel.json
git add .
git commit -m "Remove vercel.json — use auto-detected Python"
git push origin main
```

Vercel will auto-deploy. The build should take 30–60 seconds (not 5ms).

### Step 4: Check the build logs

Look for these lines in the Vercel build output:

```
Installing required dependencies...
Build Completed in /vercel/output [xxxxxms]
```

If the build time is more than a few seconds and you see dependency installation,
your Python function is being built correctly.

### Step 5: Test

```
https://ebc-assessment-backend.vercel.app/api/health
```

Should return: `{"status":"healthy"}`

```
https://ebc-assessment-backend.vercel.app/api/submit
```

Should return a JSON error (because you didn't POST form data), not a 404.

## URL Mapping

| Browser URL | Vercel handles | Flask sees | Route |
|---|---|---|---|
| `/api/health` | strips `/api` → `api/index.py` | `/health` | `@app.route("/health")` |
| `/api/submit` | strips `/api` → `api/index.py` | `/submit` | `@app.route("/submit")` |

## HTML Forms

In all 5 assessment HTML files, use:

```javascript
const API_URL = 'https://ebc-assessment-backend.vercel.app/api/submit';
```

## Environment Variables (already set — don't change)

Make sure these are still in Vercel Project Settings > Environment Variables:
- `SPREADSHEET_ID`
- `GOOGLE_CREDENTIALS`
