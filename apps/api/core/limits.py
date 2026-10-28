"""Named size, count and rate limits for the API. Tests mirror these constants."""

# Registration attempts allowed per client IP (DRF rate string).
REGISTER_RATE = "10/hour"

# Sign-in attempts allowed per client IP, and per submitted email (DRF rate strings).
LOGIN_RATE = "30/hour"
LOGIN_EMAIL_RATE = "10/hour"

# Password reset requests and confirmations allowed per client IP (each counted separately).
RESET_RATE = "10/hour"

# Account deletion attempts allowed per client IP and per signed-in user (each counted separately).
ACCOUNT_DELETE_RATE = "10/hour"

# Password reset links expire after this many seconds (Django PASSWORD_RESET_TIMEOUT).
RESET_TIMEOUT_SECONDS = 60 * 60

# Password policy (Django's MinimumLengthValidator uses PASSWORD_MIN_LENGTH).
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

# Email doubles as the username, so it must fit Django's username column.
EMAIL_MAX_LENGTH = 150
