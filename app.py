"""
AI 销售助手 - 裸 socket HTTP 服务器 (Windows 完全兼容)
"""
import os
import json
import socket
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from dotenv import load_dotenv
from database import (
    save_analysis, save_name, get_record_count,
    get_clients, get_today_stats, get_week_stats, get_month_stats,
    mark_dealt, get_need_followup, get_dealt_records, batch_delete,
)

load_dotenv(os.path.join(BASE_DIR, ".env"))

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 销售助手</title>
<style>
body{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;display:flex;justify-content:center;padding-top:30px}
.container{width:650px;max-width:95%}
h1{text-align:center;font-size:28px}
.subtitle{text-align:center;color:#888;margin-bottom:10px;font-size:14px}
.nav{display:flex;gap:6px;justify-content:center;margin-bottom:15px;flex-wrap:wrap}
.nav a{padding:8px 14px;border-radius:6px;text-decoration:none;color:#fff;font-size:13px;font-weight:bold}
.nav .nav-analyze{background:#4a90d9}
.nav .nav-clients{background:#27ae60}
.nav .nav-report{background:#e67e22}
textarea{width:100%;padding:15px;border:2px solid #ddd;border-radius:10px;font-size:16px;resize:vertical;box-sizing:border-box}
textarea:focus{border-color:#4a90d9;outline:none}
button{display:block;width:100%;padding:14px;margin-top:15px;background:#4a90d9;color:#fff;border:none;border-radius:10px;font-size:18px;cursor:pointer}
button:disabled{background:#aaa}
.result{margin-top:20px;padding:20px;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);line-height:1.8;display:none;font-size:14px}
.loading{text-align:center;padding:30px;color:#888;display:none}
@media (max-width: 600px) {{
h1{{font-size:22px}}
.nav a{{padding:6px 10px;font-size:11px}}
textarea{{font-size:15px}}
button{{font-size:16px;padding:12px}}
.subtitle{{font-size:12px}}
.result{{font-size:13px}}
}}
</style>
</head>
<body>
<div class="container">
<h1>🏠 AI 销售助手</h1>
<p class="subtitle">粘贴客户聊天记录，AI 自动分析</p>
<div class="nav">
<a href="/" class="nav-analyze">🏠 分析</a>
<a href="/clients" class="nav-clients">👥 客户列表</a>
<a href="/report" class="nav-report">📊 销售报告</a>
</div>
<textarea id="chatInput" placeholder="粘贴客户聊天记录..." rows="8"></textarea>
<button id="analyzeBtn" onclick="analyze()">🔍 分析客户</button>
<div id="loading" class="loading">正在分析中...</div>
<div id="result" class="result"></div>
</div>
<script>
async function analyze(){
const t=document.getElementById("chatInput").value.trim();
if(!t){alert("请先粘贴客户聊天记录！");return}
document.getElementById("loading").style.display="block";
document.getElementById("result").style.display="none";
document.getElementById("analyzeBtn").disabled=true;
try{
const r=await fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chat:t})});
const d=await r.json();
document.getElementById("result").innerHTML=d.html||"分析失败";
document.getElementById("result").style.display="block";
}catch(e){alert("请求失败: "+e.message)}
finally{document.getElementById("loading").style.display="none";document.getElementById("analyzeBtn").disabled=false}
}
</script>
</body>
</html>"""


def extract_field(text, field_name):
    pattern = rf"- {field_name}[：:]\s*(.*)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def build_clients_page(q=""):
    clients = get_clients(None)
    total = get_record_count()

    rows = ""
    cards = ""
    if clients:
        for c in clients:
            cid, cname, need, budget, region, btype, purpose, interest, follow, note, dealt, created = c
            is_dealt = dealt == 1
            row_class = 'class="dealt"' if is_dealt else ""
            card_dealt_class = 'card-dealt' if is_dealt else ""
            deal_badge_card = '<span style="background:#27ae60;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold">✓ 成交</span>' if is_dealt else ""
            deal_badge = '<br><span style="color:#27ae60;font-size:11px;font-weight:bold">✓ 成交</span>' if is_dealt else ""
            deal_btn = "" if is_dealt else f'<button onclick="markDealt({cid})" style="padding:4px 10px;background:#27ae60;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">标记成交</button>'
            edit_btn = f'<button onclick="editName({cid})" style="padding:4px 10px;background:#f39c12;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;margin-top:4px">编辑名字</button>'
            name_cell = f'<span id="name-{cid}">{cname or "-"}{deal_badge}</span>'
            name_card = f'<span id="name-{cid}">{cname or "-"}</span>'
            rows += f"""
            <tr {row_class}>
                <td class="cb-col" style="display:none"><input type="checkbox" class="del-cb" value="{cid}"></td>
                <td>{name_cell}</td>
                <td>{cid}</td>
                <td>{need or '-'}</td>
                <td>{budget or '-'}</td>
                <td>{region or '-'}</td>
                <td>{btype or '-'}</td>
                <td>{purpose or '-'}</td>
                <td style="font-size:11px">{created[:16] if created else '-'}</td>
                <td style="white-space:nowrap;text-align:center">{deal_btn}{edit_btn}</td>
            </tr>"""
            cards += f"""
            <div class="client-card {card_dealt_class}">
                <div class="card-top">
                    <span class="card-name">{name_card}</span>
                    {deal_badge_card}
                    <span class="card-id">#{cid}</span>
                </div>
                <div class="card-main">
                    <div class="card-row"><span class="card-label">需求</span> {need or '-'}</div>
                    <div class="card-row"><span class="card-label">预算</span> {budget or '-'}</div>
                    <div class="card-row"><span class="card-label">地区</span> {region or '-'}</div>
                </div>
                <div class="card-extra" style="display:none">
                    <div class="card-row"><span class="card-label">类型</span> {btype or '-'}</div>
                    <div class="card-row"><span class="card-label">目的</span> {purpose or '-'}</div>
                    <div class="card-row"><span class="card-label">时间</span> {created[:16] if created else '-'}</div>
                </div>
                <div class="card-actions">
                    <button class="card-more" onclick="this.parentElement.parentElement.querySelector('.card-extra').style.display=this.parentElement.parentElement.querySelector('.card-extra').style.display==='none'?'block':'none';this.textContent=this.textContent==='更多 ▼'?'收起 ▲':'更多 ▼'">更多 ▼</button>
                    {deal_btn}{edit_btn}
                </div>
            </div>"""
    else:
        rows = '<tr><td colspan="11" style="text-align:center;color:#888">暂无客户记录</td></tr>'
        cards = '<div class="client-card" style="text-align:center;color:#888;padding:30px">暂无客户记录</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>客户列表 - AI 销售助手</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;padding:20px}}
.container{{max-width:1400px;margin:0 auto}}
h1{{text-align:center}}
.nav{{display:flex;gap:10px;justify-content:center;margin-bottom:15px}}
.nav a{{padding:10px 20px;border-radius:8px;text-decoration:none;color:#fff;font-size:14px;font-weight:bold}}
.top-bar{{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-bottom:15px}}
.stats{{color:#888}}
.del-toggle{{padding:6px 14px;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px}}
.del-actions{{display:none;gap:8px;align-items:center}}
.del-confirm{{padding:6px 14px;background:#c0392b;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px}}
.del-cancel{{padding:6px 14px;background:#95a5a6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th{{background:#4a90d9;color:#fff;padding:10px;font-size:12px;text-align:left}}
td{{padding:8px 10px;border-bottom:1px solid #eee;font-size:12px}}
tr:hover{{background:#f8f9fa}}
.dealt{{background:#e8f5e9}}
.cb-col.show{{display:table-cell!important}}
/* 卡片视图 - 手机端 */
.client-cards{{display:none;flex-direction:column;gap:12px}}
.client-card{{background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
.client-card.card-dealt{{background:#e8f5e9;border-left:4px solid #27ae60}}
.card-top{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.card-name{{font-size:16px;font-weight:bold;flex:1}}
.card-id{{color:#aaa;font-size:12px}}
.card-main{{margin-bottom:6px}}
.card-row{{font-size:13px;padding:3px 0;color:#555}}
.card-label{{color:#888;font-size:11px;margin-right:8px}}
.card-extra{{border-top:1px dashed #ddd;padding-top:6px;margin-top:4px}}
.card-actions{{display:flex;gap:6px;align-items:center;margin-top:10px;flex-wrap:wrap}}
.card-actions button{{margin-top:0!important;width:auto!important}}
.card-more{{padding:4px 12px;background:#e8e8e8;border:none;border-radius:4px;font-size:12px;cursor:pointer;color:#666}}
.note-modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:999;justify-content:center;align-items:center}}
.note-modal.show{{display:flex}}
.note-box{{background:#fff;padding:25px;border-radius:10px;width:450px;max-width:90%}}
.note-box textarea{{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;box-sizing:border-box}}
.note-box .note-btns{{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}}
.table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
@media (max-width: 768px) {{
.nav a{{padding:8px 12px;font-size:12px}}
.top-bar{{flex-wrap:wrap;gap:8px}}
.top-bar input{{width:150px;font-size:12px}}
table{{display:none!important}}
.client-cards{{display:flex!important}}
.del-toggle,.del-confirm,.del-cancel{{font-size:11px;padding:5px 10px}}
}}
</style>
</head>
<body>
<div class="container">
<h1>👥 客户列表</h1>
<div class="nav">
<a href="/" style="background:#4a90d9">🏠 分析</a>
<a href="/clients" style="background:#27ae60">👥 客户列表</a>
<a href="/report" style="background:#e67e22">📊 销售报告</a>
</div>
<div class="top-bar">
<span class="stats" id="clientCount">共 {total} 个客户</span>
<div style="display:flex;gap:10px;align-items:center">
<input type="text" id="searchBox" placeholder="🔍 搜索名字或地区..." oninput="filterClients()" style="padding:6px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:200px;outline:none">
<div class="del-actions" id="delActions">
<button class="del-confirm" onclick="doBatchDelete()">确认删除</button>
<button class="del-cancel" onclick="toggleDeleteMode()">取消</button>
</div>
<button class="del-toggle" onclick="toggleDeleteMode()" id="delToggleBtn">🗑 删除记录</button>
</div>
</div>
<table>
<thead><tr><th class="cb-col" style="display:none">选</th><th>名字</th><th>ID</th><th>需求</th><th>预算</th><th>地区</th><th>类型</th><th>目的</th><th>时间</th><th>操作</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<div class="client-cards">{cards}</div>
</div>
</div>

<!-- 备注弹窗 -->
<div class="note-modal" id="noteModal">
<div class="note-box">
<h3>✏️ 编辑名字 - 客户 #<span id="editNameId"></span></h3>
<input id="editNameText" style="width:100%;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;box-sizing:border-box" placeholder="输入客户名字...">
<div class="note-btns">
<button onclick="closeNote()" style="background:#95a5a6;color:#fff;border:none;padding:8px 18px;border-radius:6px;cursor:pointer">取消</button>
<button onclick="saveName()" style="background:#27ae60;color:#fff;border:none;padding:8px 18px;border-radius:6px;cursor:pointer">保存</button>
</div>
</div>
</div>

<script>
function filterClients() {{
    const query = document.getElementById('searchBox').value.toLowerCase().trim();
    const rows = document.querySelectorAll('tbody tr');
    let visibleCount = 0;
    rows.forEach(row => {{
        const text = row.textContent.toLowerCase();
        const match = !query || text.includes(query);
        row.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    }});
    document.getElementById('clientCount').textContent = '共 ' + visibleCount + ' 个客户';
}}

let deleteMode = false;
let currentNoteId = null;

function toggleDeleteMode() {{
    deleteMode = !deleteMode;
    document.querySelectorAll('.cb-col').forEach(el => {{
        el.style.display = deleteMode ? '' : 'none';
    }});
    document.getElementById('delActions').style.display = deleteMode ? 'flex' : 'none';
    document.getElementById('delToggleBtn').textContent = deleteMode ? '🗑 退出删除' : '🗑 删除记录';
    if (!deleteMode) document.querySelectorAll('.del-cb').forEach(cb => cb.checked = false);
}}

async function doBatchDelete() {{
    const checked = document.querySelectorAll('.del-cb:checked');
    if (checked.length === 0) {{ alert('请至少勾选一个客户'); return; }}
    if (!confirm('确认删除选中的 ' + checked.length + ' 个客户？此操作不可恢复！')) return;
    const ids = Array.from(checked).map(cb => parseInt(cb.value));
    try {{
        const r = await fetch('/batch-delete', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{ids:ids}}) }});
        if (r.ok) {{ location.reload(); }} else {{ alert('删除失败'); }}
    }} catch(e) {{ alert('请求失败: '+e.message); }}
}}

let currentEditId = null;

function editName(id) {{
    currentEditId = id;
    document.getElementById('editNameId').textContent = id;
    const span = document.getElementById('name-'+id);
    document.getElementById('editNameText').value = span ? span.textContent.trim() : '';
    document.getElementById('noteModal').classList.add('show');
}}

function closeNote() {{
    document.getElementById('noteModal').classList.remove('show');
    currentEditId = null;
}}

async function saveName() {{
    const name = document.getElementById('editNameText').value.trim();
    try {{
        const r = await fetch('/save-name', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{id:currentEditId, name:name}}) }});
        if (r.ok) {{ location.reload(); }} else {{ alert('保存失败'); }}
    }} catch(e) {{ alert('请求失败: '+e.message); }}
}}

async function markDealt(id){{if(!confirm('确认标记为成交？'))return;try{{const r=await fetch('/dealt',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id}})}});if(r.ok){{location.reload();}}else{{alert('标记失败')}}}}catch(e){{alert('请求失败: '+e.message)}}}}
</script>
</body>
</html>"""


def build_report_page():
    today_total, today_dealt = get_today_stats()
    week_total, week_dealt = get_week_stats()
    month_total, month_dealt = get_month_stats()
    dealt_records = get_dealt_records(50)

    dealt_rows = ""
    if dealt_records:
        for d in dealt_records:
            did, name, need, budget, region, dealt_at = d
            dealt_rows += f"""
            <tr>
                <td>{did}</td>
                <td>{name or '-'}</td>
                <td>{need or '-'}</td>
                <td>{budget or '-'}</td>
                <td>{region or '-'}</td>
                <td>{dealt_at[:16] if dealt_at else '-'}</td>
            </tr>"""
    else:
        dealt_rows = '<tr><td colspan="6" style="text-align:center;color:#888">暂无成交记录</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>销售报告 - AI 销售助手</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;background:#f0f2f5;padding:20px}}
.container{{max-width:1000px;margin:0 auto}}
h1{{text-align:center}}
.nav{{display:flex;gap:10px;justify-content:center;margin-bottom:30px}}
.nav a{{padding:10px 20px;border-radius:8px;text-decoration:none;color:#fff;font-size:14px;font-weight:bold}}
.cards{{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin-bottom:35px}}
.card{{background:#fff;padding:25px 35px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1);text-align:center;min-width:160px}}
.card .num{{font-size:42px;font-weight:bold;color:#4a90d9}}
.card .num.dealt{{color:#27ae60}}
.card .label{{color:#888;font-size:14px;margin-top:6px}}
h3{{text-align:center;margin-bottom:15px;color:#555;display:flex;align-items:center;justify-content:center;gap:10px}}
.section-title{{font-size:16px;font-weight:bold;margin:30px 0 10px;color:#333}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th{{background:#27ae60;color:#fff;padding:10px;font-size:13px;text-align:left}}
td{{padding:8px 10px;border-bottom:1px solid #eee;font-size:13px}}
tr:hover{{background:#f8f9fa}}
.table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
@media (max-width: 768px) {{
body{{padding:10px}}
h1{{font-size:22px}}
.nav a{{padding:8px 12px;font-size:12px}}
.cards{{gap:10px}}
.card{{padding:15px 20px;min-width:120px}}
.card .num{{font-size:32px}}
.card .label{{font-size:12px}}
h3{{font-size:15px}}
th,td{{font-size:12px;padding:6px}}
}}
</style>
</head>
<body>
<div class="container">
<h1>📊 销售报告</h1>
<div class="nav">
<a href="/" style="background:#4a90d9">🏠 分析</a>
<a href="/clients" style="background:#27ae60">👥 客户列表</a>
<a href="/report" style="background:#e67e22">📊 销售报告</a>
</div>
<h3><span class="icon">📅</span> 今日统计</h3>
<div class="cards">
<div class="card"><div class="num">{today_total}</div><div class="label">今日分析</div></div>
<div class="card"><div class="num dealt">{today_dealt}</div><div class="label">今日成交</div></div>
</div>
<h3><span class="icon">📆</span> 本周统计</h3>
<div class="cards">
<div class="card"><div class="num">{week_total}</div><div class="label">本周分析</div></div>
<div class="card"><div class="num dealt">{week_dealt}</div><div class="label">本周成交</div></div>
</div>
<h3><span class="icon">📈</span> 本月统计</h3>
<div class="cards">
<div class="card"><div class="num">{month_total}</div><div class="label">本月分析</div></div>
<div class="card"><div class="num dealt">{month_dealt}</div><div class="label">本月成交</div></div>
</div>
<div class="section-title">✅ 成交记录</div>
<div class="table-wrap">
<table>
<thead><tr><th>ID</th><th>名字</th><th>需求</th><th>预算</th><th>地区</th><th>成交时间</th></tr></thead>
<tbody>{dealt_rows}</tbody>
</table>
</div>
</div>
</body>
</html>"""


def analyze_chat(chat_text):
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_URL)
    prompt = f"""你是一个专业的房地产销售助手。请分析以下客户聊天记录，并严格按照格式输出。

客户聊天记录：
{chat_text}

请按照以下格式输出（用中文）：

【客户名字】
<从聊天中提取客户称呼或名字，如无法提取则填"未知">
【客户需求总结】
- 需求：<总结客户想找什么类型的房产>
- 预算：<客户的预算范围>
- 地区：<客户想找的地区>
- 类型：<买房/租房>
- 目的：<自住/投资>
- 意向程度：<高/中/低>

【Follow Up 建议】
<写一条自然、友好的跟进信息，适合 WhatsApp 发送，不要超过3句话>"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "你是一个专业的房地产销售助手。"}, {"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=1000,
    )
    return response.choices[0].message.content


def http_response(conn, status, content_type, body_bytes):
    headers = [
        f"HTTP/1.1 {status}", f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}", "Connection: close",
        "Access-Control-Allow-Origin: *", "", ""
    ]
    conn.sendall("\r\n".join(headers).encode() + body_bytes)


def handle_request(conn):
    try:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk: return
            raw += chunk
            if len(raw) > 65536: break

        request_text = raw.decode("utf-8", errors="replace")
        lines = request_text.split("\r\n")
        if not lines: return

        first_line = lines[0]
        parts = first_line.split(" ")
        method = parts[0] if len(parts) > 0 else ""
        full_path = parts[1] if len(parts) > 1 else "/"

        if "?" in full_path:
            path, query_string = full_path.split("?", 1)
        else:
            path, query_string = full_path, ""

        query_params = {}
        if query_string:
            for pair in query_string.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query_params[k] = v

        content_length = 0
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                if key.lower() == "content-length":
                    content_length = int(value)

        body = ""
        if "\r\n\r\n" in request_text:
            body = request_text.split("\r\n\r\n", 1)[1]
            if len(body) < content_length:
                body += conn.recv(content_length - len(body)).decode("utf-8", errors="replace")

        print(f"[{method}] {path}")

        if method == "GET" and path == "/":
            http_response(conn, "200 OK", "text/html; charset=utf-8", HTML_PAGE.encode("utf-8"))

        elif method == "GET" and path == "/clients":
            html_str = build_clients_page(query_params.get("q", ""))
            http_response(conn, "200 OK", "text/html; charset=utf-8", html_str.encode("utf-8"))

        elif method == "GET" and path == "/report":
            html_str = build_report_page()
            http_response(conn, "200 OK", "text/html; charset=utf-8", html_str.encode("utf-8"))

        elif method == "POST" and path == "/dealt":
            data = json.loads(body)
            mark_dealt(data.get("id", 0))
            http_response(conn, "200 OK", "application/json; charset=utf-8", b'{"ok":true}')

        elif method == "POST" and path == "/save-name":
            data = json.loads(body)
            save_name(data.get("id", 0), data.get("name", ""))
            http_response(conn, "200 OK", "application/json; charset=utf-8", b'{"ok":true}')

        elif method == "POST" and path == "/batch-delete":
            data = json.loads(body)
            ids = data.get("ids", [])
            batch_delete(ids)
            http_response(conn, "200 OK", "application/json; charset=utf-8", json.dumps({"ok": True, "deleted": len(ids)}).encode("utf-8"))

        elif method == "POST" and path == "/analyze":
            try:
                data = json.loads(body)
                chat_text = data.get("chat", "")
                if not chat_text.strip():
                    resp = json.dumps({"html": "<p style='color:red;'>请输入聊天记录</p>"}, ensure_ascii=False)
                    http_response(conn, "200 OK", "application/json; charset=utf-8", resp.encode("utf-8"))
                else:
                    ai_result = analyze_chat(chat_text)
                    try:
                        customer_name = extract_field(ai_result, "客户名字") or extract_field(ai_result, "名字")
                        need_summary = extract_field(ai_result, "需求")
                        budget = extract_field(ai_result, "预算")
                        region = extract_field(ai_result, "地区")
                        buy_type = extract_field(ai_result, "类型")
                        purpose = extract_field(ai_result, "目的")
                        interest_level = extract_field(ai_result, "意向程度")
                        follow_up_match = re.search(r"【Follow[_\s]?Up[_\s]?建议】\s*\n*(.*)", ai_result, re.DOTALL)
                        follow_up = follow_up_match.group(1).strip() if follow_up_match else ""
                        save_analysis(chat_text, customer_name, need_summary, budget, region, buy_type, purpose, interest_level, follow_up)
                        print(f"  💾 已保存 (共 {get_record_count()} 条)")
                    except Exception as db_err:
                        print(f"  ⚠ 数据库保存失败: {db_err}")
                    resp = json.dumps({"html": ai_result.replace("\n", "<br>")}, ensure_ascii=False)
                    http_response(conn, "200 OK", "application/json; charset=utf-8", resp.encode("utf-8"))
            except Exception as e:
                resp = json.dumps({"html": f"<p style='color:red;'>错误：{str(e)}</p>"}, ensure_ascii=False)
                http_response(conn, "200 OK", "application/json; charset=utf-8", resp.encode("utf-8"))
        else:
            http_response(conn, "404 Not Found", "text/plain", b"404 Not Found")
    except Exception as e:
        print(f"处理请求出错: {e}")
    finally:
        conn.close()


def main():
    import threading
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 8080))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((HOST, PORT))
    except OSError:
        HOST = "0.0.0.0"
        s.bind((HOST, PORT))
    s.listen(10)
    print("=" * 50)
    print(f"  AI 销售助手 启动成功！（多线程）")
    print(f"  👉 监听: http://{HOST}:{PORT}")
    print("=" * 50)
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_request, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n服务器已停止。")
    finally:
        s.close()


if __name__ == "__main__":
    main()