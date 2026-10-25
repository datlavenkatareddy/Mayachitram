class ImageValidationError(ValueError):
    """Uploaded file is not an acceptable image."""


class ProviderNotConfiguredError(RuntimeError):
    """Vision provider credentials are missing."""


class ProviderAnalysisError(RuntimeError):
    """Vision provider failed to analyze the image."""
