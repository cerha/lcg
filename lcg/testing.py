# Copyright (C) 2026 Tomáš Cerha <cerha@truecode.cz>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Pytest plugin for testing the exported HTML content in a web browser.

The browser tests verify the behavior of the JavaScript code and the
accessibility of the content as presented to assistive technologies, such as
the keyboard focus or the ARIA attributes set by the scripts.  They run in a
headless browser through Playwright (the package 'pytest-playwright').

The plugin is enabled in 'conftest.py' of the project by:

    pytest_plugins = ['lcg.testing']

The browser tests are marked by 'pytest.mark.browser' and load the tested
content into the browser through the fixture 'load_content' (see
'load_content()').  The fixtures of 'pytest-playwright', such as 'page', and
its command line options, such as '--browser webkit' or '--headed', are
available as well.

When Playwright or the browser are not installed, the browser tests are
skipped, so that the other tests may run without them.  When the environment
variable 'PYTEST_REQUIRE_BROWSER' is set (such as in CI), the browser tests
fail instead, so that they can not be skipped unnoticed.

"""

import os
import urllib.parse

import pytest

import lcg

BASE_URI = 'http://lcg.test/'
"""The URI of the loaded page.  The requests are served by the test itself."""

_REQUIRE_BROWSER = 'PYTEST_REQUIRE_BROWSER'


def _missing_browser(config):
    """Return the reason why the browser tests can't run or None if they can."""
    try:
        import playwright.sync_api
        import pytest_playwright  # noqa: F401
    except ImportError:
        return ("Playwright not installed "
                "(pip install pytest-playwright && playwright install chromium)")
    browsers = config.getoption('browser', None) or ['chromium']
    with playwright.sync_api.sync_playwright() as p:
        for name in browsers:
            if not os.path.exists(getattr(p, name).executable_path):
                return "Browser %s not installed (playwright install %s)" % (name, name)
    return None


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'browser: test runs in a web browser through Playwright; skipped when not installed',
    )


def pytest_collection_modifyitems(config, items):
    browser_items = [item for item in items if item.get_closest_marker('browser')]
    if browser_items:
        reason = _missing_browser(config)
        if reason:
            if os.getenv(_REQUIRE_BROWSER):
                raise pytest.UsageError("%s is set, but %s." % (_REQUIRE_BROWSER, reason))
            for item in browser_items:
                item.add_marker(pytest.mark.skip(reason=reason))


class _Exporter(lcg.StyledHtmlExporter, lcg.HtmlExporter):
    pass


@pytest.fixture
def load_content(page):
    """Return a function loading given content into the browser page.

    The returned function takes the following arguments:

      content -- the 'lcg.Content' instance to load
      lang -- the language of the content
      resource_dirs -- the directories to search for the resources (scripts,
        stylesheets) required by the content in addition to the default LCG
        resources (see 'lcg.ResourceProvider')

    The content is exported as an HTML page served at 'BASE_URI' together
    with its resources.  The function returns the Playwright 'Page' instance
    with the page loaded.

    The test fails when a JavaScript error occurs in the page.

    """
    errors = []
    page.on('pageerror', lambda error: errors.append(error))

    def load(content, lang='en', resource_dirs=()):
        node = lcg.ContentNode('index', title='Test', content=content,
                               resource_provider=lcg.ResourceProvider(dirs=resource_dirs))
        exporter = _Exporter()
        context = exporter.context(node, lang)
        html = exporter.export(context)
        files = dict((urllib.parse.urljoin(BASE_URI, context.uri(r)), r.src_file())
                     for r in node.resources() if r.src_file())

        def handle(route):
            uri = route.request.url
            if uri == BASE_URI:
                route.fulfill(body=html, content_type='text/html; charset=utf-8')
            elif uri in files:
                route.fulfill(path=files[uri])
            else:
                route.fulfill(status=404)
        page.route(BASE_URI + '**', handle)
        page.goto(BASE_URI)
        return page

    yield load
    assert not errors, errors
