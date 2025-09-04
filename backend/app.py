import os
import base64
import time
from datetime import datetime
from email.mime.text import MIMEText
import urllib.parse

from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, make_response
from flask_cors import CORS
from jinja2 import Environment, FileSystemLoader

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# -----------------------------
# 환경설정
# -----------------------------
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME_Y = os.getenv("SHEET_NAME_Y", "트라이얼(Y)")
SHEET_NAME_N = os.getenv("SHEET_NAME_N", "트라이얼(N)")
PORT = int(os.getenv("PORT", 8080))
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000")

# 🔹 스킵 키워드(유입월 컬럼에 포함되면 메타/구분 행으로 판단)
IGNORE_KEYWORDS = [k.strip() for k in os.getenv("IGNORE_KEYWORDS", "종료,합계,요약").split(",") if k.strip()]

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
    "d7_1": "D7",
    "m1_1": "M1",
    "memo": "상담내용",
    "action": "후속조치",
    "end_date": "종료일",
    "d7_2": "D7",
    "m1_2": "M1",
    "snapshot": "8/28",
}

# 템플릿 로더
env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "email_templates")))
env.globals["now"] = lambda: datetime.now().strftime("%Y-%m-%d")

# 템플릿 관련 설정

TEMPLATE_CATALOG = [
    # 원본 3종
    {"id": "eform_plan_change_original.html",   "label": "[이폼사인] 요금제 변경 방법 안내(원본)", "default_subject": "[이폼사인] 요금제 변경 방법 안내"},
    {"id": "eform_pay_prepaid_add_original.html","label": "[이폼사인] 충전형 결제 방법 안내 (추가 구매하기/원본)", "default_subject": "[이폼사인] 충전형 결제 방법 안내 (추가 구매하기)"},
    {"id": "eform_pay_prepaid_buy_original.html","label": "[이폼사인] 충전형 결제 방법 안내 (구매하기/원본)", "default_subject": "[이폼사인] 충전형 결제 방법 안내 (구매하기)"},
]

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

app = Flask(__name__)

# -----------------------------
# CORS (프리플라이트 포함) 설정 
# -----------------------------
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


# -----------------------------
# 유틸
# -----------------------------
# 🔹 요약/구분/합계 행 제외 휴리스틱
def is_noise_row(item: dict) -> bool:
    """
    스프레드시트 중간의 섹션/요약/합계/퍼센트 행을 제외.
    - 유입월에 IGNORE_KEYWORDS 포함
    - 회사명/담당자/이메일 모두 비고(핵심 식별 없음) + 전체 값 거의 없음
    - 뒤쪽 지표열에 %가 다수인데 핵심 식별이 없음
    """
    # 1) A열(유입월)에 구분 키워드
    a = (item.get(COLS["inflow_month"], "") or "").strip()
    if a and any(k in a for k in IGNORE_KEYWORDS):
        return True

    # 2) 핵심 식별 정보가 없음(회사명/담당자/이메일 모두 비어있음) + 전체 비어있는 값이 대부분
    has_company_like = any([
        (item.get(COLS["company"], "") or "").strip(),
        (item.get(COLS["manager"], "") or "").strip(),
        (item.get(COLS["email"], "") or "").strip(),
    ])
    if not has_company_like:
        non_empty = sum(1 for v in item.values() if isinstance(v, str) and v.strip())
        if non_empty <= 3:
            return True

    # 3) 퍼센트 위주의 요약 행: 지표 필드 텍스트에 %가 보이는데 핵심 식별이 없음
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


# (기존) def read_sheet(sheet_name: str):
# (변경) 모드 파라미터 추가: data | meta | all
def read_sheet(sheet_name: str, mode: str = "data"):
    svc = sheets_service()
    rng = f"{sheet_name}!A1:Z"
    res = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=rng).execute()
    values = res.get("values", [])
    if not values:
        return []
    headers, rows = values[0], values[1:]

    # 헤더에서 D7/M1 위치 찾아두기
    d7_idx = _nth_indices(headers, "D7")
    m1_idx = _nth_indices(headers, "M1")

    out = []
    for idx, row in enumerate(rows, start=2):
        item = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
        item["_sheet"] = sheet_name
        item["_row"] = idx
        item["_id"] = f"{sheet_name}:{idx}"

        # D7/M1 파생 키 추가
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

        out.append(item)
    return out


def parse_date(s: str):
    """문자열 -> 날짜 파싱(여러 포맷 지원). 실패시 None"""
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def create_gmail_message(to: str, subject: str, html: str) -> dict:
    msg = MIMEText(html, "html", "utf-8")
    msg["To"] = to
    msg["From"] = "me"
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
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


def _nth_indices(headers: list[str], name: str) -> list[int]:
    return [i for i, h in enumerate(headers) if h == name]


# -----------------------------
# API
# -----------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "trials-backend", "time": datetime.now().isoformat()}

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/trials")
def list_trials():
    """
    두 시트 병합 후 서버에서 1차 필터/정렬.
    쿼리 파라미터:
      - meta: exclude(기본) | include | only
      - q: 키워드(회사명/담당자/이메일/상담내용/후속조치/연락처/회사ID/유입월)
      - sheet: ALL|Y|N  (기본 ALL)
      - sortBy: 정렬 키 (실제 시트 헤더)
      - sortDir: asc|desc
      - 그 외: 실제 헤더명을 키로 보내면 equals 필터
    """
    # 🔹 meta 모드
    meta_mode = (request.args.get("meta") or "exclude").lower()
    if meta_mode == "only":
        mode = "meta"
    elif meta_mode == "include":
        mode = "all"
    else:
        mode = "data"

    # 🔹 모드에 맞춰 로드
    data = read_sheet(SHEET_NAME_Y, mode=mode) + read_sheet(SHEET_NAME_N, mode=mode)

    # 시트 필터
    sheet_filter = (request.args.get("sheet") or "ALL").upper()
    if sheet_filter == "Y":
        data = [x for x in data if x.get("_sheet") == SHEET_NAME_Y]
    elif sheet_filter == "N":
        data = [x for x in data if x.get("_sheet") == SHEET_NAME_N]

    # 키워드 검색 (유입월도 포함해 메타 제목 검색 가능)
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
                x.get(COLS["inflow_month"], ""),  # 🔹 추가
            ]).lower()
        data = [x for x in data if q in hay(x)]

    # 동적 equals 필터
    for key, value in request.args.items():
        if key in ("q", "sheet", "sortBy", "sortDir", "meta"):
            continue
        if value == "":
            continue
        data = [x for x in data if x.get(key, "") == value]

    # 정렬
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

    # 🔹 헤더에서 D7/M1 위치 찾고 파생 키 부여
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

    return jsonify(item)


@app.get("/api/trials/meta")
def list_meta_only():
    data = read_sheet(SHEET_NAME_Y, mode="meta") + read_sheet(SHEET_NAME_N, mode="meta")
    return jsonify({"count": len(data), "items": data})


@app.route("/api/send", methods=["POST", "OPTIONS"])
def send_mail():
    """
    body: {
      "id": "트라이얼(Y):5",
      "template": "eform_plan_change_clean.html",  # TEMPLATE_CATALOG의 id 중 하나
      "subject": "(선택) 제목. 없으면 catalog 기본 제목",
      "context": { ... }  # (선택) 템플릿 변수 추가 (DEFAULT_SENDER_CONTEXT와 병합)
    }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(force=True)
    item_id = data.get("id")

    # 1) 템플릿 id 확인 및 기본값
    template_name = data.get("template") or "eform_plan_change_clean.html"
    tpl_meta = next((t for t in TEMPLATE_CATALOG if t["id"] == template_name), None)
    if not tpl_meta:
        return jsonify({"error": f"unknown template: {template_name}"}), 400

    # 2) 제목 기본값(카탈로그) 적용
    subject = data.get("subject") or tpl_meta["default_subject"]

    # 3) 추가 컨텍스트
    extra_ctx = data.get("context") or {}

    # id URL 디코딩
    if item_id:
        item_id = urllib.parse.unquote(item_id)

    # 4) 상세 조회 재사용
    resp = get_trial(item_id)
    if isinstance(resp, Response) and resp.status_code != 200:
        return resp
    item = resp.get_json()

    email = (item.get(COLS["email"], "") or "").strip()
    manager = (item.get(COLS["manager"], "") or "").strip()
    company = (item.get(COLS["company"], "") or "").strip()
    if not email:
        return jsonify({"error": "이메일이 없습니다."}), 400

    # 5) 렌더링 컨텍스트(발신자 기본값 + 추가 컨텍스트 사용자값 우선)
    render_ctx = {
        "manager": manager,
        "company": company,
        "memo": item.get(COLS["memo"], ""),
        "action": item.get(COLS["action"], ""),
        "end_date": item.get(COLS["end_date"], ""),
        "item": item,
        "subject": subject,
        **DEFAULT_SENDER_CONTEXT,  # 기본 발신자 정보
        **extra_ctx,               # 사용자가 넘긴 값이 있으면 덮어씀
    }

    # 6) 템플릿 렌더링
    html = env.get_template(template_name).render(**render_ctx)

    # 7) 전송
    gmail = gmail_service()
    msg = create_gmail_message(email, subject, html)
    try:
        sent = backoff_send(gmail, msg)
        return jsonify({"ok": True, "message_id": sent.get("id")})
    except HttpError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.get("/api/templates")
def list_templates():
    return jsonify(TEMPLATE_CATALOG)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)