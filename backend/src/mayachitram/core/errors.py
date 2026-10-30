class MayaChitramError(Exception):
    """Base error for MayaChitram domain exceptions."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ImageValidationError(MayaChitramError):
    """Uploaded file is not an acceptable image or violates size/dimension constraints."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message, status_code=status_code)


class OperationError(MayaChitramError):
    """An image processing or tool execution operation failed."""

    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message, status_code=status_code)


class NotFoundError(MayaChitramError):
    """Requested resource (project, asset, tool, version) was not found."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class StorageError(MayaChitramError):
    """Storage read, write, or cleanup error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


class ProviderNotConfiguredError(MayaChitramError):
    """AI provider credentials or configuration are missing."""

    def __init__(self, message: str = "AI Provider credentials are not configured.") -> None:
        super().__init__(message, status_code=503)


class ProviderAnalysisError(MayaChitramError):
    """AI provider failed to analyze the image or produce a plan."""

    def __init__(self, message: str = "AI provider failed to process the request.") -> None:
        super().__init__(message, status_code=502)
