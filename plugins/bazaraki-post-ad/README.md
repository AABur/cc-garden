# bazaraki-post-ad

Automate posting classified ads on [Bazaraki.com](https://www.bazaraki.com) — Cyprus's largest classifieds marketplace.

## What it does

Fills in the entire "Post an Ad" form automatically:
- 3-level category selection
- Title (handles Bazaraki's iframe-based rich text editor)
- Price + negotiable toggle
- Custom JS dropdowns (item type, condition, sub-type)
- Description
- WhatsApp contact toggle
- Location (uses your profile location)

Then **pauses at the Images section** so you can upload photos manually (browser security prevents automation), and scrolls to the Submit button when you're ready.

## Install

```
/plugin install bazaraki-post-ad@cc-garden
```

Or add the marketplace first:

```
/plugin marketplace add cc-garden github:AABur/cc-garden
/plugin install bazaraki-post-ad@cc-garden
```

## Usage

Just describe what you want to sell:

> "Post my corner sofa on Bazaraki for €600, negotiable. It's an L-shaped grey fabric sofa, good condition."

Or: "разместить объявление на Базараки"

## Requirements

- Logged in to Bazaraki.com in Chrome
- [Claude in Chrome](https://claude.ai/download) extension active

## Notes

- Title max 80 chars; no words: sale/urgent/sell/price/rent
- No phone numbers or email in description (Bazaraki rejects these)
- Photos must be uploaded manually — browser security blocks file upload automation
