# app/notification_resources.py
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from .extensions import db
from .models import Notification, User
from .schemas import NotificationSchema
from .notification_service import NotificationService

notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)


class NotificationListResource(Resource):
    """Get all notifications for current user"""

    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            unread_only = request.args.get('unread_only', 'false').lower() == 'true'

            query = Notification.query.filter_by(user_id=user_id)

            if unread_only:
                query = query.filter_by(is_read=False)

            query = query.order_by(Notification.created_at.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                'items': notifications_schema.dump(pagination.items),
                'pagination': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next
                }
            }, 200
        except Exception as e:
            print(f"❌ Error fetching notifications: {str(e)}")
            return {"error": f"Failed to fetch notifications: {str(e)}"}, 500


class NotificationResource(Resource):
    """Single notification operations"""

    @jwt_required()
    def get(self, notification_id):
        """Get single notification"""
        user_id = int(get_jwt_identity())
        try:
            notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
            if not notification:
                return {"error": "Notification not found"}, 404

            return notification_schema.dump(notification), 200
        except Exception as e:
            print(f"❌ Error fetching notification: {str(e)}")
            return {"error": str(e)}, 500

    @jwt_required()
    def put(self, notification_id):
        """Mark notification as read"""
        user_id = int(get_jwt_identity())
        try:
            notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
            if not notification:
                return {"error": "Notification not found"}, 404

            notification.is_read = True
            db.session.commit()

            return notification_schema.dump(notification), 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating notification: {str(e)}")
            return {"error": str(e)}, 500

    @jwt_required()
    def delete(self, notification_id):
        """Delete notification"""
        user_id = int(get_jwt_identity())
        try:
            notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
            if not notification:
                return {"error": "Notification not found"}, 404

            db.session.delete(notification)
            db.session.commit()

            return {"message": "Notification deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting notification: {str(e)}")
            return {"error": str(e)}, 500


class MarkAllReadResource(Resource):
    """Mark all notifications as read"""

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            updated = Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
            db.session.commit()

            return {"message": f"{updated} notifications marked as read"}, 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error marking all read: {str(e)}")
            return {"error": str(e)}, 500


class UnreadCountResource(Resource):
    """Get unread notification count"""

    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        try:
            count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
            return {"unread_count": count}, 200
        except Exception as e:
            print(f"❌ Error fetching unread count: {str(e)}")
            return {"error": str(e)}, 500


class PushSubscriptionResource(Resource):
    """Subscribe to push notifications"""

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            data = request.get_json()
            subscription = data.get('subscription')

            if not subscription:
                return {"error": "Subscription data is required"}, 400

            user = User.query.get(user_id)
            if not user:
                return {"error": "User not found"}, 404

            user.push_subscription = subscription
            db.session.commit()

            return {"message": "Successfully subscribed to push notifications"}, 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error subscribing to push: {str(e)}")
            return {"error": str(e)}, 500

    @jwt_required()
    def delete(self):
        """Unsubscribe from push notifications"""
        user_id = int(get_jwt_identity())
        try:
            user = User.query.get(user_id)
            if not user:
                return {"error": "User not found"}, 404

            user.push_subscription = None
            db.session.commit()

            return {"message": "Successfully unsubscribed from push notifications"}, 200
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error unsubscribing from push: {str(e)}")
            return {"error": str(e)}, 500


class TestNotificationResource(Resource):
    """Create a test notification"""

    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        try:
            notification = NotificationService.create_notification(
                user_id=user_id,
                title="Test Notification 🧪",
                message="This is a test notification from the backend!",
                notification_type="system",
                link="/dashboard"
            )

            if notification:
                return notification_schema.dump(notification), 201
            else:
                return {"error": "Failed to create test notification"}, 500
        except Exception as e:
            print(f"❌ Error creating test notification: {str(e)}")
            return {"error": str(e)}, 500
