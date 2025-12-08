from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, messaging
from logger import get_sync_logger
from pathlib import Path

logger = get_sync_logger(__name__)

# Initialize Firebase Admin SDK (singleton pattern)
_firebase_app: Optional[firebase_admin.App] = None


def _initialize_firebase_app(credential_path: str = "keys/firebase-key.json") -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK with service account credentials
    
    Args:
        credential_path: Path to Firebase service account key JSON file
        
    Returns:
        Initialized Firebase App instance
    """
    global _firebase_app
    
    if _firebase_app is None:
        credential_file = Path(credential_path)
        if not credential_file.exists():
            raise FileNotFoundError(f"Firebase credential file not found at {credential_path}")
        
        cred = credentials.Certificate(str(credential_file))
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    
    return _firebase_app


class FirebaseNotificationManager:
    """Manager for sending push notifications via Firebase Cloud Messaging (FCM)"""
    
    def __init__(self, credential_path: str = "keys/firebase-key.json"):
        """
        Initialize Firebase Notification Manager
        
        Args:
            credential_path: Path to Firebase service account key JSON file
        """
        self.credential_path = credential_path
        _initialize_firebase_app(credential_path)
    
    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> str:
        """
        Send push notification to a device using FCM token
        
        Args:
            token: FCM registration token of the target device
            title: Notification title
            body: Notification body text
            data: Optional dictionary of custom data to send with notification
            image_url: Optional URL of image to display in notification
            
        Returns:
            Message ID from Firebase
            
        Raises:
            ValueError: If token is invalid or expired
            Exception: If notification sending fails
        """
        try:
            # Build notification payload
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build message
            message = messaging.Message(
                notification=notification,
                token=token,
                data=data or {}
            )
            
            logger.info(
                "Sending FCM notification",
                extra={
                    "token": token[:20] + "...",  # Log only first 20 chars for security
                    "title": title
                }
            )
            
            # Send message
            response = messaging.send(message)
            
            logger.info(
                "FCM notification sent successfully",
                extra={
                    "message_id": response,
                    "title": title
                }
            )
            
            return response
            
        except messaging.UnregisteredError:
            logger.warning(
                "FCM token is invalid or unregistered",
                extra={"token": token[:20] + "..."}
            )
            raise ValueError("Invalid or expired FCM token")
        except Exception as e:
            # Check for SenderIdMismatchError and other token-related errors
            error_type = type(e).__name__
            error_message = str(e)
            
            # Handle SenderIdMismatchError (token from different Firebase project)
            if "SenderId" in error_type or "SenderId" in error_message or "sender-id" in error_message.lower():
                logger.warning(
                    "FCM token has SenderId mismatch (token from different Firebase project)",
                    extra={"token": token[:20] + "...", "error_type": error_type}
                )
                raise ValueError("Invalid FCM token: SenderId mismatch")
            
            # Handle other token-related errors
            if "token" in error_message.lower() and ("invalid" in error_message.lower() or "expired" in error_message.lower()):
                logger.warning(
                    f"FCM token error: {error_message}",
                    extra={"token": token[:20] + "...", "error_type": error_type}
                )
                raise ValueError(f"Invalid FCM token: {error_message}")
            
            # Handle ValueError/TypeError from Firebase (invalid arguments)
            if isinstance(e, (ValueError, TypeError)):
                logger.error(
                    f"Invalid argument for FCM notification: {error_message}",
                    extra={"token": token[:20] + "...", "error_type": error_type}
                )
                raise ValueError(f"Invalid notification parameters: {error_message}")
            
            # Log and re-raise other exceptions
            logger.error(
                f"Error sending FCM notification: {error_message}",
                extra={"token": token[:20] + "...", "error_type": error_type}
            )
            raise
    
    async def send_multicast_notification(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> messaging.BatchResponse:
        """
        Send push notification to multiple devices
        
        Args:
            tokens: List of FCM registration tokens
            title: Notification title
            body: Notification body text
            data: Optional dictionary of custom data to send with notification
            image_url: Optional URL of image to display in notification
            
        Returns:
            BatchResponse containing success/failure information for each token
        """
        if not tokens:
            raise ValueError("Tokens list cannot be empty")
        
        try:
            # Build notification payload
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build multicast message
            message = messaging.MulticastMessage(
                notification=notification,
                tokens=tokens,
                data=data or {}
            )
            
            logger.info(
                "Sending FCM multicast notification",
                extra={
                    "token_count": len(tokens),
                    "title": title
                }
            )
            
            # Send message using send_each_for_multicast (send_multicast was deprecated)
            response = messaging.send_each_for_multicast(message)
            
            logger.info(
                "FCM multicast notification sent",
                extra={
                    "success_count": response.success_count,
                    "failure_count": response.failure_count,
                    "title": title
                }
            )
            
            # Log failures if any
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        exception = resp.exception
                        if exception:
                            # Check exception type directly
                            if isinstance(exception, messaging.UnregisteredError):
                                logger.warning(
                                    f"Token {idx} is invalid or unregistered",
                                    extra={"token": tokens[idx][:20] + "..."}
                                )
                            else:
                                logger.error(
                                    f"Failed to send to token {idx}: {str(exception)}",
                                    extra={"token": tokens[idx][:20] + "..."}
                                )
                        else:
                            logger.error(
                                f"Failed to send to token {idx}: Unknown error",
                                extra={"token": tokens[idx][:20] + "..."}
                            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"Error sending FCM multicast notification: {str(e)}",
                extra={"token_count": len(tokens)}
            )
            raise


def create_firebase_notification_manager(
    credential_path: str = "keys/firebase-key.json"
) -> FirebaseNotificationManager:
    """
    Create a FirebaseNotificationManager instance
    
    Args:
        credential_path: Path to Firebase service account key JSON file
        
    Returns:
        FirebaseNotificationManager instance
    """
    return FirebaseNotificationManager(credential_path)

