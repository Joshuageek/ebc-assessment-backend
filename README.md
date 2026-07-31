# EBC Assessment Backend — Final Fix

## What Was Broken

Two issues caused the "none define a top-level 'app' Flask instance" error:

1. **Syntax error in api/index.py** — Missing closing quote on `__main__`:
   ```python
   if __name__ == "__main__:     # ← missing " before the colon
   ```
   This syntax error prevented Python from parsing the file, so Vercel
could not find the `app = Flask(__name__)` variable.

2. **Possible leftover index.py at repo root** — If you have `index.py`
   at the root AND `api/index.py`, Vercel gets confused.

## The Fix (3 steps)

### Step 1: Clean your repo

Make sure your repo has EXACTLY these files and NOTHING else:

```
ebc-assessment-backend/
├── api/
│   └── index.py          ← the ONLY Python file
├── requirements.txt
└── .gitignore            ← optional
```

**Delete these if they exist:**
- `index.py` at the ROOT (not inside `api/`)
- `vercel.json` (any version)
- `app.py`
- `main.py`
- Any other `.py` files

Run this in your repo:
```bash
# Delete any root-level Python files
git rm -f index.py app.py main.py vercel.json 2>/dev/null

# Verify only api/index.py and requirements.txt exist
ls
ls api/

# Should show:
# README.md  requirements.txt  api/
# api/index.py

git add .
git commit -m "Fix: corrected syntax error, removed extra files"
git push origin main
```

### Step 2: Verify the corrected code

Open `api/index.py` and confirm line 85 reads:
```python
if __name__ == "__main__":
```
NOT:
```python
if __name__ == "__main__:
```

### Step 3: Check the Vercel build

After pushing, Vercel should auto-deploy. Look for:

```
Build Completed in /vercel/output [xxxxxms]
```

Where `xxxxxms` is more than a few seconds (30–60s is normal for Python).

You should NOT see:
```
Error: Found index.py, api/index.py but none define a top-level "app"
```

### Step 4: Test

```
https://ebc-assessment-backend.vercel.app/api/health
```

Should return: `{"status":"healthy"}`

## If You Still Get the Error

1. Go to your GitHub repo → click the file list
2. Confirm there is NO `index.py` at root level
3. Confirm `api/index.py` exists
4. Click into `api/index.py` and scroll to the bottom
5. Confirm the last line is `if __name__ == "__main__":` (with both quotes)
6. If anything looks wrong, upload the file from this package directly

## HTML Forms

Keep using:
```javascript
const API_URL = 'https://ebc-assessment-backend.vercel.app/api/submit';
```
