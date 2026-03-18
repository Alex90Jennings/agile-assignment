"""
Unit tests for the centralised password validation helper.
No app context required — pure function tests.
"""

from app.utils.validation import validate_password


class TestValidatePassword:
    def test_valid_password_returns_no_errors(self):
        assert validate_password('Secure1!') == []

    def test_valid_password_various_specials(self):
        for special in '!@#$%^&*()-_=+[]{}|;:,.<>?':
            result = validate_password(f'Password1{special}')
            assert result == [], f'Expected valid with special char: {special!r}'

    def test_empty_string_returns_required_error(self):
        errors = validate_password('')
        assert any('required' in e.lower() for e in errors)

    def test_too_short_returns_length_error(self):
        errors = validate_password('Ab1!')
        assert any('8 characters' in e for e in errors)

    def test_exactly_8_chars_is_valid(self):
        assert validate_password('Abcde1!x') == []

    def test_missing_letter_returns_error(self):
        errors = validate_password('12345678!')
        assert any('letter' in e for e in errors)

    def test_missing_number_returns_error(self):
        errors = validate_password('Password!')
        assert any('number' in e for e in errors)

    def test_missing_special_char_returns_error(self):
        errors = validate_password('Password1')
        assert any('special' in e for e in errors)

    def test_multiple_failures_returns_all_errors(self):
        # 'short' — too short, no number, no special char
        errors = validate_password('short')
        assert len(errors) >= 3

    def test_only_letters_fails_number_and_special(self):
        errors = validate_password('abcdefgh')
        categories = ' '.join(errors).lower()
        assert 'number' in categories
        assert 'special' in categories

    def test_only_numbers_fails_letter_and_special(self):
        errors = validate_password('12345678')
        categories = ' '.join(errors).lower()
        assert 'letter' in categories
        assert 'special' in categories

    def test_password_just_letters_and_numbers_fails_special(self):
        errors = validate_password('Password1')
        assert len(errors) == 1
        assert 'special' in errors[0]

    def test_long_valid_password(self):
        assert validate_password('MyV3ryS3cur3P@ssword!') == []
