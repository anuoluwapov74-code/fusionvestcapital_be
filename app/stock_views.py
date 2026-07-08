from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal, InvalidOperation
from django.utils.crypto import get_random_string
from .models import Stock, UserStockPosition, TradeHistory, Notification

# ---------------------------------------------------------------------------
# FMP-driven market data — curated symbol lists per category
# ---------------------------------------------------------------------------
_CATEGORY_SYMBOLS = {
    'stock': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META',
        'JPM', 'V', 'JNJ', 'WMT', 'MA', 'PG', 'UNH', 'BAC',
        'XOM', 'AVGO', 'LLY', 'NFLX', 'DIS',
    ],
    'crypto': [
        'BTCUSD', 'ETHUSD', 'BNBUSD', 'XRPUSD', 'SOLUSD',
        'ADAUSD', 'DOGEUSD', 'AVAXUSD', 'LINKUSD', 'LTCUSD',
    ],
    'etf': [
        'SPY', 'QQQ', 'IWM', 'DIA', 'GLD', 'VTI', 'VOO',
        'ARKK', 'XLF', 'XLK', 'TLT', 'EFA', 'SLV', 'XLE', 'VNQ',
    ],
    'indices': [
        'SPX', 'NDX', 'DJI', 'RUT', 'VIX',
    ],
}

_FEATURED_SYMBOLS = {'AAPL', 'MSFT', 'BTCUSD', 'ETHUSD', 'SPY', 'NVDA'}

_SYMBOL_TO_CATEGORY = {
    sym: cat
    for cat, syms in _CATEGORY_SYMBOLS.items()
    for sym in syms
}

_SYMBOL_NAMES = {
    'BTCUSD': 'Bitcoin', 'ETHUSD': 'Ethereum', 'BNBUSD': 'BNB',
    'XRPUSD': 'XRP', 'SOLUSD': 'Solana', 'ADAUSD': 'Cardano',
    'DOGEUSD': 'Dogecoin', 'AVAXUSD': 'Avalanche',
    'LINKUSD': 'Chainlink', 'LTCUSD': 'Litecoin',
    'SPX': 'S&P 500', 'NDX': 'NASDAQ 100', 'DJI': 'Dow Jones',
    'RUT': 'Russell 2000', 'VIX': 'CBOE VIX',
}

_ALL_SYMBOLS = [sym for syms in _CATEGORY_SYMBOLS.values() for sym in syms]


def _fmt_market_cap(value):
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return "N/A"
    if v <= 0:
        return "N/A"
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


@api_view(["GET"])
@permission_classes([AllowAny])
def list_stocks(request):
    from app.fmp_client import get_quotes

    featured = request.GET.get('featured', '').lower() == 'true'
    category = request.GET.get('category', '').lower()
    search = (request.GET.get('search') or '').strip().lower()

    if category and category != 'all':
        symbols = list(_CATEGORY_SYMBOLS.get(category, []))
    else:
        symbols = list(_ALL_SYMBOLS)

    if featured:
        symbols = [s for s in symbols if s in _FEATURED_SYMBOLS]

    if search:
        symbols = [
            s for s in symbols
            if search in s.lower() or search in _SYMBOL_NAMES.get(s, '').lower()
        ]

    if not symbols:
        return Response({"success": True, "stocks": []})

    try:
        quotes = get_quotes(symbols)
        quote_map = {q["symbol"].upper(): q for q in quotes if "symbol" in q}
    except Exception:
        quote_map = {}

    stocks_list = []
    for sym in symbols:
        q = quote_map.get(sym.upper(), {})
        price      = float(q.get("price") or 0)
        change     = float(q.get("change") or 0)
        change_pct = float(q.get("changePercentage") or q.get("changesPercentage") or 0)
        name       = q.get("name") or _SYMBOL_NAMES.get(sym, sym)

        stocks_list.append({
            "symbol":             sym,
            "name":               name,
            "logo_url":           f"https://financialmodelingprep.com/image-stock/{sym}.png",
            "category":           _SYMBOL_TO_CATEGORY.get(sym, "stock"),
            "price":              f"{price:.2f}",
            "change":             f"{change:.2f}",
            "change_percent":     f"{change_pct:.2f}",
            "is_positive_change": change_pct >= 0,
            "is_featured":        sym in _FEATURED_SYMBOLS,
        })

    stocks_list.sort(key=lambda x: float(x["price"]) == 0)
    return Response({"success": True, "stocks": stocks_list})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stock_detail(request, symbol):
    from app.fmp_client import fmp_get, get_profile

    symbol = symbol.upper()
    user = request.user

    try:
        quotes = fmp_get("/quote", {"symbol": symbol})
        if not (isinstance(quotes, list) and quotes):
            return Response({"success": False, "error": "Symbol not found"}, status=status.HTTP_404_NOT_FOUND)
        q = quotes[0]
    except Exception:
        return Response({"success": False, "error": "Unable to fetch market data"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    profile = get_profile(symbol)

    price      = float(q.get("price") or 0)
    change     = float(q.get("change") or 0)
    change_pct = float(q.get("changePercentage") or q.get("changesPercentage") or 0)
    market_cap = int(q.get("marketCap") or 0)
    volume     = int(q.get("volume") or 0)

    stock_data = {
        "symbol":             symbol,
        "name":               q.get("name") or profile.get("companyName") or _SYMBOL_NAMES.get(symbol, symbol),
        "logo_url":           f"https://financialmodelingprep.com/image-stock/{symbol}.png",
        "category":           _SYMBOL_TO_CATEGORY.get(symbol, "stock"),
        "price":              f"{price:.2f}",
        "change":             f"{change:.2f}",
        "change_percent":     f"{change_pct:.2f}",
        "is_positive_change": change_pct >= 0,
        "volume":             volume,
        "market_cap":         market_cap,
        "formatted_market_cap": _fmt_market_cap(market_cap),
        "sector":             profile.get("sector") or _SYMBOL_TO_CATEGORY.get(symbol, ""),
        "industry":           profile.get("industry"),
        "description":        profile.get("description"),
        "day_high":           float(q.get("dayHigh") or 0),
        "day_low":            float(q.get("dayLow") or 0),
        "year_high":          float(q.get("yearHigh") or 0),
        "year_low":           float(q.get("yearLow") or 0),
        "open":               float(q.get("open") or 0),
        "previous_close":     float(q.get("previousClose") or 0),
        "avg_volume":         int(q.get("avgVolume") or 0),
        "eps":                q.get("eps"),
        "pe":                 q.get("pe"),
        "exchange":           q.get("exchange") or profile.get("exchangeShortName"),
        "website":            profile.get("website"),
        "ceo":                profile.get("ceo"),
    }

    # User position (requires DB stock record)
    user_position = None
    try:
        db_stock = Stock.objects.get(symbol=symbol, is_active=True)
        position = UserStockPosition.objects.get(user=user, stock=db_stock, is_active=True)
        user_position = {
            "id": position.id,
            "shares": str(position.shares),
            "average_buy_price": str(position.average_buy_price),
            "total_invested": str(position.total_invested),
            "current_value": str(position.current_value),
            "profit_loss": str(position.profit_loss),
            "profit_loss_percent": str(position.profit_loss_percent),
        }
    except (Stock.DoesNotExist, UserStockPosition.DoesNotExist):
        pass

    return Response({"success": True, "stock": stock_data, "user_position": user_position})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy_stock(request):
    """
    Buy stock shares
    """
    user = request.user
    symbol = request.data.get('symbol', '').strip().upper()
    shares = request.data.get('shares', '0')

    # Validate inputs
    try:
        shares = Decimal(shares)
        if shares <= 0:
            return Response({
                "success": False,
                "error": "Shares must be greater than 0"
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            "success": False,
            "error": "Invalid shares amount"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get stock — auto-create from FMP if it's in our curated list
    try:
        stock = Stock.objects.get(symbol=symbol, is_active=True)
    except Stock.DoesNotExist:
        if symbol not in _SYMBOL_TO_CATEGORY:
            return Response({"success": False, "error": "Stock not available for trading"}, status=status.HTTP_404_NOT_FOUND)
        try:
            from app.fmp_client import fmp_get as _fmp_get
            _quotes = _fmp_get("/quote", {"symbol": symbol})
            if not (isinstance(_quotes, list) and _quotes):
                return Response({"success": False, "error": "Unable to fetch stock data"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            _q = _quotes[0]
            stock = Stock.objects.create(
                symbol=symbol,
                name=_q.get("name") or _SYMBOL_NAMES.get(symbol, symbol),
                price=Decimal(str(_q.get("price") or 0)),
                change=Decimal(str(_q.get("change") or 0)),
                change_percent=Decimal(str(_q.get("changePercentage") or _q.get("changesPercentage") or 0)),
                volume=int(_q.get("volume") or 0),
                market_cap=int(_q.get("marketCap") or 0),
                sector=_SYMBOL_TO_CATEGORY.get(symbol, "stock"),
                logo_url=f"https://financialmodelingprep.com/image-stock/{symbol}.png",
                is_active=True,
                is_featured=symbol in _FEATURED_SYMBOLS,
            )
        except Exception:
            return Response({"success": False, "error": "Unable to load stock data"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Use live FMP price for the transaction
    try:
        from app.fmp_client import fmp_get as _fmp_get2
        _lq = _fmp_get2("/quote", {"symbol": symbol})
        if isinstance(_lq, list) and _lq and _lq[0].get("price"):
            live_price = Decimal(str(_lq[0]["price"]))
            stock.price = live_price
            stock.change = Decimal(str(_lq[0].get("change") or 0))
            stock.change_percent = Decimal(str(_lq[0].get("changePercentage") or _lq[0].get("changesPercentage") or 0))
            stock.save(update_fields=['price', 'change', 'change_percent'])
    except Exception:
        pass  # Fall back to stored price

    # Calculate total cost
    total_cost = shares * stock.price

    # Check user balance
    if user.balance < total_cost:
        return Response({
            "success": False,
            "error": f"Insufficient balance. You need ${total_cost} but only have ${user.balance}",
            "required": str(total_cost),
            "current_balance": str(user.balance),
        }, status=status.HTTP_400_BAD_REQUEST)

    # Deduct from balance
    user.balance -= total_cost
    user.save(update_fields=['balance'])

    # Get or create position
    position, created = UserStockPosition.objects.get_or_create(
        user=user,
        stock=stock,
        is_active=True,
        defaults={
            'shares': shares,
            'average_buy_price': stock.price,
            'total_invested': total_cost,
        }
    )

    if not created:
        # Update existing position
        total_shares = position.shares + shares
        total_invested = position.total_invested + total_cost
        position.average_buy_price = total_invested / total_shares
        position.shares = total_shares
        position.total_invested = total_invested
        position.save(update_fields=['shares', 'average_buy_price', 'total_invested'])

    # Create trade history
    reference = f"BUY-{get_random_string(12).upper()}"
    TradeHistory.objects.create(
        user=user,
        stock=stock,
        trade_type='buy',
        shares=shares,
        price_per_share=stock.price,
        total_amount=total_cost,
        reference=reference,
    )

    # Create notification
    Notification.objects.create(
        user=user,
        type="trade",
        title="Stock Purchase Successful",
        message=f"You bought {shares} shares of {stock.symbol} for ${total_cost}",
        full_details=f"Your purchase of {shares} shares of {stock.name} ({stock.symbol}) at ${stock.price} per share has been completed. Total cost: ${total_cost}. Reference: {reference}",
        metadata={
            "stock": stock.symbol,
            "amount": f"${total_cost}",
            "shares": str(shares),
            "reference": reference,
        }
    )

    return Response({
        "success": True,
        "message": f"Successfully bought {shares} shares of {stock.symbol}",
        "reference": reference,
        "new_balance": str(user.balance),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sell_stock(request):
    """
    Sell stock shares
    """
    user = request.user
    symbol = request.data.get('symbol', '').strip().upper()
    shares = request.data.get('shares', '0')

    # Validate inputs
    try:
        shares = Decimal(shares)
        if shares <= 0:
            return Response({
                "success": False,
                "error": "Shares must be greater than 0"
            }, status=status.HTTP_400_BAD_REQUEST)
    except (ValueError, TypeError):
        return Response({
            "success": False,
            "error": "Invalid shares amount"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get stock
    try:
        stock = Stock.objects.get(symbol=symbol, is_active=True)
    except Stock.DoesNotExist:
        return Response({
            "success": False,
            "error": "Stock not found"
        }, status=status.HTTP_404_NOT_FOUND)

    # Get user position
    try:
        position = UserStockPosition.objects.get(user=user, stock=stock, is_active=True)
    except UserStockPosition.DoesNotExist:
        return Response({
            "success": False,
            "error": "You don't own any shares of this stock"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check if user has enough shares
    if position.shares < shares:
        return Response({
            "success": False,
            "error": f"You only have {position.shares} shares available",
            "available_shares": str(position.shares),
        }, status=status.HTTP_400_BAD_REQUEST)

    # Calculate sale proceeds
    sale_proceeds = shares * stock.price

    # Calculate profit/loss for this sale
    cost_basis = (position.total_invested / position.shares) * shares
    profit_loss = sale_proceeds - cost_basis

    # Add proceeds to balance
    user.balance += sale_proceeds
    user.save(update_fields=['balance'])

    # Update position
    remaining_shares = position.shares - shares
    if remaining_shares == 0:
        # Close position
        position.is_active = False
        position.save(update_fields=['is_active'])
    else:
        # Update position
        remaining_investment = position.total_invested - cost_basis
        position.shares = remaining_shares
        position.total_invested = remaining_investment
        position.save(update_fields=['shares', 'total_invested'])

    # Create trade history
    reference = f"SELL-{get_random_string(12).upper()}"
    TradeHistory.objects.create(
        user=user,
        stock=stock,
        trade_type='sell',
        shares=shares,
        price_per_share=stock.price,
        total_amount=sale_proceeds,
        profit_loss=profit_loss,
        reference=reference,
    )

    # Create notification
    profit_loss_text = f"profit of ${profit_loss}" if profit_loss >= 0 else f"loss of ${abs(profit_loss)}"
    Notification.objects.create(
        user=user,
        type="trade",
        title="Stock Sale Successful",
        message=f"You sold {shares} shares of {stock.symbol} for ${sale_proceeds} ({profit_loss_text})",
        full_details=f"Your sale of {shares} shares of {stock.name} ({stock.symbol}) at ${stock.price} per share has been completed. Sale proceeds: ${sale_proceeds}. {profit_loss_text.capitalize()}. Reference: {reference}",
        metadata={
            "stock": stock.symbol,
            "amount": f"${sale_proceeds}",
            "shares": str(shares),
            "profit_loss": str(profit_loss),
            "reference": reference,
        }
    )

    return Response({
        "success": True,
        "message": f"Successfully sold {shares} shares of {stock.symbol}",
        "reference": reference,
        "sale_proceeds": str(sale_proceeds),
        "profit_loss": str(profit_loss),
        "new_balance": str(user.balance),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_positions(request):
    """
    Get all user's active stock positions
    """
    user = request.user

    positions = UserStockPosition.objects.filter(user=user, is_active=True).select_related('stock')

    positions_list = []
    for position in positions:
        stock = position.stock
        positions_list.append({
            "id": position.id,
            "stock": {
                "symbol": stock.symbol,
                "name": stock.name,
                "logo_url": stock.logo_url,
                "current_price": str(stock.price),
            },
            "shares": str(position.shares),
            "average_buy_price": str(position.average_buy_price),
            "total_invested": str(position.total_invested),
            "current_value": str(position.current_value),
            "profit_loss": str(position.profit_loss),
            "profit_loss_percent": str(position.profit_loss_percent),
            "is_positive": position.profit_loss >= 0,
        })

    return Response({
        "success": True,
        "positions": positions_list,
    })
