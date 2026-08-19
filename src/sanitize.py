"""nh3 白名单消毒 + 相对 URL 绝对化。"""
from __future__ import annotations

from urllib.parse import urljoin

import nh3

_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "del",
    "div", "dl", "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4",
    "h5", "h6", "hr", "i", "img", "ins", "kbd", "li", "mark", "ol", "p",
    "pre", "q", "s", "small", "span", "strike", "strong", "sub", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
_ATTRS = {
    "*": {"id", "class", "title"},
    "a": {"href", "target"},
    "img": {"src", "srcset", "alt", "width", "height", "loading"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
}
_URL_ATTRS = {"href", "src"}


def _absolutize(html: str, base_url: str) -> str:
    """用正则对消毒后的属性做相对 URL 绝对化（nh3 无遍历 API，属性值已被转义）。"""
    import re
    def repl(m: re.Match) -> str:
        attr, quote, val = m.group(1), m.group(2), m.group(3)
        if attr not in _URL_ATTRS or not val:
            return m.group(0)
        if val.startswith(("http://", "https://", "mailto:", "data:", "#")):
            return m.group(0)
        return f'{attr}={quote}{urljoin(base_url, val)}{quote}'

    return re.sub(r'\b(href|src)=("([^"]*)"|\'([^\']*)\')', repl, html)


def sanitize_html(html: str, base_url: str) -> str:
    """消毒 HTML 并将相对资源地址绝对化（基于原文 URL）。"""
    cleaned = nh3.clean(
        html,
        tags=_TAGS,
        attributes=_ATTRS,
        url_schemes={"http", "https", "mailto", "data"},
        link_rel="noopener nofollow",
        strip_comments=True,
    )
    return _absolutize(cleaned, base_url)
