# Frontend Integration Guide

## API Base URL
```javascript
// Development
const API_BASE_URL = 'http://localhost:8000';

// Production
const API_BASE_URL = 'https://your-api-domain.com';
```

## Core API Endpoints

### 1. Get Complete AI Digest (Recommended)
```javascript
// Fetch complete digest with articles, audio, and video
async function getAIDigest(refresh = false) {
  const url = `${API_BASE_URL}/api/digest${refresh ? '?refresh=1' : ''}`;
  const response = await fetch(url);
  return await response.json();
}

// Response structure:
{
  "summary": {
    "keyPoints": ["• Point 1", "• Point 2"],
    "metrics": {
      "totalUpdates": 25,
      "highImpact": 5,
      "newResearch": 8,
      "industryMoves": 3
    }
  },
  "topStories": [
    {
      "title": "Article Title",
      "source": "OpenAI",
      "significanceScore": 8.5,
      "url": "https://..."
    }
  ],
  "content": {
    "blog": [...],
    "audio": [...],
    "video": [...]
  },
  "timestamp": "2025-08-22T...",
  "badge": "Morning Digest"
}
```

### 2. Get Specific Content Types
```javascript
// Get blog articles only
async function getBlogArticles() {
  const response = await fetch(`${API_BASE_URL}/api/scrape`);
  return await response.json();
}

// Get audio content (podcasts)
async function getAudioContent(hours = 24, limit = 20) {
  const response = await fetch(`${API_BASE_URL}/api/multimedia/audio?hours=${hours}&limit=${limit}`);
  return await response.json();
}

// Get video content (YouTube)
async function getVideoContent(hours = 24, limit = 20) {
  const response = await fetch(`${API_BASE_URL}/api/multimedia/video?hours=${hours}&limit=${limit}`);
  return await response.json();
}
```

### 3. System Information
```javascript
// Check API health
async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return await response.json();
}

// Get configured sources
async function getSources() {
  const response = await fetch(`${API_BASE_URL}/api/sources`);
  return await response.json();
}

// Get multimedia sources
async function getMultimediaSources() {
  const response = await fetch(`${API_BASE_URL}/api/multimedia/sources`);
  return await response.json();
}
```

## React Integration Examples

### 1. Complete AI News Dashboard
```jsx
import React, { useState, useEffect } from 'react';

const AIDashboard = () => {
  const [digest, setDigest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDigest();
  }, []);

  const fetchDigest = async (refresh = false) => {
    try {
      setLoading(true);
      const data = await getAIDigest(refresh);
      setDigest(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch AI digest');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading AI digest...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="ai-dashboard">
      <header>
        <h1>AI News Digest</h1>
        <button onClick={() => fetchDigest(true)}>Refresh</button>
      </header>

      {/* Summary Section */}
      <section className="summary">
        <h2>{digest.badge}</h2>
        <div className="metrics">
          <div>Total Updates: {digest.summary.metrics.totalUpdates}</div>
          <div>High Impact: {digest.summary.metrics.highImpact}</div>
        </div>
        <ul>
          {digest.summary.keyPoints.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
      </section>

      {/* Content Tabs */}
      <ContentTabs content={digest.content} />
    </div>
  );
};

const ContentTabs = ({ content }) => {
  const [activeTab, setActiveTab] = useState('blog');

  return (
    <div className="content-tabs">
      <nav>
        <button 
          className={activeTab === 'blog' ? 'active' : ''}
          onClick={() => setActiveTab('blog')}
        >
          Articles ({content.blog.length})
        </button>
        <button 
          className={activeTab === 'audio' ? 'active' : ''}
          onClick={() => setActiveTab('audio')}
        >
          Podcasts ({content.audio.length})
        </button>
        <button 
          className={activeTab === 'video' ? 'active' : ''}
          onClick={() => setActiveTab('video')}
        >
          Videos ({content.video.length})
        </button>
      </nav>

      <div className="tab-content">
        {activeTab === 'blog' && <BlogList articles={content.blog} />}
        {activeTab === 'audio' && <AudioList episodes={content.audio} />}
        {activeTab === 'video' && <VideoList videos={content.video} />}
      </div>
    </div>
  );
};
```

### 2. Blog Articles Component
```jsx
const BlogList = ({ articles }) => (
  <div className="blog-list">
    {articles.map((article, i) => (
      <div key={i} className="blog-item">
        <h3>{article.title}</h3>
        <div className="meta">
          <span className="source">{article.source}</span>
          <span className="time">{article.time}</span>
          <span className={`impact impact-${article.impact}`}>
            {article.impact} impact
          </span>
        </div>
        <p>{article.description}</p>
        <a href={article.url} target="_blank" rel="noopener noreferrer">
          Read More
        </a>
      </div>
    ))}
  </div>
);
```

### 3. Audio Content Component
```jsx
const AudioList = ({ episodes }) => (
  <div className="audio-list">
    {episodes.map((episode, i) => (
      <div key={i} className="audio-item">
        <h3>{episode.title}</h3>
        <div className="meta">
          <span className="source">{episode.source}</span>
          <span className="time">{episode.time}</span>
          <span className="duration">
            {Math.floor(episode.duration / 60)}m
          </span>
        </div>
        <p>{episode.description}</p>
        <div className="audio-controls">
          {episode.audio_url && (
            <audio controls>
              <source src={episode.audio_url} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
          )}
          <a href={episode.url} target="_blank" rel="noopener noreferrer">
            View Episode
          </a>
        </div>
      </div>
    ))}
  </div>
);
```

### 4. Video Content Component
```jsx
const VideoList = ({ videos }) => (
  <div className="video-list">
    {videos.map((video, i) => (
      <div key={i} className="video-item">
        <div className="video-thumbnail">
          <img src={video.thumbnail_url} alt={video.title} />
          <div className="play-overlay">▶</div>
        </div>
        <div className="video-info">
          <h3>{video.title}</h3>
          <div className="meta">
            <span className="source">{video.source}</span>
            <span className="time">{video.time}</span>
          </div>
          <p>{video.description}</p>
          <a href={video.url} target="_blank" rel="noopener noreferrer">
            Watch on YouTube
          </a>
        </div>
      </div>
    ))}
  </div>
);
```

## Vue.js Integration Example

```vue
<template>
  <div class="ai-dashboard">
    <header>
      <h1>AI News Digest</h1>
      <button @click="refreshDigest" :disabled="loading">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </header>

    <div v-if="digest" class="content">
      <!-- Summary -->
      <section class="summary">
        <h2>{{ digest.badge }}</h2>
        <div class="metrics">
          <div>Total: {{ digest.summary.metrics.totalUpdates }}</div>
          <div>High Impact: {{ digest.summary.metrics.highImpact }}</div>
        </div>
      </section>

      <!-- Content Tabs -->
      <div class="tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.key"
          @click="activeTab = tab.key"
          :class="{ active: activeTab === tab.key }"
        >
          {{ tab.label }} ({{ digest.content[tab.key].length }})
        </button>
      </div>

      <!-- Content Display -->
      <div class="tab-content">
        <div v-for="item in digest.content[activeTab]" :key="item.url" class="content-item">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <a :href="item.url" target="_blank">{{ getLinkText(activeTab) }}</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AIDashboard',
  data() {
    return {
      digest: null,
      loading: false,
      activeTab: 'blog',
      tabs: [
        { key: 'blog', label: 'Articles' },
        { key: 'audio', label: 'Podcasts' },
        { key: 'video', label: 'Videos' }
      ]
    };
  },
  async mounted() {
    await this.fetchDigest();
  },
  methods: {
    async fetchDigest(refresh = false) {
      this.loading = true;
      try {
        const response = await fetch(`${process.env.VUE_APP_API_URL}/api/digest${refresh ? '?refresh=1' : ''}`);
        this.digest = await response.json();
      } catch (error) {
        console.error('Failed to fetch digest:', error);
      } finally {
        this.loading = false;
      }
    },
    async refreshDigest() {
      await this.fetchDigest(true);
    },
    getLinkText(type) {
      const texts = {
        blog: 'Read Article',
        audio: 'Listen',
        video: 'Watch Video'
      };
      return texts[type] || 'View';
    }
  }
};
</script>
```

## Error Handling & Loading States

```javascript
// Enhanced fetch with error handling
async function fetchWithErrorHandling(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// Usage with retry logic
async function getDigestWithRetry(maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetchWithErrorHandling(`${API_BASE_URL}/api/digest`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
    }
  }
}
```

## CSS Styling Examples

```css
/* Basic styling for the dashboard */
.ai-dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.content-tabs nav {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 20px;
}

.content-tabs button {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.content-tabs button.active {
  border-bottom-color: #007bff;
  color: #007bff;
}

.blog-item, .audio-item, .video-item {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}

.meta {
  display: flex;
  gap: 10px;
  margin: 5px 0;
  font-size: 0.9em;
  color: #666;
}

.impact-high { color: #d32f2f; }
.impact-medium { color: #f57c00; }
.impact-low { color: #388e3c; }

.video-thumbnail {
  position: relative;
  width: 200px;
  height: 112px;
}

.video-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.play-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px;
  border-radius: 50%;
}
```

This comprehensive integration guide provides everything needed to connect your frontend application with the multimedia-enhanced AI news scraper API!