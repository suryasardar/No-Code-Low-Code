from cryptography.fernet import Fernet
import os
import base64
from typing import Dict, Optional
from dotenv import load_dotenv
load_dotenv()


class EncryptionService:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_SECRET_KEY")
        if not self.key:
            raise ValueError("ENCRYPTION_SECRET_KEY environment variable is required")
        
        try:
            # Ensure the key is properly formatted
            if isinstance(self.key, str):
                self.key = self.key.encode()
            self.cipher = Fernet(self.key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key"""
        if not api_key:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(api_key.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to encrypt API key: {e}")
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key"""
        if not encrypted_key:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_key.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt API key: {e}")
    
    def encrypt_api_keys_dict(self, api_keys: Dict[str, str]) -> Dict[str, str]:
        """Encrypt a dictionary of API keys"""
        encrypted_keys = {}
        for key_type, api_key in api_keys.items():
            if api_key:  # Only encrypt non-empty keys
                encrypted_keys[key_type] = self.encrypt_api_key(api_key)
        return encrypted_keys
    
    def decrypt_api_keys_dict(self, encrypted_keys: Dict[str, str]) -> Dict[str, str]:
        """Decrypt a dictionary of API keys"""
        decrypted_keys = {}
        for key_type, encrypted_key in encrypted_keys.items():
            if encrypted_key:  # Only decrypt non-empty keys
                decrypted_keys[key_type] = self.decrypt_api_key(encrypted_key)
        return decrypted_keys

# Global instance
encryption_service = EncryptionService()

def get_encryption_service() -> EncryptionService:
    """Get encryption service instance"""
    return encryption_service

# Utility functions
def encrypt_api_key(api_key: str) -> str:
    """Utility function to encrypt an API key"""
    return encryption_service.encrypt_api_key(api_key)

def decrypt_api_key(encrypted_key: str) -> str:
    """Utility function to decrypt an API key"""
    return encryption_service.decrypt_api_key(encrypted_key)

def encrypt_api_keys_dict(api_keys: Dict[str, str]) -> Dict[str, str]:
    """Utility function to encrypt API keys dictionary"""
    return encryption_service.encrypt_api_keys_dict(api_keys)

def decrypt_api_keys_dict(encrypted_keys: Dict[str, str]) -> Dict[str, str]:
    """Utility function to decrypt API keys dictionary"""
    return encryption_service.decrypt_api_keys_dict(encrypted_keys)

# Key generation utility (for setup)
def generate_encryption_key() -> str:
    """Generate a new encryption key (for initial setup)"""
    return Fernet.generate_key().decode()

if __name__ == "__main__":
    # For testing purposes
    print("Generated encryption key:", generate_encryption_key())