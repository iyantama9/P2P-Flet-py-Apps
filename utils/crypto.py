import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    load_pem_parameters,
    Encoding,
    PublicFormat,
    ParameterFormat
)

cipher_suite = None
dh_private_key = None

PARAMS_PATH = "dh_params.pem"

def get_dh_parameters() -> dh.DHParameters:
    """
    Loads DH parameters from file if it exists, otherwise generates and saves them.
    """
    if os.path.exists(PARAMS_PATH):
        with open(PARAMS_PATH, "rb") as f:
            return load_pem_parameters(f.read())
    else:
        print(f"First time setup: Generating DH parameters (this may take a moment)...")
        params = dh.generate_parameters(generator=2, key_size=2048)
        pem_data = params.parameter_bytes(Encoding.PEM, ParameterFormat.PKCS3)
        with open(PARAMS_PATH, "wb") as f:
            f.write(pem_data)
        print("DH parameters saved to dh_params.pem")
        return params

parameters = get_dh_parameters()

def generate_dh_keys() -> tuple[dh.DHPrivateKey, bytes]:
    """
    Generates a private key for the DH key exchange and the corresponding public key.
    """
    global dh_private_key
    dh_private_key = parameters.generate_private_key()
    public_key_bytes = dh_private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    return dh_private_key, public_key_bytes

def establish_secure_channel(peer_public_key_bytes: bytes) -> tuple[bool, str | None]:
    """
    Establishes the final symmetric encryption key using our private key and the peer's public key.
    """
    global cipher_suite
    try:
        if dh_private_key is None:
            return False, "Local DH private key is not available."

        peer_public_key = load_pem_public_key(peer_public_key_bytes)
        shared_secret = dh_private_key.exchange(peer_public_key)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'p2p-chat-key',
        ).derive(shared_secret)

        cipher_suite = AESGCM(derived_key)
        return True, None
    except Exception as e:
        return False, f"Error computing shared key: {e}"

def encrypt_message(message: str) -> bytes | None:
    """Encrypts a message using the established secure channel."""
    if not cipher_suite:
        return None
    nonce = os.urandom(12)
    ciphertext = cipher_suite.encrypt(nonce, message.encode('utf-8'), None)
    return nonce + ciphertext

def decrypt_message(encrypted_message: bytes) -> str | None:
    """Decrypts a message using the established secure channel."""
    if not cipher_suite:
        return None
    try:
        nonce = encrypted_message[:12]
        ciphertext = encrypted_message[12:]
        decrypted_bytes = cipher_suite.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode('utf-8')
    except Exception:
        return None
