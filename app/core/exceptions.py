class AppError(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AddressNotFoundError(AppError):
    def __init__(self, message: str = "Address not found."):
        super().__init__(message, status_code=404)


class AddressDeactivatedError(AppError):
    def __init__(self, message: str = "This address is currently unavailable."):
        super().__init__(message, status_code=410)


class AddressPrivateError(AppError):
    def __init__(self, message: str = "This address is private."):
        super().__init__(message, status_code=403)


class RateLimitExceededError(AppError):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message, status_code=429)


class AccountLockedError(AppError):
    def __init__(self, message: str = "Account temporarily locked due to too many failed attempts."):
        super().__init__(message, status_code=423)


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid credentials provided."):
        super().__init__(message, status_code=401)


class InvalidEditIdError(AppError):
    def __init__(self, message: str = "Invalid Edit ID provided."):
        super().__init__(message, status_code=401)


class PatternExhaustedError(AppError):
    def __init__(self, message: str = "No Public Address IDs are currently available for this year."):
        super().__init__(message, status_code=503)


class UnsafeDestinationError(AppError):
    def __init__(self, message: str = "Invalid or unsafe destination URL. Only HTTP and HTTPS URLs are permitted."):
        super().__init__(message, status_code=400)
