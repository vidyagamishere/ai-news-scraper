# ai_sources_config.py - Comprehensive AI Sources Configuration
# Enhanced with Events and Learning content categories

# Content type definitions - Professional Elite Design
CONTENT_TYPES = {
    "all_sources": {
        "name": "All Sources",
        "description": "Comprehensive AI content from all our curated sources",
        "icon": "🌐"
    },
    "blogs": {
        "name": "Blogs",
        "description": "Expert insights, analysis, and thought leadership articles",
        "icon": "✍️"
    },
    "podcasts": {
        "name": "Podcasts", 
        "description": "Audio content, interviews, and discussions from AI leaders",
        "icon": "🎧"
    },
    "videos": {
        "name": "Videos",
        "description": "Visual content, presentations, and educational videos",
        "icon": "📹"
    },
    "events": {
        "name": "Events", 
        "description": "AI conferences, webinars, workshops, and networking events",
        "icon": "📅"
    },
    "learn": {
        "name": "Learn",
        "description": "Courses, tutorials, educational content, and skill development",
        "icon": "🎓"
    }
}

AI_SOURCES = [
    # Tier 1: Major AI Companies & Research Labs (Priority 1)
    {
        "name": "OpenAI",
        "rss_url": "https://openai.com/blog/rss.xml",
        "website": "https://openai.com/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Anthropic",
        "rss_url": "https://www.anthropic.com/news/rss.xml",
        "website": "https://www.anthropic.com/news",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Google DeepMind",
        "rss_url": "https://deepmind.google/discover/blog/rss.xml",
        "website": "https://deepmind.google/discover/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Meta AI",
        "rss_url": "https://ai.meta.com/blog/rss",
        "website": "https://ai.meta.com/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Microsoft AI",
        "rss_url": "https://azure.microsoft.com/en-us/blog/feed",
        "website": "https://azure.microsoft.com/en-us/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Google AI Blog",
        "rss_url": "https://blog.google/technology/ai/rss",
        "website": "https://blog.google/technology/ai",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "NVIDIA AI",
        "rss_url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed",
        "website": "https://blogs.nvidia.com/blog/category/artificial-intelligence",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },
    {
        "name": "Stability AI",
        "rss_url": "https://stability.ai/blog/rss.xml",
        "website": "https://stability.ai/blog",
        "enabled": True,
        "priority": 1,
        "category": "company"
    },

    # Tier 2: Research Institutions & Academic Sources (Priority 2)
    {
        "name": "MIT CSAIL",
        "rss_url": "https://www.csail.mit.edu/news/rss.xml",
        "website": "https://www.csail.mit.edu/news",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },
    {
        "name": "Stanford HAI",
        "rss_url": "https://hai.stanford.edu/news/rss.xml",
        "website": "https://hai.stanford.edu/news",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },
    {
        "name": "Berkeley AI Research",
        "rss_url": "https://bair.berkeley.edu/blog/feed.xml",
        "website": "https://bair.berkeley.edu/blog",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },
    {
        "name": "CMU Machine Learning",
        "rss_url": "https://blog.ml.cmu.edu/feed",
        "website": "https://blog.ml.cmu.edu",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },
    {
        "name": "Allen Institute for AI",
        "rss_url": "https://allenai.org/news/rss",
        "website": "https://allenai.org/news",
        "enabled": True,
        "priority": 2,
        "category": "research"
    },

    # Tier 3: Major News & Media Outlets (Priority 2)
    {
        "name": "AI News",
        "rss_url": "https://artificialintelligence-news.com/feed",
        "website": "https://artificialintelligence-news.com",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "VentureBeat AI",
        "rss_url": "https://venturebeat.com/ai/feed",
        "website": "https://venturebeat.com/ai",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "TechCrunch AI",
        "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed",
        "website": "https://techcrunch.com/category/artificial-intelligence",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "The Verge AI",
        "rss_url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "website": "https://www.theverge.com/ai-artificial-intelligence",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "MIT Technology Review AI",
        "rss_url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "website": "https://www.technologyreview.com/topic/artificial-intelligence",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },
    {
        "name": "Wired AI",
        "rss_url": "https://www.wired.com/tag/artificial-intelligence/feed",
        "website": "https://www.wired.com/tag/artificial-intelligence",
        "enabled": True,
        "priority": 2,
        "category": "news"
    },

    # Tier 4: Developer Platforms & Communities (Priority 3)
    {
        "name": "Hugging Face",
        "rss_url": "https://huggingface.co/blog/feed.xml",
        "website": "https://huggingface.co/blog",
        "enabled": True,
        "priority": 3,
        "category": "platform"
    },
    {
        "name": "Papers with Code",
        "rss_url": "https://paperswithcode.com/feed.xml",
        "website": "https://paperswithcode.com",
        "enabled": True,
        "priority": 3,
        "category": "platform"
    },
    {
        "name": "Towards Data Science",
        "rss_url": "https://towardsdatascience.com/feed",
        "website": "https://towardsdatascience.com",
        "enabled": True,
        "priority": 3,
        "category": "platform"
    },
    {
        "name": "The Gradient",
        "rss_url": "https://thegradient.pub/rss",
        "website": "https://thegradient.pub",
        "enabled": True,
        "priority": 3,
        "category": "platform"
    },
    {
        "name": "Distill.pub",
        "rss_url": "https://distill.pub/rss.xml",
        "website": "https://distill.pub",
        "enabled": True,
        "priority": 3,
        "category": "platform"
    },

    # Tier 5: AI Startups & Emerging Companies (Priority 3)
    {
        "name": "Cohere",
        "rss_url": "https://cohere.com/blog/rss.xml",
        "website": "https://cohere.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "AI21 Labs",
        "rss_url": "https://www.ai21.com/blog/rss.xml",
        "website": "https://www.ai21.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Runway",
        "rss_url": "https://runwayml.com/blog/rss",
        "website": "https://runwayml.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Scale AI",
        "rss_url": "https://scale.com/blog/rss",
        "website": "https://scale.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Weights & Biases",
        "rss_url": "https://wandb.ai/blog/rss",
        "website": "https://wandb.ai/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },

    # Blog Sources - Expert Insights & Analysis
    {
        "name": "Towards Data Science",
        "rss_url": "https://towardsdatascience.com/feed",
        "website": "https://towardsdatascience.com",
        "enabled": True,
        "priority": 1,
        "category": "blogs",
        "content_type": "blogs"
    },
    {
        "name": "The Gradient Blog",
        "rss_url": "https://thegradient.pub/rss",
        "website": "https://thegradient.pub",
        "enabled": True,
        "priority": 1,
        "category": "blogs",
        "content_type": "blogs"
    },
    {
        "name": "Distill.pub",
        "rss_url": "https://distill.pub/rss.xml",
        "website": "https://distill.pub",
        "enabled": True,
        "priority": 1,
        "category": "blogs",
        "content_type": "blogs"
    },
    {
        "name": "Berkeley AI Research Blog",
        "rss_url": "https://bair.berkeley.edu/blog/feed.xml",
        "website": "https://bair.berkeley.edu/blog",
        "enabled": True,
        "priority": 1,
        "category": "blogs",
        "content_type": "blogs"
    },
    {
        "name": "OpenAI Blog",
        "rss_url": "https://openai.com/blog/rss.xml",
        "website": "https://openai.com/blog",
        "enabled": True,
        "priority": 1,
        "category": "blogs",
        "content_type": "blogs"
    },

    # Additional 70+ sources to reach 100 total
    {
        "name": "Pinecone",
        "rss_url": "https://www.pinecone.io/blog/rss.xml",
        "website": "https://www.pinecone.io/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "LangChain",
        "rss_url": "https://blog.langchain.dev/rss",
        "website": "https://blog.langchain.dev",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Replicate",
        "rss_url": "https://replicate.com/blog/rss",
        "website": "https://replicate.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Character.AI",
        "rss_url": "https://blog.character.ai/rss",
        "website": "https://blog.character.ai",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },
    {
        "name": "Midjourney",
        "rss_url": "https://docs.midjourney.com/blog/rss",
        "website": "https://docs.midjourney.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "startup"
    },

    # International AI Sources
    {
        "name": "Baidu Research",
        "rss_url": "http://research.baidu.com/Blog/rss",
        "website": "http://research.baidu.com/Blog",
        "enabled": True,
        "priority": 3,
        "category": "international"
    },
    {
        "name": "Tencent AI Lab",
        "rss_url": "https://ai.tencent.com/ailab/en/news/rss",
        "website": "https://ai.tencent.com/ailab/en/news",
        "enabled": True,
        "priority": 3,
        "category": "international"
    },
    {
        "name": "DeepL",
        "rss_url": "https://www.deepl.com/blog/rss",
        "website": "https://www.deepl.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "international"
    },

    # Specialized AI Domains
    {
        "name": "Boston Dynamics",
        "rss_url": "https://www.bostondynamics.com/blog/rss",
        "website": "https://www.bostondynamics.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "robotics"
    },
    {
        "name": "Tesla AI",
        "rss_url": "https://www.tesla.com/blog/rss",
        "website": "https://www.tesla.com/blog",
        "enabled": True,
        "priority": 3,
        "category": "automotive"
    },
    {
        "name": "Adobe Research",
        "rss_url": "https://research.adobe.com/news/rss",
        "website": "https://research.adobe.com/news",
        "enabled": True,
        "priority": 3,
        "category": "creative"
    },

    # Additional Tech Industry Sources (continuing to 100)
    {
        "name": "IBM Research AI",
        "rss_url": "https://research.ibm.com/blog/rss.xml",
        "website": "https://research.ibm.com/blog",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },
    {
        "name": "Amazon Science",
        "rss_url": "https://www.amazon.science/blog/rss.xml",
        "website": "https://www.amazon.science/blog",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },
    {
        "name": "Salesforce AI Research",
        "rss_url": "https://www.salesforceairesearch.com/rss.xml",
        "website": "https://www.salesforceairesearch.com",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },
    {
        "name": "Intel AI",
        "rss_url": "https://www.intel.com/content/www/us/en/artificial-intelligence/rss.xml",
        "website": "https://www.intel.com/content/www/us/en/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },
    {
        "name": "Qualcomm AI",
        "rss_url": "https://www.qualcomm.com/news/rss.xml",
        "website": "https://www.qualcomm.com/news",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },

    # Academic & Research Journals
    {
        "name": "Nature Machine Intelligence",
        "rss_url": "https://www.nature.com/natmachintell.rss",
        "website": "https://www.nature.com/natmachintell",
        "enabled": True,
        "priority": 4,
        "category": "research"
    },
    {
        "name": "Science Robotics",
        "rss_url": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=scirobotics",
        "website": "https://www.science.org/journal/scirobotics",
        "enabled": True,
        "priority": 4,
        "category": "research"
    },
    {
        "name": "AI Magazine",
        "rss_url": "https://onlinelibrary.wiley.com/feed/23719621/most-recent",
        "website": "https://onlinelibrary.wiley.com/journal/23719621",
        "enabled": True,
        "priority": 4,
        "category": "research"
    },

    # Additional News & Media
    {
        "name": "IEEE Spectrum AI",
        "rss_url": "https://spectrum.ieee.org/topic/artificial-intelligence/rss",
        "website": "https://spectrum.ieee.org/topic/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "news"
    },
    {
        "name": "Forbes AI",
        "rss_url": "https://www.forbes.com/ai/rss2.xml",
        "website": "https://www.forbes.com/ai",
        "enabled": True,
        "priority": 4,
        "category": "news"
    },
    {
        "name": "Reuters AI",
        "rss_url": "https://www.reuters.com/technology/artificial-intelligence/rss",
        "website": "https://www.reuters.com/technology/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "news"
    },
    {
        "name": "Associated Press AI",
        "rss_url": "https://apnews.com/hub/artificial-intelligence/rss",
        "website": "https://apnews.com/hub/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "news"
    },
    {
        "name": "BBC Technology AI",
        "rss_url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "website": "https://www.bbc.com/news/technology",
        "enabled": True,
        "priority": 4,
        "category": "news"
    },

    # Additional Platforms & Tools
    {
        "name": "Kaggle Blog",
        "rss_url": "https://medium.com/kaggle-blog/feed",
        "website": "https://medium.com/kaggle-blog",
        "enabled": True,
        "priority": 4,
        "category": "platform"
    },
    {
        "name": "MLOps Community",
        "rss_url": "https://mlops.community/feed",
        "website": "https://mlops.community",
        "enabled": True,
        "priority": 4,
        "category": "platform"
    },
    {
        "name": "Machine Learning Mastery",
        "rss_url": "https://machinelearningmastery.com/feed",
        "website": "https://machinelearningmastery.com",
        "enabled": True,
        "priority": 4,
        "category": "platform"
    },
    {
        "name": "AI/ML at Netflix",
        "rss_url": "https://netflixtechblog.com/feed",
        "website": "https://netflixtechblog.com",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },
    {
        "name": "Uber AI",
        "rss_url": "https://eng.uber.com/feed",
        "website": "https://eng.uber.com",
        "enabled": True,
        "priority": 4,
        "category": "company"
    },

    # Government & Policy Sources
    {
        "name": "AI.gov",
        "rss_url": "https://www.ai.gov/news/rss.xml",
        "website": "https://www.ai.gov/news",
        "enabled": True,
        "priority": 4,
        "category": "policy"
    },
    {
        "name": "Partnership on AI",
        "rss_url": "https://partnershiponai.org/news/rss",
        "website": "https://partnershiponai.org/news",
        "enabled": True,
        "priority": 4,
        "category": "policy"
    },
    {
        "name": "Center for AI Safety",
        "rss_url": "https://www.safe.ai/blog/rss",
        "website": "https://www.safe.ai/blog",
        "enabled": True,
        "priority": 4,
        "category": "policy"
    },
    {
        "name": "Future of Humanity Institute",
        "rss_url": "https://www.fhi.ox.ac.uk/news/rss",
        "website": "https://www.fhi.ox.ac.uk/news",
        "enabled": True,
        "priority": 4,
        "category": "policy"
    },

    # Specialized AI Applications
    {
        "name": "Grammarly Engineering",
        "rss_url": "https://www.grammarly.com/blog/engineering/rss",
        "website": "https://www.grammarly.com/blog/engineering",
        "enabled": True,
        "priority": 4,
        "category": "language"
    },
    {
        "name": "Duolingo Engineering",
        "rss_url": "https://blog.duolingo.com/rss",
        "website": "https://blog.duolingo.com",
        "enabled": True,
        "priority": 4,
        "category": "language"
    },
    {
        "name": "Unity AI",
        "rss_url": "https://blog.unity.com/technology/ai/rss",
        "website": "https://blog.unity.com/technology/ai",
        "enabled": True,
        "priority": 4,
        "category": "gaming"
    },
    {
        "name": "Epic Games AI",
        "rss_url": "https://www.unrealengine.com/en-US/blog/rss",
        "website": "https://www.unrealengine.com/en-US/blog",
        "enabled": True,
        "priority": 4,
        "category": "gaming"
    },

    # Healthcare AI
    {
        "name": "Google Health AI",
        "rss_url": "https://blog.google/technology/health/rss",
        "website": "https://blog.google/technology/health",
        "enabled": True,
        "priority": 4,
        "category": "healthcare"
    },
    {
        "name": "IBM Watson Health",
        "rss_url": "https://www.ibm.com/blogs/watson-health/feed",
        "website": "https://www.ibm.com/blogs/watson-health",
        "enabled": True,
        "priority": 4,
        "category": "healthcare"
    },

    # Financial AI
    {
        "name": "JPMorgan AI Research",
        "rss_url": "https://www.jpmorgan.com/technology/artificial-intelligence/rss",
        "website": "https://www.jpmorgan.com/technology/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "finance"
    },
    {
        "name": "Goldman Sachs AI",
        "rss_url": "https://www.goldmansachs.com/insights/technology/artificial-intelligence/rss",
        "website": "https://www.goldmansachs.com/insights/technology/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "finance"
    },

    # Edge Computing & Hardware
    {
        "name": "ARM AI",
        "rss_url": "https://www.arm.com/blogs/blueprint/rss.xml",
        "website": "https://www.arm.com/blogs/blueprint",
        "enabled": True,
        "priority": 4,
        "category": "hardware"
    },
    {
        "name": "AMD AI",
        "rss_url": "https://www.amd.com/en/corporate/news-events/rss.xml",
        "website": "https://www.amd.com/en/corporate/news-events",
        "enabled": True,
        "priority": 4,
        "category": "hardware"
    },

    # Cloud AI Services
    {
        "name": "AWS Machine Learning",
        "rss_url": "https://aws.amazon.com/blogs/machine-learning/feed",
        "website": "https://aws.amazon.com/blogs/machine-learning",
        "enabled": True,
        "priority": 4,
        "category": "cloud"
    },
    {
        "name": "Google Cloud AI",
        "rss_url": "https://cloud.google.com/blog/topics/ai-machine-learning/rss.xml",
        "website": "https://cloud.google.com/blog/topics/ai-machine-learning",
        "enabled": True,
        "priority": 4,
        "category": "cloud"
    },
    {
        "name": "Azure AI",
        "rss_url": "https://azure.microsoft.com/en-us/blog/topics/artificial-intelligence/rss",
        "website": "https://azure.microsoft.com/en-us/blog/topics/artificial-intelligence",
        "enabled": True,
        "priority": 4,
        "category": "cloud"
    },

    # Additional Startups and Emerging Technologies (to reach 100)
    {
        "name": "Cerebras",
        "rss_url": "https://www.cerebras.net/blog/rss",
        "website": "https://www.cerebras.net/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "SambaNova",
        "rss_url": "https://sambanova.ai/blog/rss",
        "website": "https://sambanova.ai/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Graphcore",
        "rss_url": "https://www.graphcore.ai/posts/rss.xml",
        "website": "https://www.graphcore.ai/posts",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Habana Labs",
        "rss_url": "https://habana.ai/blog/rss",
        "website": "https://habana.ai/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Lightmatter",
        "rss_url": "https://lightmatter.co/blog/rss",
        "website": "https://lightmatter.co/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Modular AI",
        "rss_url": "https://www.modular.com/blog/rss",
        "website": "https://www.modular.com/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Together AI",
        "rss_url": "https://www.together.ai/blog/rss",
        "website": "https://www.together.ai/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Mosaic ML",
        "rss_url": "https://www.mosaicml.com/blog/rss",
        "website": "https://www.mosaicml.com/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Inflection AI",
        "rss_url": "https://inflection.ai/blog/rss",
        "website": "https://inflection.ai/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },
    {
        "name": "Adept AI",
        "rss_url": "https://www.adept.ai/blog/rss",
        "website": "https://www.adept.ai/blog",
        "enabled": True,
        "priority": 5,
        "category": "startup"
    },

    # Events Sources - AI Conferences, Webinars, Workshops
    {
        "name": "AI Events",
        "rss_url": "https://eventil.com/events.rss?q=artificial+intelligence",
        "website": "https://eventil.com/events?q=artificial+intelligence",
        "enabled": True,
        "priority": 2,
        "category": "events",
        "content_type": "events"
    },
    {
        "name": "Meetup AI Events",
        "rss_url": "https://www.meetup.com/topics/artificial-intelligence/rss/",
        "website": "https://www.meetup.com/topics/artificial-intelligence/",
        "enabled": True,
        "priority": 2,
        "category": "events",
        "content_type": "events"
    },
    {
        "name": "NeurIPS Conference",
        "rss_url": "https://neurips.cc/feed.xml",
        "website": "https://neurips.cc",
        "enabled": True,
        "priority": 1,
        "category": "events",
        "content_type": "events"
    },
    {
        "name": "ICML Conference",
        "rss_url": "https://icml.cc/feed.xml",
        "website": "https://icml.cc",
        "enabled": True,
        "priority": 1,
        "category": "events",
        "content_type": "events"
    },
    {
        "name": "AI/ML Conference Hub",
        "rss_url": "https://aiconference.com/feed/",
        "website": "https://aiconference.com",
        "enabled": True,
        "priority": 2,
        "category": "events", 
        "content_type": "events"
    },
    {
        "name": "AI Summit Events",
        "rss_url": "https://theaisummit.com/feed/",
        "website": "https://theaisummit.com",
        "enabled": True,
        "priority": 2,
        "category": "events",
        "content_type": "events"
    },

    # Podcast Sources - AI Audio Content
    {
        "name": "Lex Fridman Podcast",
        "rss_url": "https://lexfridman.com/feed/podcast/",
        "website": "https://lexfridman.com/podcast/",
        "enabled": True,
        "priority": 1,
        "category": "podcasts",
        "content_type": "podcasts"
    },
    {
        "name": "The AI Podcast",
        "rss_url": "https://blogs.nvidia.com/ai-podcast/feed/",
        "website": "https://blogs.nvidia.com/ai-podcast/",
        "enabled": True,
        "priority": 1,
        "category": "podcasts",
        "content_type": "podcasts"
    },
    {
        "name": "Machine Learning Street Talk",
        "rss_url": "https://anchor.fm/s/26e1b2b8/podcast/rss",
        "website": "https://www.youtube.com/c/MachineLearningStreetTalk",
        "enabled": True,
        "priority": 1,
        "category": "podcasts",
        "content_type": "podcasts"
    },
    {
        "name": "Gradient Dissent",
        "rss_url": "https://wandb.ai/podcast/rss",
        "website": "https://wandb.ai/podcast",
        "enabled": True,
        "priority": 1,
        "category": "podcasts",
        "content_type": "podcasts"
    },
    {
        "name": "The TWIML AI Podcast",
        "rss_url": "https://twimlai.com/feed/podcast/",
        "website": "https://twimlai.com/podcast/",
        "enabled": True,
        "priority": 1,
        "category": "podcasts",
        "content_type": "podcasts"
    },

    # Video Sources - AI Visual Content
    {
        "name": "Two Minute Papers",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg",
        "website": "https://www.youtube.com/c/TwoMinutePapers",
        "enabled": True,
        "priority": 1,
        "category": "videos",
        "content_type": "videos"
    },
    {
        "name": "3Blue1Brown",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYO_jab_esuFRV4b17AJtAw",
        "website": "https://www.youtube.com/c/3blue1brown",
        "enabled": True,
        "priority": 1,
        "category": "videos",
        "content_type": "videos"
    },
    {
        "name": "Yannic Kilcher",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCZHmQk67mSJgfCCTn7xBfew",
        "website": "https://www.youtube.com/c/YannicKilcher",
        "enabled": True,
        "priority": 1,
        "category": "videos",
        "content_type": "videos"
    },
    {
        "name": "AI Explained",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw",
        "website": "https://www.youtube.com/c/AIExplained-Official",
        "enabled": True,
        "priority": 1,
        "category": "videos",
        "content_type": "videos"
    },
    {
        "name": "DeepLearning.AI YouTube",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcIXc5mJsHVYTZR1maL5l9w",
        "website": "https://www.youtube.com/c/Deeplearningai",
        "enabled": True,
        "priority": 1,
        "category": "videos",
        "content_type": "videos"
    },

    # Learning Sources - Courses, Tutorials, Educational Content
    {
        "name": "Coursera AI Courses",
        "rss_url": "https://www.coursera.org/browse/data-science/machine-learning.rss",
        "website": "https://www.coursera.org/browse/data-science/machine-learning",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Fast.ai",
        "rss_url": "https://www.fast.ai/feed.xml",
        "website": "https://www.fast.ai",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Machine Learning Mastery",
        "rss_url": "https://machinelearningmastery.com/feed/",
        "website": "https://machinelearningmastery.com",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Towards Data Science",
        "rss_url": "https://towardsdatascience.com/feed",
        "website": "https://towardsdatascience.com",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "DeepLearning.AI",
        "rss_url": "https://www.deeplearning.ai/blog/rss.xml",
        "website": "https://www.deeplearning.ai/blog",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "AI Research Blog",
        "rss_url": "https://ai.googleblog.com/feeds/posts/default",
        "website": "https://ai.googleblog.com",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Papers With Code",
        "rss_url": "https://paperswithcode.com/feed.xml",
        "website": "https://paperswithcode.com",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Distill.pub",
        "rss_url": "https://distill.pub/rss.xml",
        "website": "https://distill.pub",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "MIT AI News",
        "rss_url": "https://news.mit.edu/rss/research/artificial-intelligence2",
        "website": "https://news.mit.edu/topic/artificial-intelligence2",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    },
    {
        "name": "Stanford AI Blog",
        "rss_url": "https://ai.stanford.edu/blog/rss.xml",
        "website": "https://ai.stanford.edu/blog",
        "enabled": True,
        "priority": 1,
        "category": "learning",
        "content_type": "learn"
    }
]

# Configuration for fallback URLs when RSS feeds are not available
FALLBACK_SCRAPING = {
    "enabled": True,
    "max_articles_per_source": 10,
    "timeout_seconds": 30
}

# Categories for filtering and organization
CATEGORIES = [
    "company", "research", "news", "platform", "startup", 
    "international", "robotics", "automotive", "creative", 
    "policy", "language", "gaming", "healthcare", "finance",
    "hardware", "cloud", "events", "learning"
]

# Content type filtering functions
def get_sources_by_content_type(content_type):
    """Filter sources by content type (articles, events, learning)"""
    if content_type == "articles":
        return [source for source in AI_SOURCES if source.get("content_type") != "events" and source.get("content_type") != "learning"]
    return [source for source in AI_SOURCES if source.get("content_type") == content_type]

def get_enabled_sources_by_type(content_type):
    """Get enabled sources filtered by content type"""
    sources = get_sources_by_content_type(content_type)
    return [source for source in sources if source.get("enabled", True)]