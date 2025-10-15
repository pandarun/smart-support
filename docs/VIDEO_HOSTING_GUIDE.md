# Video Hosting Guide for Smart Support Presentation

## Overview

The presentation currently references a video at `docs/minsk_hackaton.mp4` (line 275 of `smart_support_presentation.tsx`). This guide explains different hosting options for making the video playable in the presentation.

## Option 1: YouTube (Recommended ⭐)

**Pros:**
- ✅ Best streaming performance worldwide
- ✅ Automatic quality adaptation
- ✅ Mobile-friendly
- ✅ No bandwidth costs
- ✅ Professional appearance
- ✅ Easy embedding

**Cons:**
- ❌ Requires YouTube account
- ❌ Video is public (unless unlisted)

**Implementation:**

1. Upload video to YouTube (set as "Unlisted" for privacy)
2. Get the video embed code
3. Update presentation to use iframe:

```jsx
// In smart_support_presentation.tsx, replace line 272-276:
<div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg p-6">
  <div className="aspect-video">
    <iframe
      width="100%"
      height="100%"
      src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
      title="Smart Support Demo"
      frameBorder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
      className="rounded-lg"
    />
  </div>
</div>
```

## Option 2: GitHub Releases (Good for Static Sites)

**Pros:**
- ✅ Direct file hosting on GitHub
- ✅ Permanent links
- ✅ Good for large files (up to 2GB)
- ✅ Version control

**Cons:**
- ❌ Not optimized for streaming
- ❌ Uses GitHub bandwidth
- ❌ Slower load times

**Implementation:**

1. Create a new GitHub release:
```bash
gh release create v1.0.0 docs/minsk_hackaton.mp4 --title "Smart Support Demo" --notes "Demo video"
```

2. Get the direct download URL (format: `https://github.com/USER/REPO/releases/download/TAG/FILE`)

3. Update presentation:
```jsx
// In smart_support_presentation.tsx:
<div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg p-6">
  <video
    controls
    className="w-full rounded-lg"
    src="https://github.com/pandarun/smart-support/releases/download/v1.0.0/minsk_hackaton.mp4"
  >
    Your browser does not support the video tag.
  </video>
</div>
```

## Option 3: External CDN (Professional Solution)

**Options:**
- **Cloudflare Stream**: $5/month for 1000 minutes
- **AWS S3 + CloudFront**: Pay-per-use (~$0.01-0.10 per GB)
- **Vimeo**: $7-75/month
- **Bunny.net**: $10/month for 250GB bandwidth

**Implementation Example (Cloudflare Stream):**

```jsx
<div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg p-6">
  <iframe
    src="https://customer-XXXXX.cloudflarestream.com/YOUR_VIDEO_ID/iframe"
    style={{ border: 'none', width: '100%', aspectRatio: '16/9' }}
    allow="accelerometer; gyroscope; autoplay; encrypted-media; picture-in-picture;"
    allowFullScreen
    className="rounded-lg"
  />
</div>
```

## Option 4: GitHub Pages Direct (Not Recommended)

**Pros:**
- ✅ Simple - just commit the file

**Cons:**
- ❌ GitHub has 100MB file size limit
- ❌ Repository size bloat
- ❌ Very slow loading
- ❌ Not optimized for video streaming

**Only use if video is <50MB**

## Recommended Approach for Hackathon

**For the presentation, I recommend this strategy:**

### 1. YouTube for Live Demo (Primary)
Upload the video to YouTube as "Unlisted" and embed it in the presentation. This gives you:
- Professional appearance
- Fast loading
- Works everywhere
- No costs

### 2. Download Link as Backup (Secondary)
Keep the video in GitHub Releases as a downloadable backup:
```bash
# Create release with video
gh release create v1.0.0 docs/minsk_hackaton.mp4 \
  --title "Smart Support v1.0.0 - Hackathon Submission" \
  --notes "Demo video and documentation"
```

### 3. Update Presentation Component

```jsx
// Slide 5: Live Demo Walkthrough (around line 270)
<div className="mt-8">
  {/* YouTube Embed */}
  <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg overflow-hidden shadow-2xl">
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

  {/* Fallback Link */}
  <div className="mt-4 text-center">
    <a
      href="https://github.com/pandarun/smart-support/releases/download/v1.0.0/minsk_hackaton.mp4"
      className="text-indigo-200 hover:text-white underline text-sm"
      target="_blank"
      rel="noopener noreferrer"
    >
      Download Video (Backup)
    </a>
  </div>
</div>
```

## Quick Start: YouTube Upload Steps

1. **Record your demo video** (recommended: 2-3 minutes)
   - Show all 6 workflow steps from E2E test
   - Narrate key features
   - Highlight metrics (95% accuracy, 3.3s response)

2. **Upload to YouTube:**
   - Go to https://studio.youtube.com
   - Click "Create" → "Upload videos"
   - Set visibility to "Unlisted" (shareable link only)
   - Title: "Smart Support - AI Customer Support Demo | Minsk Hackathon 2025"
   - Description: Add GitHub repo link

3. **Get embed code:**
   - Click "Share" → "Embed"
   - Copy the `src` URL from the iframe
   - Format: `https://www.youtube.com/embed/VIDEO_ID`

4. **Update presentation:**
   - Replace the video placeholder in `docs/smart_support_presentation.tsx`
   - Test locally: `cd presentation && npm run dev`
   - Push to GitHub to trigger deployment

## Testing Video Playback

```bash
# Test presentation locally before deploying
mkdir -p presentation
cd presentation

# Copy presentation component
cp ../docs/smart_support_presentation.tsx src/Presentation.jsx

# Install and run
npm install
npm run dev

# Open http://localhost:5173 and navigate to slide 5
```

## Final Checklist

- [ ] Video recorded (2-3 minutes, MP4 format, 1920x1080)
- [ ] Uploaded to YouTube as "Unlisted"
- [ ] Embed URL copied from YouTube
- [ ] Presentation component updated with embed code
- [ ] Tested locally with `npm run dev`
- [ ] Backup uploaded to GitHub Releases
- [ ] Pushed to main branch (triggers GitHub Pages deployment)
- [ ] Verified presentation at `https://USERNAME.github.io/smart-support/`

## URLs You'll Need

After setup, your presentation will be at:
```
https://pandarun.github.io/smart-support/
```

Your video backup will be at:
```
https://github.com/pandarun/smart-support/releases/download/v1.0.0/minsk_hackaton.mp4
```
