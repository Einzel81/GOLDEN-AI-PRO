"""
تحليل الأخبار
News Sentiment Analysis
"""

import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None


class NewsAnalyzer:
    """
    محلل مشاعر الأخبار
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.analyzer = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else None
        
    async def fetch_news(self, query: str = "gold OR XAUUSD", days: int = 1) -> List[Dict]:
        """
        جلب الأخبار (يتطلب NewsAPI أو مصدر مشابه)
        """
        if not self.api_key:
            return []
        
        url = "https://newsapi.org/v2/everything"
        
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        params = {
            'q': query,
            'from': from_date,
            'sortBy': 'relevancy',
            'apiKey': self.api_key,
            'language': 'en'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return data.get('articles', [])
        except Exception as e:
            logger.error(f"Failed to fetch news: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        تحليل مشاعر النص
        """
        if not self.analyzer:
            return {'compound': 0, 'pos': 0, 'neu': 0, 'neg': 0}
        
        scores = self.analyzer.polarity_scores(text)
        return scores
    
    async def get_overall_sentiment(self) -> Dict:
        """
        الحصول على المشاعر العامة
        """
        articles = await self.fetch_news()
        
        if not articles:
            return {'sentiment': 'neutral', 'score': 0, 'articles_analyzed': 0}
        
        sentiments = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = self.analyze_sentiment(text)
            sentiments.append(sentiment['compound'])
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        return {
            'sentiment': 'bullish' if avg_sentiment > 0.2 else \
                        'bearish' if avg_sentiment < -0.2 else 'neutral',
            'score': avg_sentiment,
            'articles_analyzed': len(articles),
            'positive_count': sum(1 for s in sentiments if s > 0.2),
            'negative_count': sum(1 for s in sentiments if s < -0.2)
        }
