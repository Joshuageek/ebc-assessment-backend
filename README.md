# FIX: Vercel 404 Error

## The Problem
Vercel auto-routes `api/index.py` to the `/api` path. When a request comes to `/api/health`,
Vercel strips the `/api` prefix and passes `/health` to your Flask app.

Your original code had routes like `@app.route("/api/health")`, so `/health` never matched → 404.

## The Fix (2 steps)

### Step 1: Delete vercel.json
Vercel does NOT need `vercel.json` for Python files in the `api/` folder.
It auto-detects and auto-routes them. Delete `vercel.json` from your repo.

Your repo should now only have:
```
├── api/
│   └── index.py
├── requirements.txt
└── README.md
```

### Step 2: Update api/index.py
The routes in the Flask app must NOT have the `/api` prefix.

**OLD (broken):**
```python
@app.route("/api/submit", methods=["POST", "OPTIONS"])
@app.route("/api/health", methods=["GET"])
```

**NEW (fixed):**
```python
@app.route("/submit", methods=["POST", "OPTIONS"])
@app.route("/health", methods=["GET"])
```

### Step 3: Update your HTML forms
Your forms should POST to:
```
https://ebc-assessment-backend.vercel.app/api/submit
```

The `/api` comes from Vercel's auto-routing (because the file is `api/index.py`).
The `/submit` comes from the Flask route.

### Step 4: Redeploy
1. Commit and push the changes to GitHub
2. Vercel will auto-deploy
3. Test: `https://ebc-assessment-backend.vercel.app/api/health`
   Should return: `{"status":"healthy"}`

## URL Mapping

| What you type in browser | Vercel routes to | Flask receives | Matches route |
|---|---|---|---|
| `/api/health` | `api/index.py` | `/health` | `@app.route("/health")` ✓ |
| `/api/submit` | `api/index.py` | `/submit` | `@app.route("/submit")` ✓ |

## If it still doesn't work

Check Vercel function logs:
1. Go to your Vercel project dashboard
2. Click the latest deployment
3. Click the **Functions** tab
4. Click on `api/index.py`
5. Try hitting `/api/health` — you should see the request in the logs

If the logs show the function is being invoked but you still get 404,
the issue is in the Flask routing. Check that your routes don't have `/api/` prefix.
