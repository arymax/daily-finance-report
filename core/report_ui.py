"""
core/report_ui.py
將 Markdown 報告轉換為 HTML，並透過 pywebview 在獨立視窗中顯示。
視窗關閉前程式不會退出。
"""
import markdown

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "Microsoft JhengHei", "微軟正黑體", sans-serif;
    background: #0f1117;
    color: #e1e4e8;
    padding: 32px 48px;
    line-height: 1.7;
    font-size: 15px;
  }}
  h1 {{
    font-size: 1.6em;
    color: #58a6ff;
    border-bottom: 1px solid #30363d;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }}
  h2 {{
    font-size: 1.15em;
    color: #79c0ff;
    margin-top: 28px;
    margin-bottom: 10px;
  }}
  h3 {{
    font-size: 1.0em;
    color: #a5d6ff;
    margin-top: 20px;
    margin-bottom: 8px;
  }}
  p {{ margin-bottom: 10px; }}
  ul, ol {{
    padding-left: 24px;
    margin-bottom: 10px;
  }}
  li {{ margin-bottom: 4px; }}
  strong {{ color: #ffa657; }}
  em {{ color: #adbac7; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 14px;
  }}
  th {{
    background: #161b22;
    color: #79c0ff;
    padding: 10px 14px;
    text-align: left;
    border: 1px solid #30363d;
    font-weight: 600;
  }}
  td {{
    padding: 8px 14px;
    border: 1px solid #30363d;
    color: #e1e4e8;
  }}
  tr:nth-child(even) td {{ background: #161b22; }}
  tr:hover td {{ background: #1c2128; }}
  code {{
    background: #161b22;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 0.9em;
    color: #ff7b72;
  }}
  hr {{
    border: none;
    border-top: 1px solid #30363d;
    margin: 24px 0;
  }}
  blockquote {{
    border-left: 3px solid #388bfd;
    padding-left: 16px;
    color: #8b949e;
    margin: 12px 0;
  }}
  .timestamp {{
    font-size: 12px;
    color: #484f58;
    margin-top: 40px;
    text-align: right;
  }}
</style>
</head>
<body>
{content}
<div class="timestamp">{timestamp}</div>
</body>
</html>"""


def open_report_window(
    md_content: str,
    title: str = "盤前晨檢",
    width: int = 860,
    height: int = 700,
    timestamp: str = "",
) -> None:
    """
    將 Markdown 內容渲染為 HTML，並在 pywebview 獨立視窗中顯示。
    視窗關閉後函式才返回。
    """
    import webview

    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    html = _HTML_TEMPLATE.format(
        title=title,
        content=html_body,
        timestamp=timestamp,
    )

    window = webview.create_window(
        title=title,
        html=html,
        width=width,
        height=height,
        resizable=True,
        min_size=(600, 400),
    )
    webview.start()
