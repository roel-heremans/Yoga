# Assets Organization Guide

This guide explains how to organize your assets for the Instagram Content Generation Engine.

## Theme Structure

Your assets are organized by **themes** that align with your business:

### 1. **kombucha_benefits** - General Health Benefits
- **Purpose**: General kombucha health information
- **Target**: Health-conscious individuals, restaurants
- **Content**: Overview articles, general health benefits

### 2. **kombucha_research** - Scientific Research
- **Purpose**: Evidence-based, scientific content
- **Target**: Health-conscious individuals, restaurants
- **Content**: Research papers, academic studies, scientific articles

### 3. **digestive_health** - Digestive System Benefits
- **Purpose**: Focus on gut health and digestion
- **Target**: Health-conscious, yoga community, restaurants
- **Content**: Probiotics, gut microbiome, digestive health research

### 4. **immune_system** - Immune Health Benefits
- **Purpose**: Immune system support and antioxidants
- **Target**: Health-conscious, yoga community, restaurants
- **Content**: Antioxidants, immune function, polyphenols research

### 5. **yoga_wellness** - Yoga & Wellness Connection
- **Purpose**: Connect kombucha with yoga practice
- **Target**: Yoga community, health-conscious
- **Content**: Post-yoga nutrition, wellness lifestyle, holistic health

### 6. **madeira_local** - Local Madeira Focus
- **Purpose**: Local business, restaurants, Madeira community
- **Target**: Restaurants, local Madeira, tourists
- **Content**: Restaurant partnerships, local Madeira content, business info

### 7. **yoga_retreats** - Yoga Retreat Content
- **Purpose**: Promote kombucha at your yoga retreats
- **Target**: Yoga community, wellness seekers, tourists
- **Content**: Retreat information, kombucha at retreats, wellness retreat lifestyle

## Folder Structure

Images and videos are shared across all themes, while PDFs are theme-specific:

```
assets/
├── images/              # Shared images (used by all themes)
├── videos/              # Shared videos (used by all themes)
├── [theme_name]/
│   └── pdfs/           # Theme-specific PDFs
└── kombucha_quotes/     # Special folder for quotes
```

## What to Add to Each Folder

### Images Folder (`assets/images/`)
- **Shared across all themes** - Images can be used for any theme
- **Feed Posts**: High-quality photos (1080x1080 or larger)
  - Kombucha bottles/products
  - Yoga class scenes
  - Madeira landscapes
  - Wellness lifestyle photos
  - Restaurant settings
  - Retreat photos

- **Formats**: JPG, PNG, WebP
- **Tips**: Use high-resolution images, ensure good lighting
- **Location**: `assets/images/`

### Videos Folder (`assets/videos/`)
- **Shared across all themes** - Videos can be used for any theme
- **Reels**: Video clips (1080x1920 or larger)
  - Kombucha preparation/brewing
  - Yoga class snippets
  - Retreat moments
  - Product shots
  - Madeira scenery
  - Customer testimonials

- **Formats**: MP4, MOV, AVI
- **Duration**: 15-90 seconds per clip
- **Tips**: Vertical format works best for Reels
- **Location**: `assets/videos/`

### PDFs Folder (`assets/[theme]/pdfs/`)
- **Theme-specific** - Each theme has its own PDFs folder
- **Research Papers**: Scientific studies and articles
- **Health Articles**: Accessible health content
- **Business Materials**: Restaurant info, retreat details
- **Your Content**: Your own articles or information sheets

- **Formats**: PDF only
- **Tips**: PDFs will be processed to extract text for AI caption generation
- **Location**: `assets/[theme_name]/pdfs/`

## Quick Start

1. **Start with one theme** (e.g., `digestive_health`)
2. **Add 2-3 PDFs** to the `pdfs/` folder (see README.md in each pdfs folder)
3. **Add 5-10 images** to the `images/` folder
4. **Add 2-3 video clips** to the `videos/` folder
5. **Test generation**: `python main.py generate --theme digestive_health --type feed`

## Finding PDFs

Each `pdfs/` folder contains a README.md with:
- Recommended PDF types
- Where to find them (PubMed, ResearchGate, etc.)
- Search terms to use
- Content ideas

## Content Ideas by Theme

### Digestive Health
- Research on kombucha probiotics
- Gut microbiome studies
- Digestive enzyme benefits

### Immune System
- Antioxidant research
- Immune function studies
- Polyphenols and health

### Yoga Wellness
- Post-yoga nutrition articles
- Wellness lifestyle content
- Your own yoga + kombucha content

### Madeira Local
- Restaurant partnership info
- Local Madeira health trends
- Business information sheets

### Yoga Retreats
- Retreat information
- Kombucha at retreats content
- Wellness retreat lifestyle

## Tips

1. **Quality over quantity**: Better to have fewer high-quality assets
2. **Consistent branding**: Use your brand colors and style
3. **Local focus**: Emphasize Madeira and local community
4. **Yoga connection**: Highlight the yoga + kombucha connection
5. **Restaurant angle**: Include content for restaurant owners

## Next Steps

1. Review each theme's PDF README.md for specific guidance
2. Start collecting PDFs from recommended sources
3. Take/collect photos and videos aligned with each theme
4. Begin generating content: `python main.py generate --theme [theme_name] --type feed`
