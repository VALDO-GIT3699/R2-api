import json
import time
from urllib.request import urlopen

from jose import jwk, jwt
from jose.utils import base64url_decode

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


def _load_apple_public_keys() -> list[dict]:
    with urlopen(APPLE_KEYS_URL) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("keys", [])


def verify_apple_identity_token(identity_token: str, audience: str) -> dict:
    if not audience:
        raise ValueError("APPLE_AUDIENCE is not configured")

    unverified_header = jwt.get_unverified_header(identity_token)
    key_id = unverified_header.get("kid")

    keys = _load_apple_public_keys()
    key_data = next((key for key in keys if key.get("kid") == key_id), None)
    if not key_data:
        raise ValueError("Unable to find Apple signing key")

    public_key = jwk.construct(key_data)

    message, encoded_signature = identity_token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

    if not public_key.verify(message.encode("utf-8"), decoded_signature):
        raise ValueError("Invalid Apple identity token signature")

    claims = jwt.get_unverified_claims(identity_token)

    if claims.get("iss") != APPLE_ISSUER:
        raise ValueError("Invalid Apple token issuer")

    token_aud = claims.get("aud")
    if token_aud != audience:
        raise ValueError("Invalid Apple token audience")

    token_exp = claims.get("exp")
    if token_exp is None or int(token_exp) < int(time.time()):
        raise ValueError("Apple identity token expired")

    return claims
