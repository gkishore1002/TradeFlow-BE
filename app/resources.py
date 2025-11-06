# resources.py
import re
from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .extensions import db, bcrypt
from .models import Strategy, Analysis, Trade, TradeLog, User
from .schemas import StrategySchema, AnalysisSchema, TradeSchema, TradeLogSchema, UserSchema
from sqlalchemy import or_, desc, asc
import cloudinary.uploader

# Constants
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# ========================
# HELPERS
# ========================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def cloudinary_upload_image(file_storage, user_id, folder="upload"):
    """Upload image to Cloudinary"""
    folder_path = f"{folder}/user_{user_id}"
    res = cloudinary.uploader.upload(
        file_storage,
        folder=folder_path,
        overwrite=False,
        unique_filename=True,
        use_filename=False,
        resource_type="image"
    )
    return res.get("secure_url")


def compute_pnl(entry_price, exit_price, quantity, trade_type):
    """Calculate Profit/Loss"""
    try:
        if entry_price is None or exit_price is None or quantity is None:
            return None
        qty = float(quantity)
        ent = float(entry_price)
        ext = float(exit_price)
        if trade_type == "Long":
            return (ext - ent) * qty
        elif trade_type == "Short":
            return (ent - ext) * qty
        return None
    except Exception:
        return None


def get_pagination_params():
    """Get pagination parameters from request"""
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 20))))
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    return page, per_page, search, sort_by, sort_order


def format_pagination_response(pagination, schema, items=None):
    """Format paginated response"""
    if items is None:
        items = pagination.items

    return {
        'items': schema.dump(items, many=True),
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num
        }
    }


# Initialize schemas
user_schema = UserSchema()
strategy_schema = StrategySchema()
strategies_schema = StrategySchema(many=True)
analysis_schema = AnalysisSchema()
analyses_schema = AnalysisSchema(many=True)
trade_schema = TradeSchema()
trades_schema = TradeSchema(many=True)
trade_log_schema = TradeLogSchema()
trade_logs_schema = TradeLogSchema(many=True)


# ========================
# AUTH RESOURCES
# ========================

class UserRegisterResource(Resource):
    """Register new user with email"""

    def post(self):
        try:
            data = request.get_json() or {}

            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            first_name = data.get("first_name", "").strip()
            last_name = data.get("last_name", "").strip()

            if not all([email, password, first_name, last_name]):
                return {"error": "Email, password, first name, and last name are required"}, 400

            if not is_valid_email(email):
                return {"error": "Invalid email format"}, 400

            if len(password) < 6:
                return {"error": "Password must be at least 6 characters long"}, 400

            if User.query.filter_by(email=email).first():
                return {"error": "Email already registered"}, 409

            pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            user = User(
                email=email,
                password_hash=pw_hash,
                first_name=first_name,
                last_name=last_name
            )
            db.session.add(user)
            db.session.commit()

            token = create_access_token(identity=str(user.id))

            return {
                "message": "User registered successfully",
                "access_token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            return {"error": f"Registration failed: {str(e)}"}, 500


class UserLoginResource(Resource):
    """Login with email and password"""

    def post(self):
        try:
            data = request.get_json() or {}

            email = data.get("email", "").strip().lower()
            password = data.get("password", "")

            if not email or not password:
                return {"error": "Email and password are required"}, 400

            user = User.query.filter_by(email=email).first()
            if not user or not bcrypt.check_password_hash(user.password_hash, password):
                return {"error": "Invalid email or password"}, 401

            token = create_access_token(identity=str(user.id))

            return {
                "message": "Login successful",
                "access_token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "avatar_url": user.avatar_url
                }
            }, 200
        except Exception as e:
            return {"error": f"Login failed: {str(e)}"}, 500


class UserProfileResource(Resource):
    """Get, Update, Delete user profile"""

    @jwt_required()
    def get(self):
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)

            if not user:
                return {"error": "User not found"}, 404

            return {
                "message": "Profile fetched successfully",
                "user": user_schema.dump(user)
            }, 200
        except Exception as e:
            return {"error": f"Failed to fetch profile: {str(e)}"}, 500

    @jwt_required()
    def put(self):
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)

            if not user:
                return {"error": "User not found"}, 404

            data = request.get_json() or {}

            if "first_name" in data and data["first_name"]:
                user.first_name = data["first_name"].strip()

            if "last_name" in data and data["last_name"]:
                user.last_name = data["last_name"].strip()

            if "bio" in data:
                user.bio = data["bio"].strip() if data["bio"] else None

            if "location" in data:
                user.location = data["location"].strip() if data["location"] else None

            if "email" in data and data["email"].strip().lower() != user.email:
                new_email = data["email"].strip().lower()
                if not is_valid_email(new_email):
                    return {"error": "Invalid email format"}, 400
                if User.query.filter_by(email=new_email).first():
                    return {"error": "Email already in use"}, 409
                user.email = new_email

            db.session.commit()

            return {
                "message": "Profile updated successfully",
                "user": user_schema.dump(user)
            }, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update profile: {str(e)}"}, 400

    @jwt_required()
    def delete(self):
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)

            if not user:
                return {"error": "User not found"}, 404

            db.session.delete(user)
            db.session.commit()

            return {"message": "Account deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete account: {str(e)}"}, 500


class UserProfileAvatarResource(Resource):
    """Upload user avatar to Cloudinary"""

    @jwt_required()
    def post(self):
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)

            if not user:
                return {"error": "User not found"}, 404

            if 'avatar' not in request.files:
                return {"error": "No file provided"}, 400

            file = request.files['avatar']
            if not file or not file.filename:
                return {"error": "No file selected"}, 400

            if not allowed_file(file.filename):
                return {"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}, 400

            avatar_url = cloudinary_upload_image(file, user_id, folder="profile")

            user.avatar_url = avatar_url
            db.session.commit()

            return {
                "message": "Avatar uploaded successfully",
                "avatar_url": avatar_url
            }, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to upload avatar: {str(e)}"}, 500


# ========================
# STRATEGY RESOURCES
# ========================

class StrategyListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page, per_page, search, sort_by, sort_order = get_pagination_params()
            query = Strategy.query.filter_by(user_id=user_id)

            if search:
                query = query.filter(
                    or_(
                        Strategy.name.ilike(f'%{search}%'),
                        Strategy.description.ilike(f'%{search}%'),
                        Strategy.category.ilike(f'%{search}%')
                    )
                )

            if hasattr(Strategy, sort_by):
                query = query.order_by(asc(getattr(Strategy, sort_by)) if sort_order.lower() == 'asc' else desc(
                    getattr(Strategy, sort_by)))
            else:
                query = query.order_by(desc(Strategy.created_at))

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return format_pagination_response(pagination, strategies_schema)
        except Exception as e:
            return {"error": f"Failed to fetch strategies: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            data = request.get_json() or {}
            data["user_id"] = user_id
            s = strategy_schema.load(data)
            db.session.add(s)
            db.session.commit()
            return strategy_schema.dump(s), 201
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create strategy: {str(e)}"}, 400


class StrategyResource(Resource):
    @jwt_required()
    def get(self, strategy_id):
        user_id = int(get_jwt_identity())
        try:
            s = Strategy.query.filter_by(id=strategy_id, user_id=user_id).first()
            if not s:
                return {"error": "Strategy not found"}, 404
            return strategy_schema.dump(s)
        except Exception as e:
            return {"error": f"Failed to fetch strategy: {str(e)}"}, 500

    @jwt_required()
    def put(self, strategy_id):
        user_id = int(get_jwt_identity())
        try:
            s = Strategy.query.filter_by(id=strategy_id, user_id=user_id).first()
            if not s:
                return {"error": "Strategy not found"}, 404
            data = request.get_json() or {}
            data.pop('user_id', None)
            data.pop('id', None)
            for k, v in data.items():
                if hasattr(s, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(s, k, v)
            db.session.commit()
            return strategy_schema.dump(s)
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update strategy: {str(e)}"}, 400

    @jwt_required()
    def delete(self, strategy_id):
        user_id = int(get_jwt_identity())
        try:
            s = Strategy.query.filter_by(id=strategy_id, user_id=user_id).first()
            if not s:
                return {"error": "Strategy not found"}, 404
            db.session.delete(s)
            db.session.commit()
            return {"message": "Strategy deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete strategy: {str(e)}"}, 400


# ========================
# ANALYSIS RESOURCES
# ========================

class AnalysisListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page, per_page, search, sort_by, sort_order = get_pagination_params()
            query = Analysis.query.filter_by(user_id=user_id)

            if search:
                query = query.filter(
                    or_(
                        Analysis.symbol.ilike(f'%{search}%'),
                        Analysis.strategy_name.ilike(f'%{search}%')
                    )
                )

            if hasattr(Analysis, sort_by):
                query = query.order_by(asc(getattr(Analysis, sort_by)) if sort_order.lower() == 'asc' else desc(
                    getattr(Analysis, sort_by)))
            else:
                query = query.order_by(desc(Analysis.created_at))

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return format_pagination_response(pagination, analyses_schema)
        except Exception as e:
            return {"error": f"Failed to fetch analyses: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            data = request.get_json() or {}
            data["user_id"] = user_id
            a = analysis_schema.load(data)
            db.session.add(a)
            db.session.commit()
            return analysis_schema.dump(a), 201
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create analysis: {str(e)}"}, 400


class AnalysisResource(Resource):
    @jwt_required()
    def get(self, analysis_id):
        user_id = int(get_jwt_identity())
        try:
            a = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
            if not a:
                return {"error": "Analysis not found"}, 404
            return analysis_schema.dump(a)
        except Exception as e:
            return {"error": f"Failed to fetch analysis: {str(e)}"}, 500

    @jwt_required()
    def put(self, analysis_id):
        user_id = int(get_jwt_identity())
        try:
            a = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
            if not a:
                return {"error": "Analysis not found"}, 404
            data = request.get_json() or {}
            data.pop('user_id', None)
            data.pop('id', None)
            for k, v in data.items():
                if hasattr(a, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(a, k, v)
            db.session.commit()
            return analysis_schema.dump(a)
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update analysis: {str(e)}"}, 400

    @jwt_required()
    def delete(self, analysis_id):
        user_id = int(get_jwt_identity())
        try:
            a = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
            if not a:
                return {"error": "Analysis not found"}, 404
            db.session.delete(a)
            db.session.commit()
            return {"message": "Analysis deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete analysis: {str(e)}"}, 400


# ========================
# TRADE RESOURCES
# ========================

class TradeListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page, per_page, search, sort_by, sort_order = get_pagination_params()
            query = Trade.query.filter_by(user_id=user_id)

            if search:
                query = query.filter(
                    or_(
                        Trade.symbol.ilike(f'%{search}%'),
                        Trade.strategy_used.ilike(f'%{search}%')
                    )
                )

            if hasattr(Trade, sort_by):
                query = query.order_by(
                    asc(getattr(Trade, sort_by)) if sort_order.lower() == 'asc' else desc(getattr(Trade, sort_by)))
            else:
                query = query.order_by(desc(Trade.created_at))

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            result = format_pagination_response(pagination, trades_schema)

            for item in result['items']:
                screenshots = item.get('screenshots') or []
                item['screenshot_urls'] = screenshots

            return result
        except Exception as e:
            return {"error": f"Failed to fetch trades: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            has_files = bool(request.files.getlist('screenshots'))
            data = {k: v for k, v in request.form.items()} if has_files else (request.get_json() or {})

            uploaded_files = request.files.getlist('screenshots') if request.files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "trade")
                    if url:
                        urls.append(url)
            if urls:
                data['screenshots'] = urls

            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key in ['quantity', 'strategy_id']:
                    processed_data[key] = int(value) if value else None
                else:
                    processed_data[key] = value

            processed_data["user_id"] = user_id

            required_fields = ['symbol', 'entry_price', 'exit_price', 'quantity', 'entry_reason', 'exit_reason']
            for field in required_fields:
                if not processed_data.get(field):
                    return {"error": f"Missing required field: {field}"}, 400

            t = trade_schema.load(processed_data)
            t.profit_loss = compute_pnl(t.entry_price, t.exit_price, t.quantity, t.trade_type)

            db.session.add(t)
            db.session.commit()

            result = trade_schema.dump(t)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result, 201
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create trade: {str(e)}"}, 400


class TradeResource(Resource):
    @jwt_required()
    def get(self, trade_id):
        user_id = int(get_jwt_identity())
        try:
            t = Trade.query.filter_by(id=trade_id, user_id=user_id).first()
            if not t:
                return {"error": "Trade not found"}, 404
            result = trade_schema.dump(t)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result
        except Exception as e:
            return {"error": f"Failed to fetch trade: {str(e)}"}, 500

    @jwt_required()
    def put(self, trade_id):
        user_id = int(get_jwt_identity())
        try:
            t = Trade.query.filter_by(id=trade_id, user_id=user_id).first()
            if not t:
                return {"error": "Trade not found"}, 404

            has_files = bool(request.files.getlist('screenshots'))
            data = {k: v for k, v in request.form.items()} if has_files else (request.get_json() or {})

            if has_files:
                uploaded_files = request.files.getlist('screenshots')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "trade")
                        if url:
                            urls.append(url)
                if urls:
                    existing = t.screenshots or []
                    data['screenshots'] = existing + urls

            data.pop('user_id', None)
            data.pop('id', None)

            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    value = float(value) if value else None
                elif key in ['quantity', 'strategy_id']:
                    value = int(value) if value else None
                if hasattr(t, key) and key not in ['id', 'user_id', 'created_at']:
                    setattr(t, key, value)

            t.profit_loss = compute_pnl(t.entry_price, t.exit_price, t.quantity, t.trade_type)
            db.session.commit()

            result = trade_schema.dump(t)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update trade: {str(e)}"}, 400

    @jwt_required()
    def delete(self, trade_id):
        user_id = int(get_jwt_identity())
        try:
            t = Trade.query.filter_by(id=trade_id, user_id=user_id).first()
            if not t:
                return {"error": "Trade not found"}, 404
            db.session.delete(t)
            db.session.commit()
            return {"message": "Trade deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete trade: {str(e)}"}, 400


# ========================
# TRADE LOG RESOURCES
# ========================

class TradeLogListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page, per_page, search, sort_by, sort_order = get_pagination_params()
            query = TradeLog.query.filter_by(user_id=user_id)

            if search:
                query = query.filter(
                    or_(
                        TradeLog.symbol.ilike(f'%{search}%'),
                        TradeLog.trading_strategy.ilike(f'%{search}%')
                    )
                )

            if hasattr(TradeLog, sort_by):
                query = query.order_by(asc(getattr(TradeLog, sort_by)) if sort_order.lower() == 'asc' else desc(
                    getattr(TradeLog, sort_by)))
            else:
                query = query.order_by(desc(TradeLog.created_at))

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            result = format_pagination_response(pagination, trade_logs_schema)

            for item in result['items']:
                screenshots = item.get('screenshots') or []
                item['screenshot_urls'] = screenshots

            return result
        except Exception as e:
            return {"error": f"Failed to fetch trade logs: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            has_files = bool(request.files.getlist('screenshots'))
            data = {k: v for k, v in request.form.items()} if has_files else (request.get_json() or {})
            data["user_id"] = user_id

            uploaded_files = request.files.getlist('screenshots') if request.files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "tradelog")
                    if url:
                        urls.append(url)

            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key == 'quantity':
                    processed_data[key] = int(value) if value else None
                else:
                    processed_data[key] = value

            tl = trade_log_schema.load(processed_data)
            if urls:
                tl.screenshots = urls

            trade_type = data.get("trade_type", "Long")
            trade = Trade(
                user_id=user_id,
                strategy_id=getattr(tl, "strategy_id", None),
                symbol=tl.symbol,
                entry_price=tl.entry_price,
                exit_price=tl.exit_price,
                quantity=tl.quantity,
                trade_type=trade_type,
                strategy_used=getattr(tl, "trading_strategy", None),
                entry_reason=getattr(tl, "trade_notes", "") or "",
                exit_reason="",
                screenshots=urls if urls else None,
            )
            trade.profit_loss = compute_pnl(trade.entry_price, trade.exit_price, trade.quantity, trade.trade_type)

            db.session.add(trade)
            db.session.flush()

            tl.trade_id = trade.id
            tl.profit_loss = compute_pnl(tl.entry_price, tl.exit_price, tl.quantity, trade_type)

            db.session.add(tl)
            db.session.commit()

            result = trade_log_schema.dump(tl)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result, 201
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to create trade log: {str(e)}"}, 400


class TradeLogResource(Resource):
    @jwt_required()
    def get(self, log_id):
        user_id = int(get_jwt_identity())
        try:
            tl = TradeLog.query.filter_by(id=log_id, user_id=user_id).first()
            if not tl:
                return {"error": "Trade log not found"}, 404
            result = trade_log_schema.dump(tl)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result
        except Exception as e:
            return {"error": f"Failed to fetch trade log: {str(e)}"}, 500

    @jwt_required()
    def put(self, log_id):
        user_id = int(get_jwt_identity())
        try:
            tl = TradeLog.query.filter_by(id=log_id, user_id=user_id).first()
            if not tl:
                return {"error": "Trade log not found"}, 404

            has_files = bool(request.files.getlist('screenshots'))
            data = {k: v for k, v in request.form.items()} if has_files else (request.get_json() or {})

            if has_files:
                uploaded_files = request.files.getlist('screenshots')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "tradelog")
                        if url:
                            urls.append(url)
                if urls:
                    existing = tl.screenshots or []
                    data['screenshots'] = existing + urls

            data.pop('user_id', None)
            data.pop('id', None)

            trade_type = data.get("trade_type", None)
            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key == 'quantity':
                    processed_data[key] = int(value) if value else None
                else:
                    processed_data[key] = value

            for k, v in processed_data.items():
                if hasattr(tl, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(tl, k, v)

            if tl.trade_id:
                t = Trade.query.filter_by(id=tl.trade_id, user_id=user_id).first()
                if t:
                    t.symbol = tl.symbol
                    t.entry_price = tl.entry_price
                    t.exit_price = tl.exit_price
                    t.quantity = tl.quantity
                    if trade_type is not None:
                        t.trade_type = trade_type
                    if tl.screenshots:
                        t.screenshots = tl.screenshots
                    t.profit_loss = compute_pnl(t.entry_price, t.exit_price, t.quantity, t.trade_type)

            if trade_type is None and tl.trade_id:
                linked_trade = Trade.query.get(tl.trade_id)
                trade_type = linked_trade.trade_type if linked_trade else "Long"
            tl.profit_loss = compute_pnl(tl.entry_price, tl.exit_price, tl.quantity, trade_type or "Long")

            db.session.commit()

            result = trade_log_schema.dump(tl)
            screenshots = result.get('screenshots') or []
            result['screenshot_urls'] = screenshots
            return result
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update trade log: {str(e)}"}, 400

    @jwt_required()
    def delete(self, log_id):
        user_id = int(get_jwt_identity())
        try:
            tl = TradeLog.query.filter_by(id=log_id, user_id=user_id).first()
            if not tl:
                return {"error": "Trade log not found"}, 404

            if tl.trade_id:
                linked_trade = Trade.query.filter_by(id=tl.trade_id, user_id=user_id).first()
                if linked_trade:
                    db.session.delete(linked_trade)

            db.session.delete(tl)
            db.session.commit()
            return {"message": "Trade log deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to delete trade log: {str(e)}"}, 400


# ========================
# STRATEGY WISE TRADES
# ========================

class StrategyWiseTradesResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page, per_page, search, sort_by, sort_order = get_pagination_params()
            trade_logs_query = TradeLog.query.filter_by(user_id=user_id)

            if search:
                trade_logs_query = trade_logs_query.filter(
                    or_(
                        TradeLog.symbol.ilike(f'%{search}%'),
                        TradeLog.trading_strategy.ilike(f'%{search}%')
                    )
                )

            trade_logs = trade_logs_query.all()
            strategy_trades = {}

            for trade_log in trade_logs:
                strategy_name = trade_log.trading_strategy or "No Strategy"
                if strategy_name not in strategy_trades:
                    strategy_trades[strategy_name] = {
                        "strategy_name": strategy_name,
                        "total_trades": 0,
                        "success_trades": 0,
                        "loss_trades": 0,
                        "breakeven_trades": 0,
                        "total_pnl": 0.0,
                        "trades": []
                    }

                pnl = float(trade_log.profit_loss) if getattr(trade_log, 'profit_loss', None) is not None else 0.0
                if pnl > 0:
                    strategy_trades[strategy_name]["success_trades"] += 1
                    result = "success"
                elif pnl < 0:
                    strategy_trades[strategy_name]["loss_trades"] += 1
                    result = "loss"
                else:
                    strategy_trades[strategy_name]["breakeven_trades"] += 1
                    result = "breakeven"

                strategy_trades[strategy_name]["total_trades"] += 1
                strategy_trades[strategy_name]["total_pnl"] += pnl

                screenshots = getattr(trade_log, 'screenshots', []) or []
                trade_detail = {
                    "id": trade_log.id,
                    "symbol": trade_log.symbol,
                    "entry_price": trade_log.entry_price,
                    "exit_price": trade_log.exit_price,
                    "quantity": trade_log.quantity,
                    "pnl": pnl,
                    "result": result,
                    "screenshot_urls": screenshots
                }
                strategy_trades[strategy_name]["trades"].append(trade_detail)

            result_list = []
            for strategy_data in strategy_trades.values():
                total = strategy_data["total_trades"]
                strategy_data["win_rate"] = round((strategy_data["success_trades"] / total) * 100,
                                                  2) if total > 0 else 0.0
                strategy_data["loss_rate"] = round((strategy_data["loss_trades"] / total) * 100,
                                                   2) if total > 0 else 0.0
                result_list.append(strategy_data)

            result_list.sort(key=lambda x: x["total_trades"], reverse=True)

            total_strategies = len(result_list)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_strategies = result_list[start_idx:end_idx]
            total_pages = (total_strategies + per_page - 1) // per_page

            return {
                'items': paginated_strategies,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_strategies,
                    'pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages,
                    'prev_num': page - 1 if page > 1 else None,
                    'next_num': page + 1 if page < total_pages else None
                }
            }, 200
        except Exception as e:
            return {"error": f"Failed to fetch strategy-wise trades: {str(e)}"}, 500


# ========================
# STATS RESOURCE
# ========================

class TradeLogStatsResource(Resource):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            items = TradeLog.query.filter_by(user_id=user_id).all()

            def get_pnl(tl):
                return float(tl.profit_loss) if getattr(tl, 'profit_loss', None) is not None else 0.0

            success = sum(1 for t in items if get_pnl(t) > 0)
            loss = sum(1 for t in items if get_pnl(t) < 0)
            breakeven = sum(1 for t in items if get_pnl(t) == 0)
            total = len(items)
            total_pnl = sum(get_pnl(t) for t in items)
            win_rate = (success / total) * 100.0 if total else 0.0
            loss_rate = (loss / total) * 100.0 if total else 0.0

            return {
                "counts": {
                    "success": success,
                    "loss": loss,
                    "breakeven": breakeven
                },
                "performance": {
                    "total_trades": total,
                    "win_rate": round(win_rate, 2),
                    "loss_rate": round(loss_rate, 2),
                    "total_pnl": total_pnl
                }
            }, 200
        except Exception as e:
            return {"error": f"Failed to fetch trade log stats: {str(e)}"}, 500


# ========================
# REGISTER RESOURCES
# ========================

def register_resources(api):
    """Register all API resources"""
    print(">>> Registering API resources...")

    # Auth
    api.add_resource(UserRegisterResource, "/api/auth/register")
    api.add_resource(UserLoginResource, "/api/auth/login")
    api.add_resource(UserProfileResource, "/api/auth/profile")
    api.add_resource(UserProfileAvatarResource, "/api/auth/profile/avatar")

    # Strategies
    api.add_resource(StrategyListResource, '/api/strategies')
    api.add_resource(StrategyResource, '/api/strategies/<int:strategy_id>')

    # Analyses
    api.add_resource(AnalysisListResource, '/api/analyses')
    api.add_resource(AnalysisResource, '/api/analyses/<int:analysis_id>')

    # Trades
    api.add_resource(TradeListResource, '/api/trades')
    api.add_resource(TradeResource, '/api/trades/<int:trade_id>')

    # Trade Logs
    api.add_resource(TradeLogListResource, '/api/trade-logs')
    api.add_resource(TradeLogResource, '/api/trade-logs/<int:log_id>')
    api.add_resource(TradeLogStatsResource, '/api/trade-logs/stats')

    # Strategy-wise trades
    api.add_resource(StrategyWiseTradesResource, '/api/strategy-wise-trades')

    print(">>> API resources registered successfully!")
