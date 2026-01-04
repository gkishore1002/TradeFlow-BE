# app/notification_service.py
from .extensions import db, socketio
from .models import Notification


class NotificationService:
    """Service for creating and managing notifications"""

    @staticmethod
    def create_notification(user_id, title, message, notification_type="system", link=None, data=None):
        """Create a new notification"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                link=link,
                data=data
            )
            db.session.add(notification)
            db.session.commit()

            # Emit via SocketIO
            try:
                socketio.emit('new_notification', notification.to_dict(), room=f'user_{user_id}')
            except Exception as socket_error:
                print(f"⚠️ SocketIO emit failed: {str(socket_error)}")

            print(f"✅ Notification created: {title}")
            return notification
        except Exception as e:
            db.session.rollback()
            print(f"❌ Notification creation failed: {str(e)}")
            return None

    @staticmethod
    def notify_new_strategy(user_id, strategy):
        """Send notification for new strategy"""
        return NotificationService.create_notification(
            user_id=user_id,
            title="New Strategy Created 📝",
            message=f"Strategy '{strategy.name}' has been created successfully.",
            notification_type="strategy",
            link=f"/strategies/{strategy.id}",
            data={"strategy_id": strategy.id}
        )

    @staticmethod
    def notify_new_analysis(user_id, analysis):
        """Send notification for new analysis"""
        return NotificationService.create_notification(
            user_id=user_id,
            title="New Analysis Created 📊",
            message=f"Analysis for {analysis.symbol} has been created.",
            notification_type="analysis",
            link=f"/analysis/{analysis.id}",
            data={"analysis_id": analysis.id, "symbol": analysis.symbol}
        )

    @staticmethod
    def notify_new_trade(user_id, trade):
        """Send notification for new trade"""
        pnl = trade.profit_loss or 0
        emoji = "📈" if pnl > 0 else "📉"

        return NotificationService.create_notification(
            user_id=user_id,
            title=f"Trade {'Profit' if pnl > 0 else 'Loss'} {emoji}",
            message=f"Trade for {trade.symbol} recorded with P&L: ${pnl:.2f}",
            notification_type="trade",
            link=f"/trades/{trade.id}",
            data={"trade_id": trade.id, "symbol": trade.symbol, "pnl": pnl}
        )

    @staticmethod
    def notify_new_trade_log(user_id, trade_log):
        """Send notification for new trade log"""
        pnl = trade_log.profit_loss or 0
        emoji = "✅" if pnl > 0 else "❌"

        return NotificationService.create_notification(
            user_id=user_id,
            title=f"Trade Log {('Profit' if pnl > 0 else 'Loss')} {emoji}",
            message=f"Trade log for {trade_log.symbol} recorded with P&L: ${pnl:.2f}",
            notification_type="trade",
            link=f"/trade-logs/{trade_log.id}",
            data={"trade_log_id": trade_log.id, "symbol": trade_log.symbol, "pnl": pnl}
        )
