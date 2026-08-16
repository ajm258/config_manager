class ConfigurationRationalizerError(Exception):
    """Base exception for expected application errors."""


class ConfigurationError(ConfigurationRationalizerError):
    """Invalid or incomplete tool configuration."""


class InvalidCommandError(ConfigurationRationalizerError):
    """Invalid CLI command or option combination."""


class SnapshotError(ConfigurationRationalizerError):
    """Snapshot creation or verification failure."""


class ParsingError(ConfigurationRationalizerError):
    """Configuration parsing failure."""


class ValidationError(ConfigurationRationalizerError):
    """Candidate or configuration validation failure."""


class PolicyError(ConfigurationRationalizerError):
    """Operation violates a rationalization safety policy."""