# Deploying HabitFlow to Vercel

---

## Step 1 — Create a free Postgres database (Neon)

1. Go to https://neon.tech and sign up free
2. Click **New Project** → name it `habitflow`
3. Copy the **Connection string** — looks like:
   ```
   postgresql://nityam:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```
   Keep this, you'll need it in Step 3.

---

## Step 2 — Push code to GitHub

```bash
cd habitflow
git init
git add .
git commit -m "Initial HabitFlow commit"
```

Go to https://github.com/new → create a new **private** repo → follow the
"push existing repo" instructions GitHub shows you.

---

## Step 3 — Deploy on Vercel

1. Go to https://vercel.com → **Add New Project**
2. Import your GitHub repo
3. **Framework Preset** → select **Other**
4. **Build Command** → `bash build_files.sh`
5. **Output Directory** → leave empty
6. Click **Environment Variables** and add all of these:

| Name | Value |
|---|---|
| `SECRET_KEY` | any long random string e.g. `openssl rand -hex 32` |
| `DATABASE_URL` | your Neon connection string from Step 1 |
| `ALLOWED_HOSTS` | `your-app.vercel.app` (fill in after first deploy) |
| `DEBUG` | `False` |
| `EMAIL_HOST_USER` | `habitfloww@gmail.com` |
| `EMAIL_HOST_PASSWORD` | `amol agkr wcvx xjvh` |
| `GOOGLE_CLIENT_ID` | `65650647695-dsoilitqu0p95t7ago0t7ijq5vtc07s2.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | `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` |

7. Click **Deploy** 🚀

---

## Step 4 — Update Google OAuth redirect URI

After your first deploy, Vercel gives you a URL like `https://habitflow-xyz.vercel.app`.

1. Go to https://console.cloud.google.com
2. **APIs & Services → Credentials → your OAuth Client**
3. Add to **Authorised redirect URIs**:
   ```
   https://your-app.vercel.app/auth/google/callback/
   ```
4. Save — Google OAuth will now work in production.

---

## Step 5 — Update ALLOWED_HOSTS

In Vercel → Settings → Environment Variables, update `ALLOWED_HOSTS`:
```
habitflow-xyz.vercel.app
```
Then **Redeploy** (Deployments tab → three dots → Redeploy).

---

## Local development (still works)

```bash
pip install -r requirements.txt
python manage.py migrate        # uses SQLite locally
python manage.py runserver
```

No need to set any env vars locally — SQLite is the fallback.

---

## Troubleshooting

**500 error on Vercel** → Check **Vercel → your project → Functions → View Logs**

**Migrations didn't run** → Go to Vercel → Deployments → click latest → **Redeploy**

**Google login fails** → Make sure you added the production callback URI in Google Cloud Console (Step 4)

**Static files 404** → WhiteNoise is configured and `collectstatic` runs at build time — if you still see issues, check that `STATIC_ROOT = BASE_DIR / 'staticfiles'` is set correctly
