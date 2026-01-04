# app/schemas.py
from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import fields
from .models import Strategy, Analysis, Trade, TradeLog, User, Notification


# ---------------------------
# User Schema
# ---------------------------
class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True
        exclude = ('password_hash',)

    email = fields.Email()
    first_name = fields.Str()
    last_name = fields.Str()
    bio = fields.Str(allow_none=True)
    avatar_url = fields.Str(allow_none=True)
    location = fields.Str(allow_none=True)
    push_subscription = fields.Dict(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    # Computed fields
    strategies_count = fields.Integer(dump_only=True)
    trades_count = fields.Integer(dump_only=True)
    analyses_count = fields.Integer(dump_only=True)

    def get_attribute(self, obj, attr, default):
        if attr == 'strategies_count':
            return len(obj.strategies) if obj else 0
        elif attr == 'trades_count':
            return len(obj.trades) if obj else 0
        elif attr == 'analyses_count':
            return len(obj.analyses) if obj else 0
        return super().get_attribute(obj, attr, default)


# ---------------------------
# Notification Schema
# ---------------------------
class NotificationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Notification
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    title = fields.Str(required=True)
    message = fields.Str(required=True)
    type = fields.Str(required=True)
    link = fields.Str(allow_none=True)
    is_read = fields.Boolean()
    data = fields.Dict(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ---------------------------
# Strategy Schema
# ---------------------------
class StrategySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Strategy
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    name = fields.Str(required=True)
    category = fields.Str(required=True)
    risk_level = fields.Str(required=True)
    timeframe = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    trading_rules = fields.Str(allow_none=True)
    additional_notes = fields.Str(allow_none=True)
    images = fields.List(fields.Str(), allow_none=True, dump_default=[])
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ---------------------------
# Analysis Schema
# ---------------------------
class AnalysisSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Analysis
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    strategy_id = fields.Integer(allow_none=True)
    symbol = fields.Str(required=True)
    current_price = fields.Float(required=True)
    entry_price = fields.Float(required=True)
    target_price = fields.Float(required=True)
    stop_loss = fields.Float(required=True)
    quantity = fields.Integer(required=True)
    trade_type = fields.Str(required=True)
    confidence_level = fields.Str(required=True)
    timeframe = fields.Str(required=True)
    strategy_name = fields.Str(allow_none=True)
    technical_analysis = fields.Str(required=True)
    fundamental_analysis = fields.Str(allow_none=True)
    additional_notes = fields.Str(allow_none=True)
    images = fields.List(fields.Str(), allow_none=True, dump_default=[])
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ---------------------------
# Trade Schema
# ---------------------------
class TradeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Trade
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    strategy_id = fields.Integer(allow_none=True)
    symbol = fields.Str(required=True)
    entry_price = fields.Float(required=True)
    exit_price = fields.Float(required=True)
    quantity = fields.Integer(required=True)
    trade_type = fields.Str(required=True)
    strategy_used = fields.Str(allow_none=True)
    entry_reason = fields.Str(required=True)
    exit_reason = fields.Str(required=True)
    emotions = fields.Str(allow_none=True)
    lessons_learned = fields.Str(allow_none=True)
    tags = fields.Str(allow_none=True)
    profit_loss = fields.Float(allow_none=True)
    notes = fields.Str(allow_none=True)
    images = fields.List(fields.Str(), allow_none=True, dump_default=[])
    entry_time = fields.DateTime(allow_none=True)
    exit_time = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# ---------------------------
# TradeLog Schema
# ---------------------------
class TradeLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TradeLog
        load_instance = True
        include_fk = True

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer()
    trade_id = fields.Integer(allow_none=True)
    symbol = fields.Str(required=True)
    entry_price = fields.Float(required=True)
    exit_price = fields.Float(required=True)
    quantity = fields.Integer(required=True)
    entry_date = fields.DateTime(required=True)
    exit_date = fields.DateTime(allow_none=True)
    trading_strategy = fields.Str(allow_none=True)
    trade_notes = fields.Str(allow_none=True)
    profit_loss = fields.Float(allow_none=True)
    images = fields.List(fields.Str(), allow_none=True, dump_default=[])
    strategy_id = fields.Integer(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
