"""
CustomPathsValidator for settings_screen.py

Add this class after the PortNumber validator in:
src/openclaw_dash/screens/settings_screen.py

Then add to the Input widget:
    yield Input(
        value="",
        id="setting-custom-model-paths",
        placeholder="comma-separated paths",
        validators=[CustomPathsValidator()],  # ADD THIS LINE
    )
"""

class CustomPathsValidator(Validator):
    """Validates custom model paths for security."""

    # Dangerous path patterns that should be rejected
    DANGEROUS_PATTERNS = [
        "../",
        "/..",
        "~root",
        "/etc",
        "/sys",
        "/proc",
        "/dev",
        "/boot",
        "C:\\Windows",
        "C:\\Program Files",
    ]

    def validate(self, value: str) -> ValidationResult:
        """Validate custom paths input for security.
        
        Checks:
        - Path length (<500 chars per path)
        - No dangerous patterns
        - Paths are absolute or under home directory
        """
        if not value or not value.strip():
            return self.success()

        # Parse comma-separated paths
        paths = [p.strip() for p in value.split(",") if p.strip()]

        for path_str in paths:
            # Check path length
            if len(path_str) > 500:
                return self.failure(f"Path too long (max 500 chars): {path_str[:50]}...")

            # Check for dangerous patterns
            path_lower = path_str.lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern in path_lower:
                    return self.failure(f"Dangerous path pattern detected: {pattern}")

            # Ensure path is absolute or starts with ~
            if not path_str.startswith("/") and not path_str.startswith("~"):
                return self.failure(f"Path must be absolute or start with ~: {path_str}")

        return self.success()
