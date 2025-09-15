# backend/app.py
import os
import base64
import time
import urllib.parse
import mimetypes
import re
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, make_response
from flask_cors import CORS
from jinja2 import Environment, FileSystemLoader

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

# 이메일(MIME)
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# -----------------------------
# 환경설정
# -----------------------------
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",  # ⬅️ 추가
]
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME_Y = os.getenv("SHEET_NAME_Y", "트라이얼(Y)")
SHEET_NAME_N = os.getenv("SHEET_NAME_N", "트라이얼(N)")
PORT = int(os.getenv("PORT", 8080))
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

# 스킵 키워드(유입월 컬럼에 포함되면 메타/구분 행으로 판단)
IGNORE_KEYWORDS = [
    k.strip() for k in os.getenv("IGNORE_KEYWORDS", "종료,합계,요약").split(",") if k.strip()
]

# 사용자 제공 컬럼 스키마에 맞춘 맵핑
COLS = {
    "inflow_month": "유입월",
    "signup_date": "가입일",
    "company_id": "회사 ID",
    "company": "회사명",
    "mkt_optin": "마케팅수신동의",
    "phone": "연락처",
    "manager": "담당자",
    "email": "이메일",
    "is_test": "테스트 여부",

    "contact1": "1차 컨택",
    "contact2": "2차 컨택",
    "contact3": "3차 컨택 (종료일)",

    # D7/M1은 두 번씩 나오므로 파생키로 나눔
    "d7_1": "D7",
    "m1_1": "M1",

    "first_consult": "최초 상담일",
    "conversion_date": "전환일",
    "memo": "상담내용",
    "action": "후속조치",
    "end_date": "종료일",

    "d7_2": "D7",
    "m1_2": "M1",

    "snapshot": "TTC",
}

# -----------------------------
# 템플릿 & 인라인 이미지
# -----------------------------
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "email_templates"))
)
env.globals["now"] = lambda: datetime.now().strftime("%Y-%m-%d")
env.globals["cid"] = lambda name: f"cid:{name}"

ASSET_BASE = os.getenv("ASSET_BASE", ORIGIN)
env.globals["asset"] = lambda p: f"{ASSET_BASE}{p if p.startswith('/') else '/'+p}"

# 템플릿 목록
TEMPLATE_CATALOG = [
    {
        "id": "eform_plan_change.html",
        "label": "[이폼사인] 요금제 변경 방법 안내",
        "default_subject": "[이폼사인] 요금제 변경 방법 안내",
    },
    {
        "id": "eform_pay_prepaid_add.html",
        "label": "[이폼사인] 충전형 결제 방법 안내 (추가 구매)",
        "default_subject": "[이폼사인] 충전형 결제 방법 안내 (추가 구매하기)",
    },
    {
        "id": "eform_pay_prepaid_buy.html",
        "label": "[이폼사인] 충전형 결제 방법 안내 (구매하기)",
        "default_subject": "[이폼사인] 충전형 결제 방법 안내 (구매하기)",
    },
    {
        "id": "eform_company_seal_guide.html",
        "label": "[이폼사인] 회사 도장 등록 방법 안내",
        "default_subject": "[이폼사인] 회사 도장 등록 방법 안내",
    },
    {
        "id": "eform_user_training_request.html",
        "label": "[이폼사인] 사용자 교육 신청 안내",
        "default_subject": "[이폼사인] 사용자 교육 신청 안내",
    },
    {
        "id": "eform_password_reset_change.html",
        "label": "[이폼사인] 비밀번호 초기화 및 변경 방법 안내",
        "default_subject": "[이폼사인] 비밀번호 초기화 및 변경 방법 안내",
    },
]

# 템플릿별 인라인 이미지 매핑 (cid → 파일경로) — 파일은 backend/assets/email/ 하위
TEMPLATE_INLINE_MAP: Dict[str, Dict[str, str]] = {
    "eform_plan_change.html": {
        "img1": "assets/email/요금제 변경(1).png",
        "img2": "assets/email/요금제 변경(2).png",
        "img3": "assets/email/요금제 변경(구매하기).png",
        "img4": "assets/email/요금제 변경(4).png",
    },
    "eform_pay_prepaid_add.html": {
        "img1": "assets/email/요금제 변경(1).png",
        "img2": "assets/email/요금제 변경(2).png",
        "img3": "assets/email/요금제 변경(추가구매).png",
        "img4": "assets/email/요금제 변경(4).png",
    },
    "eform_pay_prepaid_buy.html": {
        "img1": "assets/email/요금제 변경(1).png",
        "img2": "assets/email/요금제 변경(2).png",
        "img3": "assets/email/요금제 변경(구매하기).png",
        "img4": "assets/email/요금제 변경(4).png",
    },
    "eform_company_seal_guide.html": {
        "img1": "assets/email/회사 도장 등록(1).png",
        "img2": "assets/email/회사 도장 등록(2).png",
        "img3": "assets/email/회사 도장 등록(3).png",
        "img4": "assets/email/회사 도장 등록(4).png",
        "img5": "assets/email/회사 도장 등록(5).png",
    },
    "eform_user_training_request.html": {
        # 이미지 없음
    },
    "eform_password_reset_change.html": {
        "img1": "assets/email/비밀번호 변경(1).png",
        "img2": "assets/email/비밀번호 변경(2).png",
        "img3": "assets/email/비밀번호 변경(3).png",
        "img4": "assets/email/비밀번호 변경(4).png",
    },
}

# ✅ 공통 배너(서명용) CID 추가: 모든 템플릿에 sig_banner 포함
COMMON_INLINE = {"sig_banner": "assets/email/이폼사인 배너.png"}
for key in list(TEMPLATE_INLINE_MAP.keys()):
    TEMPLATE_INLINE_MAP[key] = {**TEMPLATE_INLINE_MAP[key], **COMMON_INLINE}

# 기본 발신자 정보(템플릿 변수 기본값)
DEFAULT_SENDER_CONTEXT = {
    "sender_name": "김서은",
    "sender_title": "프로",
    "sender_team": "클라우드사업본부",
    "sender_company": "(주)포시에스",
    "sender_addr": "서울시 강남구 논현로 646",
    "sender_tel": "02-6188-8411",
    "sender_email": "seoeun@forcs.com",
    "sender_www": "https://www.forcs.com",
    "sender_eform": "https://www.eformsign.com",
}

# -----------------------------
# Flask & CORS
# -----------------------------
app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": [ORIGIN]}},
    supports_credentials=True,
    expose_headers=["Content-Type"],
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
)

@app.before_request
def _cors_preflight():
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin")
        resp = make_response("", 204)
        if origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
        req_hdrs = request.headers.get("Access-Control-Request-Headers", "Content-Type, Authorization")
        resp.headers["Access-Control-Allow-Headers"] = req_hdrs
        resp.headers["Access-Control-Allow-Methods"] = request.headers.get("Access-Control-Request-Method", "GET,POST,OPTIONS")
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp

@app.after_request
def _cors_after(resp):
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.errorhandler(Exception)
def _cors_error(e):
    code = getattr(e, "code", 500)
    resp = jsonify({"error": str(e)})
    resp.status_code = code
    return _cors_after(resp)

# -----------------------------
# Google 인증/서비스
# -----------------------------
def get_creds():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return creds

def sheets_service():
    return build("sheets", "v4", credentials=get_creds())

def gmail_service():
    return build("gmail", "v1", credentials=get_creds())

def get_creds():
    creds = None
    token_path = "token.json"
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                except RefreshError as e:
                    # 흔한 케이스: invalid_grant (만료/취소)
                    try:
                        os.remove(token_path)
                    except Exception:
                        pass
                    creds = None  # 아래 재인증으로 진행
            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        return creds
    except Exception as e:
        # 마지막 안전장치: token.json 날리고 재인증 시도
        try:
            if os.path.exists(token_path):
                os.remove(token_path)
        except Exception:
            pass
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        return creds

# -----------------------------
# 유틸
# -----------------------------
ASSET_ROOT = os.path.dirname(__file__)

def _abs_path(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ASSET_ROOT, p)

def _guess_img_subtype(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"): return "png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"): return "jpeg"
    if lower.endswith(".gif"): return "gif"
    return "png"

def _ensure_inline_files(inline_map: Dict[str, str]) -> List[str]:
    missing = []
    for cid, path in inline_map.items():
        full = _abs_path(path)
        if not os.path.exists(full):
            missing.append(f"{cid}:{path}")
    return missing

def is_noise_row(item: dict) -> bool:
    a = (item.get(COLS["inflow_month"], "") or "").strip()
    if a and any(k in a for k in IGNORE_KEYWORDS):
        return True

    has_company_like = any([
        (item.get(COLS["company"], "") or "").strip(),
        (item.get(COLS["manager"], "") or "").strip(),
        (item.get(COLS["email"], "") or "").strip(),
    ])
    if not has_company_like:
        non_empty = sum(1 for v in item.values() if isinstance(v, str) and v.strip())
        if non_empty <= 3:
            return True

    tail_text = " ".join([
        (item.get(COLS.get("d7_1", "D7"), "") or ""),
        (item.get(COLS.get("m1_1", "M1"), "") or ""),
        (item.get(COLS.get("snapshot", "8/28"), "") or ""),
        (item.get(COLS.get("d7_2", "D7"), "") or ""),
        (item.get(COLS.get("m1_2", "M1"), "") or ""),
    ])
    if "%" in tail_text and not has_company_like:
        return True

    return False

def _nth_indices(headers: List[str], name: str) -> List[int]:
    return [i for i, h in enumerate(headers) if h == name]

def read_sheet(sheet_name: str, mode: str = "data"):
    """시트 전체(A1:Z) 읽어서 dict 리스트 반환. _sheet/_row/_id 포함.
       mode: data | meta | all
    """
    svc = sheets_service()
    rng = f"{sheet_name}!A1:Z"
    res = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=rng).execute()
    values = res.get("values", [])
    if not values:
        return []
    headers, rows = values[0], values[1:]

    d7_idx = _nth_indices(headers, "D7")
    m1_idx = _nth_indices(headers, "M1")

    out = []
    for idx, row in enumerate(rows, start=2):
        item = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
        item["_sheet"] = sheet_name
        item["_row"] = idx
        item["_id"] = f"{sheet_name}:{idx}"

        # 파생 지표
        if len(d7_idx) >= 1:
            item["D7_1"] = row[d7_idx[0]] if d7_idx[0] < len(row) else ""
        if len(m1_idx) >= 1:
            item["M1_1"] = row[m1_idx[0]] if m1_idx[0] < len(row) else ""
        if len(d7_idx) >= 2:
            item["D7_2"] = row[d7_idx[1]] if d7_idx[1] < len(row) else ""
        if len(m1_idx) >= 2:
            item["M1_2"] = row[m1_idx[1]] if m1_idx[1] < len(row) else ""

        noise = is_noise_row(item)
        if noise:
            item["_meta"] = "noise"

        if mode == "data" and noise:
            continue
        if mode == "meta" and not noise:
            continue

        # ⚠️ N시트엔 "2차 컨택 (종료일)"만 있는 케이스가 있으니 보정
        if "2차 컨택" not in item or not item.get("2차 컨택", ""):
            if "2차 컨택 (종료일)" in item and item.get("2차 컨택 (종료일)"):
                item["2차 컨택"] = item.get("2차 컨택 (종료일)", "")

        out.append(item)
    return out

def parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _apply_filters_from_request(data: List[dict]) -> List[dict]:
    """q/equals/sortBy/sortDir 필터를 공통 적용"""
    q = (request.args.get("q") or "").strip().lower()
    if q:
        def hay(x):
            return " ".join([
                x.get(COLS["company"], ""),
                x.get(COLS["manager"], ""),
                x.get(COLS["email"], ""),
                x.get(COLS["memo"], ""),
                x.get(COLS["action"], ""),
                x.get(COLS["phone"], ""),
                x.get(COLS["company_id"], ""),
                x.get(COLS["inflow_month"], ""),
            ]).lower()
        data = [x for x in data if q in hay(x)]

    # equals 필터(임의 키 = 값)
    for key, value in request.args.items():
        if key in ("q", "sortBy", "sortDir", "meta"):
            continue
        if value == "":
            continue
        data = [x for x in data if x.get(key, "") == value]

    sort_by = request.args.get("sortBy")
    sort_dir = (request.args.get("sortDir") or "asc").lower()
    if sort_by:
        def sort_key(x):
            v = x.get(sort_by, "")
            d = parse_date(v)
            return (0, d) if d else (1, v)
        data.sort(key=sort_key)
        if sort_dir == "desc":
            data.reverse()
    return data

def create_gmail_message(to: str, subject: str, html: str) -> dict:
    msg = MIMEText(html, "html", "utf-8")
    msg["To"] = to
    msg["From"] = "me"
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}

def create_inline_message(to: str, subject: str, html: str, inline_images: Dict[str, str]) -> dict:
    root = MIMEMultipart('related')
    root['To'] = to
    root['From'] = 'me'
    root['Subject'] = subject

    alt = MIMEMultipart('alternative')
    root.attach(alt)
    alt.attach(MIMEText(html, 'html', 'utf-8'))

    missing = _ensure_inline_files(inline_images)
    if missing:
        raise FileNotFoundError(f"inline assets not found: {', '.join(missing)}")

    for cid, rel_path in inline_images.items():
        full = _abs_path(rel_path)
        with open(full, 'rb') as f:
            data = f.read()
        subtype = _guess_img_subtype(full)
        img = MIMEImage(data, _subtype=subtype)
        img.add_header('Content-ID', f'<{cid}>')
        img.add_header('Content-Disposition', 'inline', filename=os.path.basename(full))
        root.attach(img)

    raw = base64.urlsafe_b64encode(root.as_bytes()).decode('utf-8')
    return {"raw": raw}

def backoff_send(gmail, message: dict, retries: int = 5):
    delay = 1.0
    for _ in range(retries):
        try:
            return gmail.users().messages().send(userId="me", body=message).execute()
        except HttpError as e:
            if e.resp.status in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError("메일 전송 재시도 초과")

# ---------- 미리보기 전용 유틸 (cid → data URL) ----------
def _file_to_data_url(path: str) -> str:
    full = _abs_path(path)
    mime, _ = mimetypes.guess_type(full)
    if not mime:
        ext = os.path.splitext(full)[1].lower()
        if ext in [".png"]: mime = "image/png"
        elif ext in [".jpg", ".jpeg"]: mime = "image/jpeg"
        elif ext in [".gif"]: mime = "image/gif"
        else: mime = "application/octet-stream"
    with open(full, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def _inline_cid_to_data_urls(html: str, template_name: str) -> str:
    inline_map = TEMPLATE_INLINE_MAP.get(template_name, {})
    if not inline_map:
        return html

    def repl_double(m: re.Match) -> str:
        cid = m.group(1)
        rel = inline_map.get(cid)
        if not rel:
            return m.group(0)
        try:
            return f'src="{_file_to_data_url(rel)}"'
        except Exception:
            return m.group(0)

    def repl_single(m: re.Match) -> str:
        cid = m.group(1)
        rel = inline_map.get(cid)
        if not rel:
            return m.group(0)
        try:
            return f"src='{_file_to_data_url(rel)}'"
        except Exception:
            return m.group(0)

    html = re.sub(r'src\s*=\s*"(?:cid:)([^"]+)"', repl_double, html)
    html = re.sub(r"src\s*=\s*'(?:cid:)([^']+)'", repl_single, html)
    return html

# -----------------------------
# API
# -----------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "trials-backend", "time": datetime.now().isoformat()}

@app.get("/api/health")
def health():
    return {"ok": True}

# ✨ 분리된 목록 엔드포인트 (ALL 제거)
@app.get("/api/trials/y")
def list_trials_y():
    """트라이얼(Y) 시트 전용 목록"""
    meta_mode = (request.args.get("meta") or "exclude").lower()
    if meta_mode == "only":
        mode = "meta"
    elif meta_mode == "include":
        mode = "all"
    else:
        mode = "data"
    data = read_sheet(SHEET_NAME_Y, mode=mode)
    data = _apply_filters_from_request(data)
    return jsonify({"count": len(data), "items": data})

@app.get("/api/trials/n")
def list_trials_n():
    """트라이얼(N) 시트 전용 목록"""
    meta_mode = (request.args.get("meta") or "exclude").lower()
    if meta_mode == "only":
        mode = "meta"
    elif meta_mode == "include":
        mode = "all"
    else:
        mode = "data"
    data = read_sheet(SHEET_NAME_N, mode=mode)
    data = _apply_filters_from_request(data)
    return jsonify({"count": len(data), "items": data})

@app.get("/api/trials/<path:item_id>")
def get_trial(item_id):
    try:
        item_id = urllib.parse.unquote(item_id)
        sheet_name, row_str = item_id.split(":", 1)
        row_num = int(row_str)
    except Exception:
        return jsonify({"error": "invalid id"}), 400

    svc = sheets_service()
    headers = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{sheet_name}!A1:Z1"
    ).execute().get("values", [[]])[0]

    row = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{sheet_name}!A{row_num}:Z{row_num}"
    ).execute().get("values", [[]])[0]

    item = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
    item["_sheet"] = sheet_name
    item["_row"] = row_num
    item["_id"] = item_id

    d7_idx = _nth_indices(headers, "D7")
    m1_idx = _nth_indices(headers, "M1")
    if len(d7_idx) >= 1:
        item["D7_1"] = row[d7_idx[0]] if d7_idx[0] < len(row) else ""
    if len(m1_idx) >= 1:
        item["M1_1"] = row[m1_idx[0]] if m1_idx[0] < len(row) else ""
    if len(d7_idx) >= 2:
        item["D7_2"] = row[d7_idx[1]] if d7_idx[1] < len(row) else ""
    if len(m1_idx) >= 2:
        item["M1_2"] = row[m1_idx[1]] if m1_idx[1] < len(row) else ""

    if is_noise_row(item):
        item["_meta"] = "noise"

    # 보정: N시트의 "2차 컨택 (종료일)" → "2차 컨택" 채워주기
    if "2차 컨택" not in item or not item.get("2차 컨택", ""):
        if "2차 컨택 (종료일)" in item and item.get("2차 컨택 (종료일)"):
            item["2차 컨택"] = item.get("2차 컨택 (종료일)", "")

    return jsonify(item)

@app.route("/api/send", methods=["POST", "OPTIONS"])
def send_mail():
    """
    body: {
      "id": "트라이얼(Y):5",
      "template": "eform_plan_change.html",
      "subject": "(선택) 제목",
      "context": { ... }
    }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(force=True)
    item_id = data.get("id")
    template_name = data.get("template") or "eform_plan_change.html"
    tpl_meta = next((t for t in TEMPLATE_CATALOG if t["id"] == template_name), None)
    if not tpl_meta:
        return jsonify({"error": f"unknown template: {template_name}"}), 400

    subject = data.get("subject") or tpl_meta["default_subject"]
    extra_ctx = data.get("context") or {}

    if item_id:
        item_id = urllib.parse.unquote(item_id)

    resp = get_trial(item_id)
    if isinstance(resp, Response) and resp.status_code != 200:
        return resp
    item = resp.get_json()

    email = (item.get(COLS["email"], "") or "").strip()
    manager = (item.get(COLS["manager"], "") or "").strip()
    company = (item.get(COLS["company"], "") or "").strip()
    if not email:
        return jsonify({"error": "이메일이 없습니다."}), 400

    render_ctx = {
        "manager": manager,
        "company": company,
        "memo": item.get(COLS["memo"], ""),
        "action": item.get(COLS["action"], ""),
        "end_date": item.get(COLS["end_date"], ""),
        "item": item,
        "subject": subject,
        "email": email,  # 일부 템플릿에서 계정 ID로 사용
        **DEFAULT_SENDER_CONTEXT,
        **extra_ctx,
    }

    try:
        html = env.get_template(template_name).render(**render_ctx)
    except Exception as e:
        return jsonify({"error": f"template render error ({template_name}): {e}"}), 500

    gmail = gmail_service()

    inline_map = TEMPLATE_INLINE_MAP.get(template_name, {})
    try:
        if inline_map:
            msg = create_inline_message(email, subject, html, inline_map)
        else:
            msg = create_gmail_message(email, subject, html)
    except FileNotFoundError as e:
        return jsonify({"error": f"inline asset missing: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"mime build error: {e}"}), 500

    try:
        sent = backoff_send(gmail, msg)
        return jsonify({"ok": True, "message_id": sent.get("id")})
    except HttpError as e:
        return jsonify({"error": f"Gmail API error: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"send error: {e}"}), 500

@app.route("/api/preview", methods=["POST", "OPTIONS"])
def preview_mail():
    """
    body: {
      "id": "트라이얼(Y):5",
      "template": "eform_plan_change.html",
      "subject": "(선택) 제목",
      "context": { ... }
    }
    -> { html: "<!doctype html>..." }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(force=True)
    item_id = data.get("id")
    template_name = data.get("template") or "eform_plan_change.html"
    tpl_meta = next((t for t in TEMPLATE_CATALOG if t["id"] == template_name), None)
    if not tpl_meta:
        return jsonify({"error": f"unknown template: {template_name}"}), 400

    subject = data.get("subject") or tpl_meta["default_subject"]
    extra_ctx = data.get("context") or {}

    if item_id:
        item_id = urllib.parse.unquote(item_id)

    resp = get_trial(item_id)
    if isinstance(resp, Response) and resp.status_code != 200:
        return resp
    item = resp.get_json()

    email = (item.get(COLS["email"], "") or "").strip()
    manager = (item.get(COLS["manager"], "") or "").strip()
    company = (item.get(COLS["company"], "") or "").strip()

    render_ctx = {
        "manager": manager,
        "company": company,
        "memo": item.get(COLS["memo"], ""),
        "action": item.get(COLS["action"], ""),
        "end_date": item.get(COLS["end_date"], ""),
        "item": item,
        "subject": subject,
        "email": email,
        **DEFAULT_SENDER_CONTEXT,
        **extra_ctx,
    }

    try:
        html = env.get_template(template_name).render(**render_ctx)
        html = _inline_cid_to_data_urls(html, template_name)  # CID → data URL (배너 포함)
        return jsonify({"html": html})
    except Exception as e:
        return jsonify({"error": f"template render error ({template_name}): {e}"}), 500

@app.get("/api/templates")
def list_templates():
    return jsonify(TEMPLATE_CATALOG)

@app.get("/api/_debug/sheets")
def debug_sheets():
    try:
        svc = sheets_service()
        meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheets = [
            {"title": s["properties"]["title"], "sheetId": s["properties"]["sheetId"]}
            for s in meta.get("sheets", [])
        ]
        out = {"sheets": sheets, "headers": {}}
        for title in [SHEET_NAME_Y, SHEET_NAME_N]:
            try:
                rng = f"{title}!A1:Z1"
                v = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=rng).execute()
                out["headers"][title] = v.get("values", [[]])[0] if v.get("values") else []
            except Exception as e:
                out["headers"][title] = {"error": str(e)}
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"debug failure: {e}"}), 500
    
@app.get("/api/_debug/whoami")
def debug_whoami():
    try:
        svc = gmail_service()
        me = svc.users().getProfile(userId="me").execute()
        return jsonify({"email": me.get("emailAddress")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)