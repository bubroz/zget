"""
Cookie management utilities.
"""


def get_cookies_from_browser(browser: str = "chrome") -> str:
    """
    Get cookie extraction argument for yt-dlp.

    Args:
        browser: Browser name ("chrome", "firefox", "safari", "edge")

    Returns:
        Browser cookie source string for yt-dlp

    Note:
        This is a convenience function. The actual cookie extraction
        is handled by yt-dlp's --cookies-from-browser option.
    """
    valid_browsers = {
        "chrome",
        "firefox",
        "safari",
        "edge",
        "chromium",
        "brave",
        "opera",
        "vivaldi",
    }
    browser = browser.lower()

    if browser not in valid_browsers:
        raise ValueError(
            f"Unknown browser: {browser}. Valid options: {', '.join(sorted(valid_browsers))}"
        )

    return browser
