"""Exceptions exposed by the public API."""


class PyGrowUpError(RuntimeError):
    """Base class for package-specific errors."""


class DataError(PyGrowUpError):
    """The bundled reference data are missing or malformed."""


class DataNotFoundError(PyGrowUpError):
    """No applicable reference observations are available."""


class InvalidTableNameError(PyGrowUpError):
    """The requested anthropometric indicator is unknown."""


class InvalidIndexError(PyGrowUpError):
    """The index (age or length/height) is invalid."""


class InvalidAgeError(InvalidIndexError):
    """Age must be a finite, nonnegative number of months."""


class InvalidLengthError(InvalidIndexError):
    """Length/height must be a finite, positive number of centimeters."""


class InvalidSexError(PyGrowUpError):
    """Sex must be M/F or Male/Female."""


class InvalidMeasurement(PyGrowUpError):
    """The measurement must be a finite, positive number."""
