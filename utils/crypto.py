from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

# This module will hold the global cipher suite instance
cipher_suite = None
# Global state for the local Diffie-Hellman private key
dh_private_key = None

def generate_dh_keys() -> tuple[any, bytes]:
    """
    Generates a new Diffie-Hellman key pair.
    This is the first step for both Host and Joiner.
    It generates the common parameters, a private key, and a public key.
    
    Returns:
        A tuple containing the private key object (to be kept secret) and
        the public key bytes (to be sent to the peer).
    """
    global dh_private_key
    # Generate parameters for the key exchange.
    # In a real-world application, these might be pre-generated and hardcoded
    # for efficiency, but generating them on the fly is also secure.
    # The generator (g) and prime (p) are not secret.
    parameters = dh.generate_parameters(generator=2, key_size=2048)
    
    # Generate our private key. This is SECRET.
    dh_private_key = parameters.generate_private_key()
    
    # Generate our public key. This is meant to be shared.
    public_key_bytes = dh_private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    
    return dh_private_key, public_key_bytes

def establish_secure_channel(peer_public_key_bytes: bytes) -> tuple[bool, str | None]:
    """
    Establishes the final symmetric encryption key using our private key
    and the peer's public key. This is the final step of the DH exchange.

    Args:
        peer_public_key_bytes: The public key received from the peer.

    Returns:
        A tuple (success: bool, error_message: str | None).
    """
    global cipher_suite
    try:
        if dh_private_key is None:
            return False, "Local DH private key is not available. Call generate_dh_keys first."

        # Load the peer's public key from its byte representation.
        peer_public_key = load_pem_public_key(peer_public_key_bytes)

        # Compute the shared secret. This is the magic of Diffie-Hellman.
        # This secret is generated on both sides without ever being transmitted.
        shared_secret = dh_private_key.exchange(peer_public_key)

        # Derive a 32-byte key suitable for Fernet using a standard KDF.
        # A Key Derivation Function (KDF) like HKDF is crucial to turn the
        # shared secret into a cryptographically strong symmetric key.
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'p2p-chat-key-derivation-info', # A fixed, non-secret info string
        ).derive(shared_secret)

        # Initialize the Fernet cipher suite with the newly derived key.
        cipher_suite = Fernet(derived_key)
        return True, None

    except Exception as e:
        cipher_suite = None
        return False, f"Failed to establish secure channel: {e}"


def encrypt_message(message: str) -> bytes:
    """Encrypts a string message using the established channel."""
    if not cipher_suite:
        raise ValueError("Cipher suite not initialized. Key exchange has not completed.")
    return cipher_suite.encrypt(message.encode())

def decrypt_message(encrypted_message: bytes) -> str:
    """Decrypts a byte message using the established channel."""
    if not cipher_suite:
        raise ValueError("Cipher suite not initialized. Key exchange has not completed.")
    return cipher_suite.decrypt(encrypted_message).decode()
