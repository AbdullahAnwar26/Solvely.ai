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

# Lessons created per signed-in user (DRF rate string).
LESSON_CREATE_RATE = "60/hour"

# Lesson title length (characters).
LESSON_TITLE_MAX_LENGTH = 120

# --- Board revisions and payloads (Story 2.3) ---

# Board saves allowed per signed-in user (DRF rate string). Autosave fires about 1.5 s after the
# last edit, so a busy Learner stays far below this.
BOARD_SAVE_RATE = "120/min"

# Revisions kept per Lesson; older rows are pruned after each successful save.
BOARD_REVISIONS_KEPT = 50

# The only Board payload schema version accepted.
BOARD_SCHEMA_VERSION = 1

# Whole PUT body size (bytes); larger bodies are refused with 413 before parsing.
BOARD_MAX_BODY_BYTES = 2 * 1024 * 1024

# Elements per Board.
BOARD_MAX_ELEMENTS = 5000

# Element id length (characters).
BOARD_ELEMENT_ID_MAX_LENGTH = 64

# Text content of a text element (`text`, `originalText`), in characters.
BOARD_TEXT_MAX_LENGTH = 20000

# Element `link` length (characters).
BOARD_LINK_MAX_LENGTH = 2048

# Any other string inside an element (colours, ids, font names, custom data).
BOARD_STRING_MAX_LENGTH = 256

# Items in any list inside an element (freehand `points`, `pressures`, `groupIds`, ...).
BOARD_ELEMENT_LIST_MAX = 20000

# Keys per object inside an element.
BOARD_ELEMENT_MAX_KEYS = 64

# Nesting depth of values inside an element (the element itself is depth 1).
BOARD_ELEMENT_MAX_DEPTH = 5

# |x|, |y|, |width| and |height| of an element, in scene units.
BOARD_COORDINATE_LIMIT = 1_000_000

# Any other number inside an element (timestamps, seeds and nonces stay well below this).
BOARD_NUMBER_ABS_MAX = 10**15

# Element types the Board accepts (a closed Excalidraw subset: no images or embeds).
BOARD_ELEMENT_TYPES = frozenset(
    {"rectangle", "diamond", "ellipse", "arrow", "line", "freedraw", "text", "frame"}
)

# Who made an element (AD-3).
BOARD_ORIGINS = frozenset({"learner", "ai"})

# Board view settings: zoom bounds (match the web app's clamp) and background colour length.
BOARD_ZOOM_MIN = 0.1
BOARD_ZOOM_MAX = 30
BOARD_BACKGROUND_MAX_LENGTH = 32

# --- AI provider calls (Story 3.1, AD-7) ---

# Provider calls per generation, including the first one.
AI_MAX_ATTEMPTS = 3

# A `provider_invalid_output` (empty, non-JSON, blocked, truncated) is retried at most this often.
AI_MAX_INVALID_OUTPUT_RETRIES = 1

# HTTP timeout of a single provider call (seconds); never longer than what is left of the
# overall deadline.
AI_CALL_TIMEOUT_SECONDS = 30

# Overall deadline for one generation, across all attempts and backoff sleeps (seconds).
AI_TOTAL_TIMEOUT_SECONDS = 60

# Concurrent provider calls per process (a BoundedSemaphore) and how long a call may wait for a
# free slot before failing with `provider_overloaded` (seconds).
AI_MAX_CONCURRENCY = 4
AI_CONCURRENCY_WAIT_SECONDS = 0.5

# Exponential backoff between retries: base * 2^(attempt - 1), capped, with jitter (seconds).
AI_BACKOFF_BASE_SECONDS = 1.0
AI_BACKOFF_MAX_SECONDS = 8.0

# --- Versioned lesson output (Story 3.2) ---

# Provider output is bounded independently of Board persistence limits.
LESSON_SCHEMA_VERSION = 1
LESSON_STEP_DESCRIPTION_MAX_LENGTH = 2000
LESSON_STEP_ALT_MAX_LENGTH = 2000
LESSON_MAX_OPERATIONS = 100
LESSON_MAX_TARGETS = 100
LESSON_PROVISIONAL_ID_MAX_LENGTH = 64
LESSON_MAX_ADDED_ELEMENTS = 100
LESSON_ELEMENT_TEXT_MAX_LENGTH = BOARD_TEXT_MAX_LENGTH
LESSON_PROVIDER_ELEMENT_TYPES = frozenset(
    {"rectangle", "diamond", "ellipse", "arrow", "line", "freedraw", "text"}
)
