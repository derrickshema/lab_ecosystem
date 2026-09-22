from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,       # iterations
    argon2__memory_cost=65536, # 64 MiB
    argon2__parallelism=4,
)

def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def needs_rehash(hashed_password: str) -> bool:
    """Check if a hash needs upgrading (e.g. after increasing work factors)."""
    return pwd_context.needs_update(hashed_password)