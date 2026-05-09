import bcrypt


def hash_password(plain: str) -> str:
    data = plain.encode("utf-8")
    if len(data) > 72:
        data = data[:72]
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        data = plain.encode("utf-8")
        if len(data) > 72:
            data = data[:72]
        return bcrypt.checkpw(data, hashed.encode("ascii"))
    except ValueError:
        return False
