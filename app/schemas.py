from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import fields
from .models import Strategy, Analysis, Trade, TradeLog, User


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
    created_at = fields.DateTime()
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
# Strategy Schema
# ---------------------------
class StrategySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Strategy
        load_instance = True
        include_fk = True


# ---------------------------
# Analysis Schema
# ---------------------------
class AnalysisSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Analysis
        load_instance = True
        include_fk = True


# ---------------------------
# Trade Schema
# ---------------------------
class TradeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Trade
        load_instance = True
        include_fk = True


# ---------------------------
# TradeLog Schema
# ---------------------------
class TradeLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TradeLog
        load_instance = True
        include_fk = True
