from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import News

# FMP category → News model category mapping
_FMP_CATEGORY_MAP = {
    "stock":  "Stocks",
    "crypto": "Cryptocurrency",
}


def _fetch_fmp_news(feed_type, limit=15):
    from app.fmp_client import get_news
    articles = get_news(feed_type, limit=limit)
    results = []
    for i, a in enumerate(articles):
        pub_date = a.get("publishedDate") or a.get("date") or ""
        results.append({
            "id": -(i + 1 + (1000 if feed_type == "crypto" else 0)),
            "title": a.get("title", ""),
            "summary": (a.get("text") or "")[:400],
            "content": a.get("text") or "",
            "category": _FMP_CATEGORY_MAP.get(feed_type, "Stocks"),
            "source": a.get("site") or a.get("publisher") or "Financial News",
            "author": a.get("publisher") or "Market News",
            "published_at": pub_date,
            "image_url": a.get("image") or "",
            "tags": [],
            "is_featured": False,
            "created_at": pub_date,
            "updated_at": pub_date,
        })
    return results


@api_view(["GET"])
@permission_classes([AllowAny])
def list_news(request):
    category = request.GET.get('category', '').strip()
    search_query = request.GET.get('search', '').strip()

    # --- DB news ---
    news_query = News.objects.filter().order_by('-is_featured', '-published_at')
    if category:
        news_query = news_query.filter(category=category)
    if search_query:
        news_query = news_query.filter(
            title__icontains=search_query
        ) | news_query.filter(
            summary__icontains=search_query
        ) | news_query.filter(
            content__icontains=search_query
        )

    db_list = []
    for article in news_query[:40]:
        image_url = None
        if article.image:
            try:
                image_url = article.image.url
            except Exception:
                pass
        db_list.append({
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "category": article.category,
            "source": article.source,
            "author": article.author,
            "published_at": article.published_at.isoformat(),
            "image_url": image_url,
            "tags": article.tags,
            "is_featured": article.is_featured,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
        })

    # --- FMP news (only when category matches or no filter) ---
    fmp_list = []
    if not category or category in ("Stocks", "Cryptocurrency"):
        try:
            if not category or category == "Stocks":
                fmp_list += _fetch_fmp_news("stock", limit=15)
            if not category or category == "Cryptocurrency":
                fmp_list += _fetch_fmp_news("crypto", limit=10)
        except Exception:
            pass

    # Apply search to FMP results
    if search_query:
        sq = search_query.lower()
        fmp_list = [
            a for a in fmp_list
            if sq in a["title"].lower() or sq in a["summary"].lower()
        ]

    # Merge: DB featured first, then all by date descending
    all_news = db_list + fmp_list
    all_news.sort(key=lambda a: (
        not a.get("is_featured", False),
        -(len(str(a.get("published_at") or ""))),
    ))

    return Response(all_news)


@api_view(["GET"])
@permission_classes([AllowAny])
def news_detail(request, news_id):
    """
    Get detailed information about a specific news article
    """
    try:
        article = News.objects.get(id=news_id)
    except News.DoesNotExist:
        return Response({
            "success": False,
            "error": "News article not found"
        }, status=404)

    # Get image URL from Cloudinary field
    image_url = None
    if article.image:
        image_url = article.image.url

    return Response({
        "success": True,
        "article": {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "category": article.category,
            "source": article.source,
            "author": article.author,
            "published_at": article.published_at.isoformat(),
            "image_url": image_url,
            "tags": article.tags,
            "is_featured": article.is_featured,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
        }
    })
