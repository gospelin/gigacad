import random
import string


def generate_secret_key(length=32):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    secret_key = "".join(random.choice(alphabet) for _ in range(length))
    return secret_key


if __name__ == "__main__":
    secret_key_value = generate_secret_key()
    print(secret_key_value)
