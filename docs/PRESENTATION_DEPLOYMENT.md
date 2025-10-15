# Presentation Deployment Guide

## Quick Setup (5 minutes)

### 1. Enable GitHub Pages

Run these commands or configure manually:

```bash
# Using GitHub CLI (recommended)
gh repo edit --enable-pages --pages-branch gh-pages --pages-path /

# Or manually:
# 1. Go to https://github.com/pandarun/smart-support/settings/pages
# 2. Source: "GitHub Actions"
# 3. Save
```

### 2. Commit and Push the GitHub Action

```bash
# Add the workflow file
git add .github/workflows/deploy-presentation.yml
git add docs/VIDEO_HOSTING_GUIDE.md
git add docs/PRESENTATION_DEPLOYMENT.md

# Commit
git commit -m "Add GitHub Pages deployment for presentation

- GitHub Action builds React presentation from docs/smart_support_presentation.tsx
- Deploys to GitHub Pages at /smart-support/
- Auto-deploys on push to main
- Includes video hosting guide and deployment instructions"

# Push to trigger deployment
git push origin main
```

### 3. Watch Deployment

```bash
# Check workflow status
gh run watch

# Or visit: https://github.com/pandarun/smart-support/actions
```

### 4. Access Your Presentation

After deployment (2-3 minutes), visit:
```
https://pandarun.github.io/smart-support/
```

## How It Works

### GitHub Action Workflow

The workflow at `.github/workflows/deploy-presentation.yml`:

1. **Triggers** on:
   - Push to `main` branch
   - Changes to `docs/smart_support_presentation.tsx`
   - Manual dispatch

2. **Build Process**:
   - Creates a temporary Vite + React project
   - Copies your presentation component
   - Installs dependencies (React, Tailwind, Lucide icons)
   - Builds optimized production bundle
   - Uploads to GitHub Pages

3. **Deployment**:
   - Uses GitHub's official `deploy-pages` action
   - Deploys to `gh-pages` branch automatically
   - Available at `USERNAME.github.io/REPO-NAME/`

### Base Path Configuration

The presentation is configured with base path `/smart-support/` in `vite.config.js`:

```js
export default defineConfig({
  base: '/smart-support/', // Matches your repo name
})
```

**If your repo name is different**, update this in the workflow.

## Video Integration

### Option A: YouTube (Recommended)

1. **Upload video to YouTube**
2. **Update presentation** to use YouTube embed:

```jsx
// In docs/smart_support_presentation.tsx, around line 272:
<div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg overflow-hidden shadow-2xl">
  <div className="aspect-video">
    <iframe
      width="100%"
      height="100%"
      src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
      title="Smart Support Live Demo"
      frameBorder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
    />
  </div>
</div>
```

3. **Commit and push** - GitHub Action will rebuild automatically

### Option B: GitHub Releases

1. **Create release with video:**
```bash
gh release create v1.0.0 docs/minsk_hackaton.mp4 \
  --title "Smart Support v1.0.0" \
  --notes "Demo video for Minsk Hackathon submission"
```

2. **Update presentation** with video tag:
```jsx
<video controls className="w-full rounded-lg">
  <source
    src="https://github.com/pandarun/smart-support/releases/download/v1.0.0/minsk_hackaton.mp4"
    type="video/mp4"
  />
  Your browser does not support the video tag.
</video>
```

## Testing Locally

Before pushing, test the presentation locally:

```bash
# Create temporary presentation app
mkdir -p presentation
cd presentation

# Copy the workflow's setup commands (from lines 37-168 of the workflow)
# Or use this quick setup:

npm init -y
npm install react react-dom lucide-react vite @vitejs/plugin-react tailwindcss postcss autoprefixer

# Create minimal config
cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
EOF

# Copy presentation
mkdir src
cp ../docs/smart_support_presentation.tsx src/Presentation.jsx

# Create entry point
cat > src/main.jsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import Presentation from './Presentation.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Presentation />
  </React.StrictMode>,
)
EOF

# Create index.html
cat > index.html << 'EOF'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Smart Support</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
EOF

# Run dev server
npm run dev
```

Open http://localhost:5173 and test:
- ✅ All 11 slides render correctly
- ✅ Arrow keys / Space navigate slides
- ✅ Animations work smoothly
- ✅ Video placeholder/embed displays

## Troubleshooting

### Workflow Fails with "Permission denied"

**Fix:** Enable workflow permissions:
```bash
# Go to: https://github.com/pandarun/smart-support/settings/actions
# Workflow permissions: "Read and write permissions"
# Save
```

### 404 Error on Deployed Site

**Check:**
1. GitHub Pages source is set to "GitHub Actions"
2. Base path in `vite.config.js` matches your repo name
3. Workflow completed successfully (green checkmark)

### Video Not Playing

**Check:**
1. Video URL is correct and accessible
2. Video file is <2GB for GitHub Releases
3. CORS headers allow embedding (YouTube handles this automatically)
4. Browser console for errors

### Presentation Styles Broken

**Check:**
1. Tailwind CSS is properly configured in workflow
2. All dependencies installed in package.json
3. Build logs for errors: `gh run view --log`

## Manual Deployment (Alternative)

If GitHub Actions are unavailable:

```bash
# Build locally
cd presentation
npm run build

# Deploy manually with gh-pages npm package
npm install -g gh-pages
gh-pages -d dist -b gh-pages
```

## Workflow Maintenance

### Update Dependencies

The workflow pins versions for stability. To update:

```yaml
# In .github/workflows/deploy-presentation.yml
dependencies:
  "react": "^18.3.0",          # Update as needed
  "lucide-react": "^0.300.0",  # Check latest
  # etc.
```

### Change Deployment Branch

```yaml
# To deploy to a different branch:
- name: Deploy to GitHub Pages
  uses: actions/deploy-pages@v4
  with:
    branch: custom-branch  # Default: gh-pages
```

## Production Checklist

Before hackathon presentation:

- [ ] GitHub Pages enabled with "GitHub Actions" source
- [ ] Workflow completed successfully (check Actions tab)
- [ ] Presentation accessible at public URL
- [ ] Video embedded and playable
- [ ] All 11 slides render correctly
- [ ] Navigation works (arrows, space, clicks)
- [ ] Tested on mobile and desktop
- [ ] HTTPS enabled (automatic with GitHub Pages)
- [ ] Backup plan: PDF export or local HTML copy

## Support

If deployment fails:
1. Check workflow logs: `gh run view --log`
2. Verify GitHub Pages settings
3. Test locally first with `npm run dev`
4. Check [GitHub Status](https://www.githubstatus.com/) for outages

## Next Steps

1. ✅ Enable GitHub Pages
2. ✅ Push the workflow
3. ✅ Upload video to YouTube
4. ✅ Update presentation with video embed
5. ✅ Test deployed site
6. ✅ Share link in hackathon submission
