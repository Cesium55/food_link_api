import hashlib
import secrets
import base64


class PasswordUtils:
    """Utilities for password operations"""
    
    def hash_password(self, password: str) -> str:
        """Hash a password with salt"""
        # Generate random salt
        salt = secrets.token_bytes(32)
        
        # Hash password with salt
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        
        # Combine salt and hash
        combined = salt + pwd_hash
        
        # Return base64 encoded string
        return base64.b64encode(combined).decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            # Decode base64
            combined = base64.b64decode(hashed_password.encode('utf-8'))
            
            # Extract salt and hash
            salt = combined[:32]
            stored_hash = combined[32:]
            
            # Hash the provided password with the same salt
            pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
            
            # Compare hashes
            return pwd_hash == stored_hash
        except Exception:
            return False
