# AI News Scraper API Documentation

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication
Currently, the API is open access. For production, consider adding API key authentication.

## Rate Limiting
- **Default**: 60 requests per minute per IP
- **Configurable** via `RATE_LIMIT_REQUESTS_PER_MINUTE` environment variable

## Content Types
All endpoints return `application/json` unless specified otherwise.

---

## Core Endpoints

### 1. Get Complete AI Digest
**`GET /api/digest`**

Returns a comprehensive digest including articles, podcasts, and videos.

**Query Parameters:**
- `refresh` (optional): Set to `1` to force fresh content scraping

**Response:**
```json
{
  "summary": {
    "keyPoints": [
      "• Latest AI breakthroughs from top research labs",
      "• New model releases and their capabilities"
    ],
    "metrics": {
      "totalUpdates": 25,
      "highImpact": 5,
      "newResearch": 8,
      "industryMoves": 3
    }
  },
  "topStories": [
    {
      "title": "OpenAI Releases GPT-5",
      "source": "OpenAI",
      "significanceScore": 9.5,
      "url": "https://openai.com/blog/gpt-5"
    }
  ],
  "content": {
    "blog": [...],
    "audio": [...],
    "video": [...]
  },
  "timestamp": "2025-08-22T10:30:00Z",
  "badge": "Morning Digest"
}
```

### 2. Manual Content Scraping
**`GET /api/scrape`**

Manually trigger blog article scraping.

**Response:**
```json
{
  "message": "Scraping completed",
  "articles_found": 15,
  "articles_processed": 15,
  "sources": ["OpenAI", "Anthropic", "Hugging Face", "AI News", "VentureBeat AI"],
  "claude_available": true
}
```

### 3. Get Sources Configuration
**`GET /api/sources`**

Returns configured blog article sources.

**Response:**
```json
{
  "sources": [
    {
      "name": "OpenAI",
      "rss_url": "https://openai.com/blog/rss.xml",
      "website": "https://openai.com/blog",
      "enabled": true,
      "priority": 1
    }
  ],
  "enabled_count": 5,
  "claude_available": true
}
```

---

## Multimedia Endpoints

### 4. Manual Multimedia Scraping
**`GET /api/multimedia/scrape`**

Manually trigger podcast and video content scraping.

**Response:**
```json
{
  "message": "Multimedia scraping completed",
  "audio_found": 10,
  "video_found": 59,
  "audio_processed": 10,
  "video_processed": 59,
  "audio_sources": ["OpenAI Podcast", "Practical AI", "Latent Space"],
  "video_sources": ["Two Minute Papers", "DeepLearning.AI", "Yannic Kilcher"],
  "claude_available": true
}
```

### 5. Get Audio Content
**`GET /api/multimedia/audio`**

Returns recent podcast episodes.

**Query Parameters:**
- `hours` (optional, default: 24): Time range in hours
- `limit` (optional, default: 20): Maximum number of episodes

**Response:**
```json
{
  "audio_content": [
    {
      "title": "Inside America's AI Action Plan",
      "description": "Discussion about the White House AI Action Plan...",
      "source": "Practical AI",
      "url": "https://share.transistor.fm/s/f9da825c",
      "audio_url": "https://media.transistor.fm/f9da825c/8f07ed62.mp3",
      "duration": 2632,
      "published_date": "2025-08-19T13:51:16",
      "significance_score": 9.0,
      "processed": true
    }
  ],
  "total_count": 10,
  "hours_range": 24
}
```

### 6. Get Video Content
**`GET /api/multimedia/video`**

Returns recent AI YouTube videos.

**Query Parameters:**
- `hours` (optional, default: 24): Time range in hours
- `limit` (optional, default: 20): Maximum number of videos

**Response:**
```json
{
  "video_content": [
    {
      "title": "DeepMind Just Made The Most Powerful Game AI Engine!",
      "description": "Analysis of DeepMind's latest breakthrough...",
      "source": "Two Minute Papers",
      "url": "https://www.youtube.com/watch?v=YvuEKrJhjos",
      "thumbnail_url": "https://i4.ytimg.com/vi/YvuEKrJhjos/hqdefault.jpg",
      "duration": 0,
      "published_date": "2025-08-17T18:09:02+00:00",
      "significance_score": 8.0,
      "processed": true
    }
  ],
  "total_count": 59,
  "hours_range": 24
}
```

### 7. Get Multimedia Sources
**`GET /api/multimedia/sources`**

Returns configured multimedia sources.

**Response:**
```json
{
  "sources": {
    "audio": [
      {
        "name": "OpenAI Podcast",
        "type": "podcast_rss",
        "url": "https://feeds.transistor.fm/openai-podcast",
        "website": "https://openai.com/podcast",
        "priority": 1,
        "enabled": true
      }
    ],
    "video": [
      {
        "name": "Two Minute Papers",
        "type": "youtube_channel",
        "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
        "channel_url": "@TwoMinutePapers",
        "priority": 1,
        "enabled": true
      }
    ]
  },
  "audio_sources": 6,
  "video_sources": 6,
  "claude_available": true
}
```

---

## System Endpoints

### 8. Health Check
**`GET /api/health`**

Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-22T10:30:00Z",
  "components": {
    "database": true,
    "scraper": true,
    "processor": true,
    "multimedia_database": true,
    "multimedia_scraper": true,
    "multimedia_processor": true,
    "claude_api": true,
    "scheduler": true
  }
}
```

### 9. Root Endpoint
**`GET /`**

Returns API information.

**Response:**
```json
{
  "message": "AI News Scraper API - Optimized",
  "status": "running",
  "version": "1.1.0",
  "claude_enabled": true
}
```

---

## Content Structure

### Blog Article Object
```json
{
  "title": "Article Title",
  "description": "Article summary or excerpt",
  "source": "Source Name",
  "time": "2h ago",
  "impact": "high|medium|low",
  "type": "blog",
  "url": "https://source.com/article",
  "readTime": "5 min read",
  "significanceScore": 8.5
}
```

### Audio Episode Object
```json
{
  "title": "Episode Title",
  "description": "Episode summary",
  "source": "Podcast Name",
  "time": "1d ago",
  "impact": "high|medium|low",
  "type": "audio",
  "url": "https://podcast.com/episode",
  "audio_url": "https://media.com/audio.mp3",
  "duration": 3600,
  "significanceScore": 8.0
}
```

### Video Object
```json
{
  "title": "Video Title",
  "description": "Video summary",
  "source": "Channel Name",
  "time": "3h ago",
  "impact": "high|medium|low",
  "type": "video",
  "url": "https://youtube.com/watch?v=...",
  "thumbnail_url": "https://i.ytimg.com/vi/.../hqdefault.jpg",
  "duration": 0,
  "significanceScore": 9.0
}
```

---

## Error Responses

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Format
```json
{
  "detail": "Error message description",
  "status_code": 500
}
```

---

## CORS Configuration

The API supports CORS for cross-origin requests:

**Allowed Origins**: Configurable via `ALLOWED_ORIGINS` environment variable
**Allowed Methods**: `GET`, `POST`, `OPTIONS`
**Allowed Headers**: All headers allowed

---

## Rate Limiting

Rate limiting is applied globally:
- **Limit**: 60 requests per minute (configurable)
- **Window**: 60 seconds
- **Headers**: 
  - `X-RateLimit-Limit`: Rate limit
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Reset time

---

## Content Processing

### Significance Scoring
Content is automatically scored from 1-10 based on:
- **High Impact Terms**: breakthrough, launch, GPT, OpenAI, Google, Microsoft
- **Medium Impact Terms**: AI, machine learning, research, model
- **Claude AI Analysis**: When available, provides enhanced scoring

### Content Filtering
- Minimum content length requirements
- Duplicate detection via URL hashing
- Quality filtering based on significance scores

---

## Caching Strategy

- **Memory Cache**: In-memory caching for API responses
- **TTL**: 1 hour for content, 24 hours for processed summaries
- **Cache Keys**: Based on source names and content hashes

---

## Monitoring

### Health Checks
Regular health checks monitor:
- Database connectivity
- External API availability (Claude)
- Scheduler status
- Component initialization

### Logging
Structured logging includes:
- Request/response logging
- Error tracking
- Performance metrics
- Content processing statistics