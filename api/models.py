"""
Response models for AI News Scraper API
"""
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime

# Authentication Models
class GoogleAuthRequest(BaseModel):
    token: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserProfile(BaseModel):
    user: Dict[str, Any]

# Subscription Models
class SubscriptionPreferences(BaseModel):
    frequency: str = "daily"
    content_types: List[str] = ["all"]
    categories: List[str] = ["all"]

class PreferencesResponse(BaseModel):
    preferences: Dict[str, Any]

class MessageResponse(BaseModel):
    message: str

# Content Models
class Article(BaseModel):
    title: str
    description: str
    source: str
    time: str
    impact: str
    type: str
    url: str
    readTime: str
    significanceScore: float

class TopStory(BaseModel):
    title: str
    source: str
    significanceScore: float
    url: str

class DigestSummary(BaseModel):
    keyPoints: List[str]
    metrics: Dict[str, int]

class DigestContent(BaseModel):
    blog: List[Dict[str, Any]]
    audio: List[Dict[str, Any]]
    video: List[Dict[str, Any]]

class DigestResponse(BaseModel):
    summary: DigestSummary
    topStories: List[TopStory]
    content: DigestContent
    timestamp: str
    badge: str

# Multimedia Models
class AudioContent(BaseModel):
    title: str
    description: str
    source: str
    url: str
    audio_url: str
    duration: int
    published_date: Optional[str]
    significance_score: float
    processed: bool

class VideoContent(BaseModel):
    title: str
    description: str
    source: str
    url: str
    thumbnail_url: str
    duration: int
    published_date: Optional[str]
    significance_score: float
    processed: bool

class AudioResponse(BaseModel):
    audio_content: List[AudioContent]
    total_count: int
    hours_range: int

class VideoResponse(BaseModel):
    video_content: List[VideoContent]
    total_count: int
    hours_range: int

class MultimediaSourcesResponse(BaseModel):
    sources: Dict[str, List[Dict[str, Any]]]
    audio_sources: int
    video_sources: int
    claude_available: bool

# Scraping Models
class ScrapeResponse(BaseModel):
    message: str
    articles_found: int
    articles_processed: int
    sources: List[str]
    claude_available: bool

class MultimediaScrapeResponse(BaseModel):
    message: str
    audio_found: int
    video_found: int
    audio_processed: int
    video_processed: int
    audio_sources: List[str]
    video_sources: List[str]
    claude_available: bool

class SourcesResponse(BaseModel):
    sources: List[Dict[str, Any]]
    enabled_count: int
    claude_available: bool

# Admin Models
class Subscriber(BaseModel):
    id: int
    email: str
    name: str
    created_at: str
    is_active: bool
    preferences: Dict[str, Any]

class SubscribersResponse(BaseModel):
    subscribers: List[Subscriber]
    total_count: int
    active_count: int

class SubscriberStats(BaseModel):
    total_subscribers: int
    active_subscribers: int
    inactive_subscribers: int
    frequency_breakdown: Dict[str, int]
    content_type_breakdown: Dict[str, int]

# System Models
class SystemInfo(BaseModel):
    message: str
    status: str
    version: str
    claude_enabled: bool

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Dict[str, bool]

# Error Models
class ErrorResponse(BaseModel):
    detail: str
    message: Optional[str] = None