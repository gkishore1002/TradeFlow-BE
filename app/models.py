from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON
from .extensions import db
from sqlalchemy import Enum


# ---------------------------
# Timestamp Mixin
# ---------------------------
class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------
# User Model
# ---------------------------
class User(db.Model, TimestampMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)

    # Profile fields
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)  # Cloudinary URL
    location = db.Column(db.String(120), nullable=True)

    # Relationships
    strategies = db.relationship('Strategy', backref='user', lazy=True, cascade="all, delete-orphan")
    analyses = db.relationship('Analysis', backref='user', lazy=True, cascade="all, delete-orphan")
    trades = db.relationship('Trade', backref='user', lazy=True, cascade="all, delete-orphan")
    trade_logs = db.relationship('TradeLog', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.email}>'


# ---------------------------
# Strategy Model - WITH IMAGES
# ---------------------------
class Strategy(db.Model, TimestampMixin):
    __tablename__ = 'strategies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    name = db.Column(db.String(128), nullable=False)
    category = db.Column(
        Enum("Momentum Trading", "Swing Trading", "Scalping", "Mean Reversion", "Breakout", name="strategy_category"),
        nullable=False
    )
    risk_level = db.Column(
        Enum("Low Risk", "Medium Risk", "High Risk", name="strategy_risk_level"),
        nullable=False
    )
    timeframe = db.Column(
        Enum("Intraday (1 day)", "Swing (days-weeks)", "Position (weeks-months)", "Long Term (months-years)",
             name="strategy_timeframe"),
        nullable=False
    )
    description = db.Column(db.Text)
    trading_rules = db.Column(db.Text)
    additional_notes = db.Column(db.Text)

    # Multiple images for strategy documentation
    images = db.Column(JSON, default=[], nullable=False, server_default='[]')  # Array of image URLs

    # Relationships
    analyses = db.relationship('Analysis', backref='strategy', lazy=True, cascade="all, delete-orphan")
    trades = db.relationship('Trade', backref='strategy', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Strategy {self.name}>'


# ---------------------------
# Analysis Model - WITH IMAGES
# ---------------------------
class Analysis(db.Model, TimestampMixin):
    __tablename__ = 'analyses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=True)

    symbol = db.Column(db.String(64), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)

    trade_type = db.Column(
        Enum("Long", "Short", name="analysis_trade_type"),
        nullable=False
    )
    confidence_level = db.Column(
        Enum("Low", "Medium", "High", name="analysis_confidence_level"),
        nullable=False
    )
    timeframe = db.Column(
        Enum("Intraday", "Swing", "Position", "Long Term", name="analysis_timeframe"),
        nullable=False
    )
    strategy_name = db.Column(db.String(128))
    technical_analysis = db.Column(db.Text, nullable=False)
    fundamental_analysis = db.Column(db.Text)
    additional_notes = db.Column(db.Text)

    # Multiple images for technical/fundamental analysis charts
    images = db.Column(JSON, default=[], nullable=False,
                       server_default='[]')  # Array of image URLs (charts, patterns, etc.)

    def __repr__(self):
        return f'<Analysis {self.symbol}>'


# ---------------------------
# Trade Model - WITH IMAGES
# ---------------------------
class Trade(db.Model, TimestampMixin):
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=True)

    symbol = db.Column(db.String(64), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)

    trade_type = db.Column(
        Enum("Long", "Short", name="trade_type"),
        nullable=False
    )
    strategy_used = db.Column(db.String(128))
    entry_reason = db.Column(db.Text, nullable=False)
    exit_reason = db.Column(db.Text, nullable=False)
    emotions = db.Column(db.Text)
    lessons_learned = db.Column(db.Text)
    tags = db.Column(db.Text)
    profit_loss = db.Column(db.Float)
    notes = db.Column(db.Text)

    images = db.Column(JSON, default=[], nullable=False,
                       server_default='[]')  # Array of image URLs (entry/exit charts, evidence, etc.)

    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)

    # Relationships
    logs = db.relationship('TradeLog', backref='trade', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Trade {self.symbol}>'


# ---------------------------
# TradeLog Model - WITH IMAGES
# ---------------------------
class TradeLog(db.Model, TimestampMixin):
    __tablename__ = 'trade_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    trade_id = db.Column(db.Integer, db.ForeignKey('trades.id'), nullable=True)

    symbol = db.Column(db.String(64), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    entry_date = db.Column(db.DateTime, nullable=False)
    exit_date = db.Column(db.DateTime)
    trading_strategy = db.Column(db.String(128))
    trade_notes = db.Column(db.Text)
    profit_loss = db.Column(db.Float)

    images = db.Column(JSON, default=[], nullable=False,
                       server_default='[]')  # Array of image URLs (trade evidence, charts, etc.)

    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=True)

    # Relationships:
    strategy = db.relationship('Strategy', lazy='joined')

    def __repr__(self):
        return f'<TradeLog {self.symbol}>'
