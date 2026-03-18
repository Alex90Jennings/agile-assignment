"""
Central validation helpers shared across blueprints.
"""

import string


def validate_password(password: str) -> list:
    """Validate a password against the application's policy.

    Policy:
    - Minimum 8 characters
    - At least one letter
    - At least one number
    - At least one special character (punctuation)

    Returns a list of human-readable error strings.
    An empty list means the password is valid.
    """
    if not password:
        return ['Password is required.']

    errors = []

    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if not any(c.isalpha() for c in password):
        errors.append('Password must include at least one letter.')
    if not any(c.isdigit() for c in password):
        errors.append('Password must include at least one number.')
    if not any(c in string.punctuation for c in password):
        errors.append('Password must include at least one special character (e.g. ! @ # $ %).')

    return errors
