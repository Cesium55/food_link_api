#!/usr/bin/env python3
"""
Utility script to generate RSA key pair for JWT signing.
Generates private and public keys in PEM format.
"""

from pathlib import Path
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_rsa_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
    """
    Generate RSA key pair.
    
    Args:
        key_size: Key size in bits (default: 2048)
    
    Returns:
        Tuple of (private_key_pem, public_key_pem) as bytes
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    # Serialize private key
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_key_pem, public_key_pem


def save_keys(private_key_path: str, public_key_path: str, key_size: int = 2048) -> None:
    """
    Generate and save RSA key pair to files.
    
    Args:
        private_key_path: Path to save private key
        public_key_path: Path to save public key
        key_size: Key size in bits (default: 2048)
    """
    private_key_pem, public_key_pem = generate_rsa_key_pair(key_size)
    
    # Create directories if they don't exist
    Path(private_key_path).parent.mkdir(parents=True, exist_ok=True)
    Path(public_key_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save private key
    with open(private_key_path, "wb") as f:
        f.write(private_key_pem)
    print(f"Private key saved to: {private_key_path}")
    
    # Save public key
    with open(public_key_path, "wb") as f:
        f.write(public_key_pem)
    print(f"Public key saved to: {public_key_path}")
    
    # Set appropriate permissions (Unix only)
    import os
    if os.name != 'nt':  # Not Windows
        os.chmod(private_key_path, 0o600)  # Read/write for owner only
        os.chmod(public_key_path, 0o644)    # Read for all, write for owner


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add src directory to Python path
    script_dir = Path(__file__).parent.parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    from config import settings
    
    # Default paths from config
    private_key_path = settings.jwt_private_key_path
    public_key_path = settings.jwt_public_key_path
    
    # Allow override via command line
    if len(sys.argv) > 1:
        private_key_path = sys.argv[1]
    if len(sys.argv) > 2:
        public_key_path = sys.argv[2]
    
    key_size = 2048
    if len(sys.argv) > 3:
        key_size = int(sys.argv[3])
    
    print(f"Generating RSA key pair (size: {key_size} bits)...")
    save_keys(private_key_path, public_key_path, key_size)
    print("Keys generated successfully!")

