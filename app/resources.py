# resources/resources.py
import re
from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from .extensions import db, bcrypt
from .models import Strategy, Analysis, Trade, TradeLog, User
from .schemas import StrategySchema, AnalysisSchema, TradeSchema, TradeLogSchema, UserSchema
from sqlalchemy import or_, desc, asc
from datetime import datetime
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
    try:
        folder_path = f"{folder}/user_{user_id}"
        res = cloudinary.uploader.upload(
            file_storage,
            folder=folder_path,
            overwrite=False,
            unique_filename=True,
            use_filename=False,
            resource_type="image"
        )
        url = res.get("secure_url")
        print(f"✅ Image uploaded: {url}")
        return url
    except Exception as e:
        print(f"❌ Cloudinary upload error: {str(e)}")
        return None


def compute_pnl(entry_price, exit_price, quantity, trade_type="Long"):
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
        return (ext - ent) * qty
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


def extract_request_data():
    """
    FIXED: Extract data from either FormData or JSON
    Handles both multipart/form-data and application/json
    """
    has_files = bool(request.files.getlist('images'))
    content_type = request.content_type or ''

    if 'multipart/form-data' in content_type:
        data = {k: v for k, v in request.form.items()}
        print(f"📦 Extracted FormData: {len(data)} fields, Files: {len(request.files)}")
    elif 'application/json' in content_type:
        try:
            data = request.get_json() or {}
            print(f"📦 Extracted JSON: {len(data)} fields")
        except Exception as e:
            print(f"⚠️ JSON parsing failed: {str(e)}")
            data = {}
    else:
        try:
            data = request.get_json() or {}
            print(f"📦 Extracted JSON (fallback): {len(data)} fields")
        except:
            data = {k: v for k, v in request.form.items()}
            print(f"📦 Extracted FormData (fallback): {len(data)} fields")

    return data, has_files


def parse_datetime(date_str):
    """
    FIXED: Parse ISO date string to Python datetime object
    Handles ISO format with timezone and milliseconds
    """
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    if isinstance(date_str, str):
        try:
            if 'T' in date_str:
                date_str = date_str.replace('Z', '').split('.')[0]
                return datetime.fromisoformat(date_str)
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            print(f"⚠️ Date parsing failed for '{date_str}': {str(e)}")
            return None

    return date_str


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
            user = User(email=email, password_hash=pw_hash, first_name=first_name, last_name=last_name)
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
            return {"message": "Profile fetched successfully", "user": user_schema.dump(user)}, 200
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
            return {"message": "Profile updated successfully", "user": user_schema.dump(user)}, 200
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
            data, has_files = extract_request_data()
            data["user_id"] = user_id

            uploaded_files = request.files.getlist('images') if has_files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "strategy")
                    if url:
                        urls.append(url)

            if urls:
                data['images'] = urls

            print(f"📝 Creating Strategy: {data.get('name')}, Files: {len(urls)}")

            s = strategy_schema.load(data)
            db.session.add(s)
            db.session.commit()
            return strategy_schema.dump(s), 201
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating strategy: {str(e)}")
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

            data, has_files = extract_request_data()

            if has_files:
                uploaded_files = request.files.getlist('images')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "strategy")
                        if url:
                            urls.append(url)
                if urls:
                    existing = s.images or []
                    data['images'] = existing + urls

            data.pop('user_id', None)
            data.pop('id', None)
            data.pop('created_at', None)

            for k, v in data.items():
                if hasattr(s, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(s, k, v)
            db.session.commit()
            print(f"✅ Strategy updated: ID={strategy_id}")
            return strategy_schema.dump(s)
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating strategy: {str(e)}")
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
            print(f"❌ Error deleting strategy: {str(e)}")
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
            data, has_files = extract_request_data()
            data["user_id"] = user_id

            uploaded_files = request.files.getlist('images') if has_files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "analysis")
                    if url:
                        urls.append(url)

            if urls:
                data['images'] = urls

            print(f"📝 Creating Analysis: {data.get('symbol')}, Files: {len(urls)}")

            a = analysis_schema.load(data)
            db.session.add(a)
            db.session.commit()
            return analysis_schema.dump(a), 201
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating analysis: {str(e)}")
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

            data, has_files = extract_request_data()

            if has_files:
                uploaded_files = request.files.getlist('images')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "analysis")
                        if url:
                            urls.append(url)
                if urls:
                    existing = a.images or []
                    data['images'] = existing + urls

            data.pop('user_id', None)
            data.pop('id', None)
            data.pop('created_at', None)

            for k, v in data.items():
                if hasattr(a, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(a, k, v)
            db.session.commit()
            print(f"✅ Analysis updated: ID={analysis_id}")
            return analysis_schema.dump(a)
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating analysis: {str(e)}")
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
            print(f"❌ Error deleting analysis: {str(e)}")
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
                images = item.get('images') or []
                item['image_urls'] = images

            return result
        except Exception as e:
            return {"error": f"Failed to fetch trades: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            data, has_files = extract_request_data()

            uploaded_files = request.files.getlist('images') if has_files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "trade")
                    if url:
                        urls.append(url)
            if urls:
                data['images'] = urls

            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key in ['quantity', 'strategy_id']:
                    processed_data[key] = int(value) if value else None
                elif key in ['entry_time', 'exit_time']:
                    processed_data[key] = parse_datetime(value)
                else:
                    processed_data[key] = value

            processed_data["user_id"] = user_id

            required_fields = ['symbol', 'entry_price', 'exit_price', 'quantity', 'entry_reason', 'exit_reason']
            for field in required_fields:
                if not processed_data.get(field):
                    return {"error": f"Missing required field: {field}"}, 400

            print(f"📝 Creating Trade: {processed_data.get('symbol')}, Files: {len(urls)}")

            t = trade_schema.load(processed_data)
            t.profit_loss = compute_pnl(t.entry_price, t.exit_price, t.quantity, t.trade_type)

            db.session.add(t)
            db.session.commit()

            result = trade_schema.dump(t)
            images = result.get('images') or []
            result['image_urls'] = images
            return result, 201
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating trade: {str(e)}")
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
            images = result.get('images') or []
            result['image_urls'] = images
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

            data, has_files = extract_request_data()

            if has_files:
                uploaded_files = request.files.getlist('images')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "trade")
                        if url:
                            urls.append(url)
                if urls:
                    existing = t.images or []
                    data['images'] = existing + urls

            data.pop('user_id', None)
            data.pop('id', None)
            data.pop('created_at', None)

            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    value = float(value) if value else None
                elif key in ['quantity', 'strategy_id']:
                    value = int(value) if value else None
                elif key in ['entry_time', 'exit_time']:
                    value = parse_datetime(value)

                if hasattr(t, key) and key not in ['id', 'user_id', 'created_at']:
                    setattr(t, key, value)

            t.profit_loss = compute_pnl(t.entry_price, t.exit_price, t.quantity, t.trade_type)
            db.session.commit()
            print(f"✅ Trade updated: ID={trade_id}")

            result = trade_schema.dump(t)
            images = result.get('images') or []
            result['image_urls'] = images
            return result
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating trade: {str(e)}")
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
            print(f"❌ Error deleting trade: {str(e)}")
            return {"error": f"Failed to delete trade: {str(e)}"}, 400


# ========================
# TRADE LOG RESOURCES (FIXED)
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
                images = item.get('images') or []
                item['image_urls'] = images

            return result
        except Exception as e:
            return {"error": f"Failed to fetch trade logs: {str(e)}"}, 500

    @jwt_required()
    def post(self):
        """
        FIXED: Create TradeLog using only TradeLog model
        NOT creating Trade object automatically
        """
        user_id = int(get_jwt_identity())
        try:
            data, has_files = extract_request_data()

            # Upload images
            uploaded_files = request.files.getlist('images') if has_files else []
            urls = []
            for f in uploaded_files:
                if f and f.filename and allowed_file(f.filename):
                    url = cloudinary_upload_image(f, user_id, "tradelog")
                    if url:
                        urls.append(url)

            # Process data types
            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key == 'quantity':
                    processed_data[key] = int(value) if value else None
                elif key in ['entry_date', 'exit_date']:
                    processed_data[key] = parse_datetime(value)
                else:
                    processed_data[key] = value

            processed_data["user_id"] = user_id

            # Validation
            required_fields = ['symbol', 'entry_price', 'exit_price', 'quantity', 'entry_date', 'exit_date']
            for field in required_fields:
                if not processed_data.get(field):
                    return {"error": f"Missing required field: {field}"}, 400

            print(f"📝 Creating Trade Log: {processed_data.get('symbol')}, Files: {len(urls)}")

            # FIXED: Create ONLY TradeLog, not Trade
            tl = trade_log_schema.load(processed_data)
            if urls:
                tl.images = urls

            # Calculate P&L
            tl.profit_loss = compute_pnl(tl.entry_price, tl.exit_price, tl.quantity, "Long")

            db.session.add(tl)
            db.session.commit()

            print(f"✅ Trade Log Created: ID {tl.id}")

            result = trade_log_schema.dump(tl)
            images = result.get('images') or []
            result['image_urls'] = images
            return result, 201

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating trade log: {str(e)}")
            import traceback
            traceback.print_exc()
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
            images = result.get('images') or []
            result['image_urls'] = images
            return result
        except Exception as e:
            return {"error": f"Failed to fetch trade log: {str(e)}"}, 500

    @jwt_required()
    def put(self, log_id):
        """
        FIXED: Update TradeLog with proper date parsing
        """
        user_id = int(get_jwt_identity())
        try:
            tl = TradeLog.query.filter_by(id=log_id, user_id=user_id).first()
            if not tl:
                return {"error": "Trade log not found"}, 404

            data, has_files = extract_request_data()

            print(f"📝 Updating Trade Log: ID={log_id}, Has Files: {has_files}")

            # Handle image uploads
            if has_files:
                uploaded_files = request.files.getlist('images')
                urls = []
                for f in uploaded_files:
                    if f and f.filename and allowed_file(f.filename):
                        url = cloudinary_upload_image(f, user_id, "tradelog")
                        if url:
                            urls.append(url)
                if urls:
                    existing = tl.images or []
                    data['images'] = existing + urls
                    print(f"✅ Images uploaded: {len(urls)}, Total: {len(data['images'])}")

            # Remove protected fields
            data.pop('user_id', None)
            data.pop('id', None)
            data.pop('created_at', None)

            # Convert data types and parse dates
            processed_data = {}
            for key, value in data.items():
                if key in ['entry_price', 'exit_price']:
                    processed_data[key] = float(value) if value else None
                elif key == 'quantity':
                    processed_data[key] = int(value) if value else None
                elif key in ['entry_date', 'exit_date']:
                    processed_data[key] = parse_datetime(value)
                    print(f"   ✓ Parsed {key}: {value} -> {processed_data[key]}")
                else:
                    processed_data[key] = value

            # Update fields
            for k, v in processed_data.items():
                if hasattr(tl, k) and k not in ['id', 'user_id', 'created_at']:
                    setattr(tl, k, v)
                    print(f"   ✓ Set {k}: {v}")

            # Calculate P&L
            tl.profit_loss = compute_pnl(tl.entry_price, tl.exit_price, tl.quantity, "Long")
            print(f"💰 Trade Log P&L calculated: {tl.profit_loss}")

            db.session.commit()
            print(f"✅ Trade Log updated successfully: ID={log_id}")

            result = trade_log_schema.dump(tl)
            images = result.get('images') or []
            result['image_urls'] = images
            return result

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating trade log: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to update trade log: {str(e)}"}, 400

    @jwt_required()
    def delete(self, log_id):
        user_id = int(get_jwt_identity())
        try:
            tl = TradeLog.query.filter_by(id=log_id, user_id=user_id).first()
            if not tl:
                return {"error": "Trade log not found"}, 404

            db.session.delete(tl)
            db.session.commit()
            return {"message": "Trade log deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting trade log: {str(e)}")
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

                images = getattr(trade_log, 'images', []) or []
                trade_detail = {
                    "id": trade_log.id,
                    "symbol": trade_log.symbol,
                    "entry_price": trade_log.entry_price,
                    "exit_price": trade_log.exit_price,
                    "quantity": trade_log.quantity,
                    "pnl": pnl,
                    "result": result,
                    "image_urls": images
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
            print(f"❌ Error fetching strategy-wise trades: {str(e)}")
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
            print(f"❌ Error fetching stats: {str(e)}")
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

    # Strategies
    api.add_resource(StrategyListResource, '/api/strategies')
    api.add_resource(StrategyResource, '/api/strategies/<int:strategy_id>')

    # Analyses
    api.add_resource(AnalysisListResource, '/api/analyses')
    api.add_resource(AnalysisResource, '/api/analyses/<int:analysis_id>')

    # Trades
    api.add_resource(TradeListResource, '/api/trades')
    api.add_resource(TradeResource, '/api/trades/<int:trade_id>')

    # Trade Logs - FIXED
    api.add_resource(TradeLogListResource, '/api/trade-logs')
    api.add_resource(TradeLogResource, '/api/trade-logs/<int:log_id>')
    api.add_resource(TradeLogStatsResource, '/api/trade-logs/stats')

    # Strategy-wise trades
    api.add_resource(StrategyWiseTradesResource, '/api/strategy-wise-trades')

    print(">>> API resources registered successfully!")
