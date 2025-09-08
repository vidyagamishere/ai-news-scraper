# Top Stories Configuration

## Overview
The top stories displayed on the dashboard are configured in `top_stories_config.py`. This file allows you to easily modify the stories, URLs, and significance scores without touching the main API code.

## Configuration File: `top_stories_config.py`

### Structure
Each story in the `TOP_STORIES` array contains:
- `title`: The headline of the story
- `source`: The organization or company (e.g., "OpenAI", "Google", "Meta")
- `significanceScore`: A score from 0-10 indicating importance
- `url`: The authentic URL to the actual story/announcement

### Modifying Stories
1. Open `top_stories_config.py`
2. Edit any story entry in the `TOP_STORIES` array
3. Deploy the backend to apply changes: `npx vercel --prod`

### URL Guidelines
- Use authentic URLs from official company blogs/announcements
- Avoid marketing pages that may change frequently
- Test URLs before deployment to ensure they work
- Use fallback_url from URL_VALIDATION_CONFIG for broken links

### Example Story Entry
```python
{
    "title": "OpenAI Announces GPT-4 Turbo Model",
    "source": "OpenAI", 
    "significanceScore": 9.2,
    "url": "https://openai.com/blog/chatgpt"
}
```

### Significance Score Guidelines
- 9.0-10.0: Major breakthrough announcements
- 8.0-8.9: Important product releases
- 7.0-7.9: Significant updates or research
- 6.0-6.9: Notable industry news

## Dynamic Content Scraping
The API includes intelligent web scraping capabilities:
- `enable_dynamic_scraping`: Enable LLM-powered image and summary extraction from URLs
- `fallback_image`: Default image if scraping fails or is disabled
- `fallback_url`: Used if a story URL is broken
- `update_interval_hours`: How often to refresh story URLs (24 hours)

### How Dynamic Scraping Works:
1. **Image Extraction**: Scrapes meta tags (og:image, twitter:image) from target URLs
2. **Summary Generation**: Extracts meta descriptions and titles for auto-summaries
3. **Fallback System**: Uses curated content if scraping fails
4. **Performance**: Only scrapes when image/summary is missing from config

### To Enable Dynamic Scraping:
1. Set `enable_dynamic_scraping: True` in URL_VALIDATION_CONFIG
2. Remove `imageUrl` and `summary` from stories you want to auto-scrape
3. Deploy the backend
4. The API will automatically scrape and enhance content

## Deployment
After modifying the configuration:
1. Run `npx vercel --prod` from the ai-news-scraper directory
2. The new URLs will be live immediately
3. No frontend changes needed unless you modify the story structure