# AI Content Pipeline

Ứng dụng tự động hoá toàn bộ luồng **tìm kiếm web → tổng hợp nghiên cứu → tạo nội dung mạng xã hội → đăng bài** lên Facebook và TikTok.

Hỗ trợ hai chế độ vận hành:

| Chế độ | Mô tả | Cần Anthropic API key? |
|--------|-------|----------------------|
| **Streamlit UI** | Giao diện web đầy đủ tính năng | Có (hoặc dùng mock) |
| **Claude Code Agent** | Claude Code đóng vai LLM, không cần credit API riêng | **Không** |

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
3. [Cấu trúc dự án](#cấu-trúc-dự-án)
4. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
5. [Cài đặt](#cài-đặt)
6. [Cấu hình biến môi trường](#cấu-hình-biến-môi-trường)
7. [Chạy ứng dụng Streamlit](#chạy-ứng-dụng-streamlit)
8. [Chế độ Claude Code Agent](#chế-độ-claude-code-agent)
9. [Tích hợp API](#tích-hợp-api)
10. [Tạo video TikTok](#tạo-video-tiktok)
11. [Chế độ Mock](#chế-độ-mock)
12. [Cơ sở dữ liệu](#cơ-sở-dữ-liệu)
13. [Kiểm thử](#kiểm-thử)
14. [Linting & Code Quality](#linting--code-quality)
15. [Giới hạn & lưu ý](#giới-hạn--lưu-ý)
16. [Xử lý sự cố](#xử-lý-sự-cố)
17. [Thư viện chính](#thư-viện-chính)

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Tìm kiếm web tự động** | Tích hợp Tavily MCP server (qua `npx`), thu thập tối đa 10 nguồn liên quan |
| **Trích xuất nội dung** | trafilatura + BeautifulSoup4 trích xuất văn bản từ bài báo |
| **Khử trùng lặp nguồn** | Loại bỏ các nguồn trùng URL hoặc tiêu đề tương tự |
| **Tổng hợp nghiên cứu** | LLM tóm tắt, trích dẫn nguồn `[S1]`, `[S2]`, phân tích điểm không chắc chắn |
| **Tạo nội dung mạng xã hội** | Bài Facebook và kịch bản TikTok riêng biệt, phù hợp với từng nền tảng |
| **Text-to-Speech** | edge-tts tạo giọng đọc MP3 (tiếng Việt & tiếng Anh) |
| **Tạo video dọc** | FFmpeg ghép ảnh + âm thanh thành MP4 1080×1920 (định dạng TikTok) |
| **Chỉnh sửa trước khi đăng** | Sửa nội dung trực tiếp trên giao diện trước khi publish |
| **Đăng bài lên Facebook** | Graph API v19.0; hỗ trợ mock khi thiếu token |
| **Đăng video lên TikTok** | TikTok Open APIs v2; upload private, hỗ trợ mock |
| **Lịch sử job** | SQLite lưu toàn bộ lịch sử chạy, trạng thái, kết quả đăng bài |
| **Đa ngôn ngữ** | Hỗ trợ tiếng Việt và tiếng Anh đầu ra |
| **Chế độ Mock** | Chạy demo không cần API key — tất cả bước đều có dữ liệu mẫu |
| **Claude Code Agent** | Dùng Claude Code thay LLM — không tiêu tốn Anthropic API credits |

---

## Kiến trúc tổng quan

### Chế độ Streamlit UI (có Anthropic API key)

```
┌────────────────────────────────────────────────┐
│              Streamlit Web UI                  │
│  ┌─────────────────┐   ┌────────────────────┐  │
│  │  research_page  │   │   history_page     │  │
│  └────────┬────────┘   └────────────────────┘  │
└───────────┼────────────────────────────────────┘
            │
   ┌────────▼────────┐    ┌──────────────┐
   │ research_service│───►│ search_service│ ──► Tavily MCP (npx)
   └────────┬────────┘    └──────────────┘
            │
   ┌────────▼──────────┐
   │ content_extractor │ ──► trafilatura / BeautifulSoup4
   └────────┬──────────┘
            │
   ┌────────▼────────┐
   │   llm_service   │ ──► Anthropic Claude API  ← cần API credits
   └────────┬────────┘
            │
   ┌────────▼──────────────────┐
   │ content_generation_service│ ──► Anthropic Claude API  ← cần API credits
   └────────┬──────────────────┘
            │
   ┌────────▼──────────┐   ┌──────────────┐
   │   video_builder   │──►│  tts_service │ ──► edge-tts
   └────────┬──────────┘   └──────────────┘
            │
          FFmpeg ──► Publishers (Facebook / TikTok) ──► SQLite
```

### Chế độ Claude Code Agent (không cần API credits)

```
Claude Code (dùng Pro subscription)
         │
         ├── 1. Bash: python pipeline.py gather --topic "..."
         │              │
         │         Tavily MCP ──► Web extraction ──► sources.json
         │
         ├── 2. Claude Code đọc sources.json và tổng hợp nghiên cứu
         │         (LLM chạy trong Claude Code, không gọi Anthropic API)
         │
         ├── 3. Claude Code viết nội dung Facebook + TikTok
         │         (lưu vào content.json)
         │
         └── 4. Bash: python pipeline.py publish --content-file content.json
                        │
                   Facebook Graph API ──► Bài đăng
```

---

## Cấu trúc dự án

```
ai-content-pipeline/
├── app.py                              # Entry point Streamlit
├── pipeline.py                         # CLI cho Claude Code agent mode
├── CLAUDE.md                           # Hướng dẫn Claude Code agent workflow
├── requirements.txt                    # Thư viện Python
├── pyproject.toml                      # pytest & ruff config
├── .env                                # Biến môi trường (tạo từ mẫu bên dưới)
├── .streamlit/
│   └── config.toml                     # Cấu hình Streamlit (port, headless)
│
├── src/
│   ├── config.py                       # Đọc ENV, tạo thư mục output
│   │
│   ├── models/
│   │   ├── schemas.py                  # Pydantic v2: SourceItem, ResearchResult,
│   │   │                               #   FacebookPost, TikTokPackage, PipelineJob...
│   │   └── db_models.py                # SQLAlchemy ORM: JobRecord, SourceRecord,
│   │                                   #   PublishRecord, get_session_factory()
│   │
│   ├── services/
│   │   ├── search_service.py           # Tavily MCP server (npx) / mock search
│   │   ├── research_service.py         # Điều phối pipeline nghiên cứu
│   │   ├── content_extractor.py        # trafilatura + BS4 extraction
│   │   ├── source_deduplicator.py      # Khử trùng lặp URL & tiêu đề
│   │   ├── llm_service.py              # Claude API wrapper (retry + JSON parse)
│   │   ├── content_generation_service.py # Tạo nội dung Facebook & TikTok
│   │   ├── tts_service.py              # edge-tts → MP3
│   │   ├── video_builder.py            # PIL + FFmpeg → MP4 dọc
│   │   └── storage_service.py          # SQLAlchemy CRUD (list_jobs, save_job...)
│   │
│   ├── publishers/
│   │   ├── base.py                     # Abstract BasePublisher
│   │   ├── facebook_publisher.py       # Meta Graph API v19.0
│   │   └── tiktok_publisher.py         # TikTok Open APIs v2
│   │
│   ├── ui/
│   │   ├── components.py               # Sidebar trạng thái API
│   │   ├── research_page.py            # Form nhập liệu + hiển thị kết quả
│   │   └── history_page.py             # Lịch sử 50 job gần nhất
│   │
│   ├── prompts/
│   │   ├── __init__.py                 # load_prompt() helper
│   │   ├── research_system_prompt.txt  # Prompt tổng hợp nghiên cứu
│   │   └── content_generation_prompt.txt # Prompt tạo nội dung social
│   │
│   └── utils/
│       ├── ffmpeg_utils.py             # check_ffmpeg(), run_ffmpeg()
│       ├── text_utils.py               # truncate(), strip_html(), normalize_whitespace()
│       └── url_utils.py                # extract_domain(), is_valid_url(), normalize_url()
│
├── tests/
│   ├── test_schemas.py                 # Kiểm tra Pydantic schema
│   ├── test_deduplicator.py            # Kiểm tra logic khử trùng lặp
│   ├── test_llm_parsing.py             # Kiểm tra parse kết quả LLM + mock mode
│   └── test_publishers_mock.py         # Kiểm tra publisher mock & bảo mật
│
├── data/                               # SQLite database (tự tạo)
│   └── app.db
│
└── output/                             # File đầu ra (tự tạo)
    ├── audio/                          # {job_id}_narration.mp3
    ├── images/                         # {job_id}_scene{N}.jpg
    ├── videos/                         # {job_id}_clip{N}.mp4 + {job_id}_final.mp4
    └── subtitles/                      # (dành cho tương lai)
```

File tạm thời (được git-ignore):

```
ai-content-pipeline/
├── sources.json    # Kết quả gather — input cho Claude Code
└── content.json    # Nội dung do Claude Code tạo — input cho publish
```

---

## Yêu cầu hệ thống

### Python
- Python **3.11** trở lên

### Node.js & npx (để chạy Tavily MCP server)
- Tải tại: https://nodejs.org/
- Kiểm tra: `node --version` và `npx --version`
- Tavily MCP server tự tải qua `npx -y tavily-mcp@latest` khi chạy lần đầu

### FFmpeg (tùy chọn — chỉ cần khi tạo video TikTok)
- Tải tại: https://ffmpeg.org/download.html
- Thêm vào PATH hệ thống, kiểm tra: `ffmpeg -version`
- Nếu thiếu FFmpeg, ứng dụng vẫn chạy bình thường — bước tạo video sẽ bị bỏ qua

### Claude Code (chỉ cần cho chế độ Agent)
- Claude Code CLI đã cài và đăng nhập bằng tài khoản Claude Pro/Max
- Kiểm tra: `claude --version`

---

## Cài đặt

```bash
# Bước 1: Vào thư mục dự án
cd ai-content-pipeline

# Bước 2: Tạo và kích hoạt môi trường ảo
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Bước 3: Cài thư viện
pip install -r requirements.txt

# Bước 4: Tạo file .env
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

---

## Cấu hình biến môi trường

Tạo file `.env` trong thư mục `ai-content-pipeline/`. Tất cả biến đều **tùy chọn** — ứng dụng chạy ở chế độ mock khi thiếu key.

```env
# ─── Ứng dụng ──────────────────────────────────────────────────
APP_ENV=development
DATABASE_URL=sqlite:///data/app.db
OUTPUT_DIR=output

# ─── Tìm kiếm web ──────────────────────────────────────────────
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
# Lấy tại: https://app.tavily.com/
# Khi thiếu: dùng 5 bài báo mẫu về AI

MAX_SOURCES=5
MAX_EXTRACTED_CHARS_PER_SOURCE=8000

# ─── Claude LLM (chỉ cần cho chế độ Streamlit UI) ─────────────
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
# Lấy tại: https://console.anthropic.com/ (cần credit riêng)
# Không cần khi dùng chế độ Claude Code Agent
# Khi thiếu: dùng nội dung mẫu cố định (mock mode)

ANTHROPIC_MODEL=claude-sonnet-4-6
# Các lựa chọn: claude-opus-4-8, claude-haiku-4-5-20251001

# ─── Facebook ──────────────────────────────────────────────────
FACEBOOK_PAGE_ID=123456789012345
# ID của Facebook Page (Page Settings → About → Page ID)

FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxx...
# Page Access Token có quyền pages_manage_posts (hết hạn sau 60 ngày)

# ─── TikTok ────────────────────────────────────────────────────
TIKTOK_CLIENT_KEY=awxxxxxxxxxxxxxx
TIKTOK_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TIKTOK_ACCESS_TOKEN=act.xxxxxxxx...

# ─── Bật đăng bài thật ─────────────────────────────────────────
ENABLE_REAL_PUBLISHING=false
# false: mock, không gọi API đăng bài
# true: gọi Facebook Graph API và TikTok Open API thật sự
```

> **Ghi chú về `ANTHROPIC_API_KEY`:** Đây là credit tại console.anthropic.com — hoàn toàn tách biệt với gói đăng ký Claude Pro/Max. Nếu bạn dùng Claude Code Agent mode (xem bên dưới), biến này không cần thiết.

---

## Chạy ứng dụng Streamlit

```bash
# Từ thư mục ai-content-pipeline/
streamlit run app.py
```

Mở trình duyệt tại **http://localhost:8501**

```bash
# Chạy headless (server không mở browser)
streamlit run app.py --server.headless true

# Đổi port nếu 8501 bị chiếm
streamlit run app.py --server.port 8502
```

### Hướng dẫn sử dụng UI

1. **Nhập chủ đề** vào ô "Chủ đề / Prompt" — ví dụ: *"Trí tuệ nhân tạo trong giáo dục 2025"*
2. **Chọn ngôn ngữ** đầu ra: Tiếng Việt hoặc English
3. **Chọn số nguồn** muốn tổng hợp (3–10)
4. **Tích chọn** loại nội dung cần tạo: Facebook, TikTok, hoặc cả hai
5. Nhấn **"Bắt đầu nghiên cứu"**

Kết quả hiển thị trong **5 tab**:

| Tab | Nội dung |
|-----|----------|
| **Research** | Tiêu đề, tóm tắt ngắn, điểm chính có trích dẫn `[S1]`, tóm tắt chi tiết |
| **Facebook Draft** | Tiêu đề, nội dung bài viết, hashtag — chỉnh sửa được |
| **TikTok Draft** | Hook, kịch bản đọc, caption, hashtag, danh sách cảnh — chỉnh sửa được |
| **Video** | Xem trước video MP4 (nếu FFmpeg đã cài) |
| **Publish** | Nút đăng lên Facebook / TikTok sau khi xác nhận checkbox |

---

## Chế độ Claude Code Agent

Chế độ này cho phép chạy pipeline **không cần Anthropic API credits** — Claude Code (dùng subscription Claude Pro/Max của bạn) tự xử lý phần tổng hợp và viết nội dung.

### Cách dùng nhanh — Slash command

Mở Claude Code và gõ:

```
/tao-noi-dung <chủ đề>
```

Ví dụ:

```
/tao-noi-dung Bitcoin và xu hướng crypto 2025
/tao-noi-dung AI thay thế lập trình viên
/tao-noi-dung Thị trường bất động sản Hà Nội quý 3 2025
```

Claude Code sẽ tự động:
1. Chạy `pipeline.py gather` để tìm kiếm và trích xuất nguồn
2. Tổng hợp nghiên cứu từ các nguồn tìm được
3. Viết bài Facebook và kịch bản TikTok
4. Lưu kết quả vào `content.json`
5. Chạy `pipeline.py publish` để đăng lên Facebook

### Chạy thủ công từng bước

**Bước 1 — Thu thập nguồn** (không gọi LLM):

```bash
cd ai-content-pipeline
python pipeline.py gather --topic "chủ đề của bạn" --output sources.json
```

Tùy chọn:

```bash
python pipeline.py gather \
  --topic "Bitcoin 2025" \
  --language vi \
  --max-sources 5 \
  --output sources.json
```

**Bước 2 — Claude Code tổng hợp và tạo nội dung**

Trong Claude Code:
```
Đọc file ai-content-pipeline/sources.json và tạo bài Facebook + TikTok về chủ đề này, lưu vào ai-content-pipeline/content.json
```

**Bước 3 — Đăng lên Facebook**:

```bash
python pipeline.py publish --content-file content.json
```

### Cấu hình cần thiết cho Agent mode

Trong `.env`, chỉ cần:

```env
TAVILY_API_KEY=tvly-...          # Tìm kiếm web
FACEBOOK_PAGE_ID=...             # Đăng bài
FACEBOOK_PAGE_ACCESS_TOKEN=...   # Đăng bài
ENABLE_REAL_PUBLISHING=true      # Bật đăng thật

# ANTHROPIC_API_KEY không cần thiết
```

### So sánh hai chế độ

| | Streamlit UI | Claude Code Agent |
|--|-------------|------------------|
| **Giao diện** | Web browser | Terminal / IDE |
| **Anthropic API key** | Cần (hoặc mock) | Không cần |
| **Chi phí LLM** | Tính theo token | Dùng Pro subscription |
| **Chỉnh sửa nội dung** | Trực tiếp trên UI | Yêu cầu Claude sửa |
| **Lịch sử job** | SQLite database | File sources/content.json |
| **Tạo video TikTok** | Có | Không (chỉ script) |

---

## Luồng xử lý pipeline (Streamlit mode)

```
1. Người dùng nhập prompt
        │
2. Tìm kiếm web [Tavily MCP]
        │
3. Tạo SourceItem (S1, S2, ..., Sn)
        │
4. Khử trùng lặp nguồn
        │
5. Trích xuất nội dung từng URL [trafilatura / BS4]
        │
6. Lọc nguồn chất lượng thấp (< 100 ký tự)
        │
7. Tổng hợp nghiên cứu [Claude API]
   ├── Output: title, summaries, key_points, citations [S1]..[Sn]
   └── Gắn flag uncertainties / safety_notes
        │
8. Tạo nội dung mạng xã hội [Claude API]
   ├── Facebook: tiêu đề + bài viết + hashtag + trích dẫn nguồn
   └── TikTok: hook + kịch bản (30-45 giây) + caption + scenes
        │
9. Tạo video TikTok [edge-tts + FFmpeg]
        │
10. Lưu job vào SQLite
        │
11. Hiển thị kết quả trong 5 tab → Đăng bài
```

---

## Tích hợp API

### Tavily (Tìm kiếm web)

- **Cơ chế:** Tavily MCP server khởi chạy qua `npx -y tavily-mcp@latest`
- **Yêu cầu:** Node.js + npx, biến `TAVILY_API_KEY`
- **Khi thiếu key:** Trả về 5 bài báo mẫu về AI

### Anthropic Claude (Streamlit mode)

- **Model mặc định:** `claude-sonnet-4-6`
- **Gọi 2 lần mỗi pipeline:** tổng hợp nghiên cứu + tạo nội dung social
- **Output format:** JSON (tự parse, retry khi lỗi)
- **Khi thiếu key:** Trả về template mẫu

**JSON output — Research:**
```json
{
  "title": "Tiêu đề nghiên cứu",
  "short_summary": "Tóm tắt 1-2 câu",
  "key_points": ["Điểm 1 [S1]", "Điểm 2 [S2]"],
  "detailed_summary": "Tóm tắt chi tiết với trích dẫn...",
  "source_ids_used": ["S1", "S2"],
  "uncertainties": ["Điều cần làm rõ thêm"],
  "safety_notes": []
}
```

**JSON output — Social Content:**
```json
{
  "facebook": {
    "title": "Tiêu đề bài viết",
    "body": "Nội dung bài viết...",
    "hashtags": ["#AI", "#CongNghe"],
    "source_references": ["[S1] https://..."]
  },
  "tiktok": {
    "hook": "Mở đầu thu hút trong 1-3 giây",
    "narration_script": "Kịch bản đọc 30-45 giây...",
    "caption": "Caption đăng kèm video",
    "hashtags": ["#TikTok", "#AI"],
    "scenes": [
      {"scene_number": 1, "duration_seconds": 3, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 2, "duration_seconds": 15, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 3, "duration_seconds": 10, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 4, "duration_seconds": 7, "narration": "...", "on_screen_text": "..."}
    ],
    "call_to_action": "Follow để cập nhật thêm!"
  }
}
```

### Facebook Graph API

- **Phiên bản:** v19.0
- **Endpoint:** `POST /v19.0/{PAGE_ID}/feed`
- **Yêu cầu:** Page Access Token có quyền `pages_manage_posts`

### TikTok Open APIs

- **Phiên bản:** v2
- **Trạng thái sau upload:** `uploaded_private`
- **Yêu cầu:** OAuth 2.0 access token, app đã qua TikTok review

---

## Tạo video TikTok

### Yêu cầu
- FFmpeg đã cài và có trong PATH

### Quy trình

```
TikTokPackage (scenes + narration_script)
    │
    ├── tts_service: narration_script → MP3
    │   ├── Tiếng Việt: vi-VN-NamMinhNeural
    │   └── Tiếng Anh:  en-US-AriaNeural
    │
    ├── Cho mỗi scene:
    │   ├── PIL: tạo ảnh 1080×1920 px
    │   ├── Vẽ on_screen_text lên ảnh
    │   └── FFmpeg: ảnh → clip MP4 (duration = scene.duration_seconds)
    │
    ├── FFmpeg: ghép tất cả clips
    └── FFmpeg: mix video + audio (narration MP3)
```

### File đầu ra

```
output/
├── audio/{job_id}_narration.mp3
├── images/{job_id}_scene1.jpg  ...
└── videos/{job_id}_final.mp4   ← dùng để đăng TikTok
```

---

## Chế độ Mock

Ứng dụng hoạt động đầy đủ **mà không cần bất kỳ API key nào**:

| Service | Hành vi khi thiếu key |
|---------|----------------------|
| Tavily MCP | 5 bài báo mẫu về AI (tiếng Việt) |
| Claude LLM | Template nghiên cứu mẫu |
| Claude content gen | Template Facebook + TikTok mẫu |
| Facebook publisher | `status="mock_published"`, không gọi API |
| TikTok publisher | `status="mock_published"`, không gọi API |
| FFmpeg | Bỏ qua bước tạo video |

Sidebar hiển thị trạng thái: ✅ Đã cấu hình / ⚠️ Mock mode

---

## Cơ sở dữ liệu

SQLite tại `data/app.db`, tự tạo khi khởi động lần đầu.

### Bảng `jobs`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | TEXT (UUID) | Primary key |
| `prompt` | TEXT | Chủ đề người dùng nhập |
| `language` | TEXT | `vi` hoặc `en` |
| `status` | TEXT | `running` / `done` / `failed` |
| `created_at` | DATETIME | Thời điểm tạo |
| `research_title` | TEXT | Tiêu đề nghiên cứu |
| `facebook_body` | TEXT | Nội dung bài Facebook |
| `tiktok_script` | TEXT | Kịch bản TikTok |
| `video_path` | TEXT | Đường dẫn file MP4 |

### Bảng `sources`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `job_id` | TEXT | FK → jobs.id |
| `source_id` | TEXT | S1, S2, ... |
| `title` | TEXT | Tiêu đề bài viết |
| `url` | TEXT | URL nguồn |
| `extraction_status` | TEXT | `success` / `partial` / `failed` |

### Bảng `publish_results`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `job_id` | TEXT | FK → jobs.id |
| `platform` | TEXT | `facebook` / `tiktok` |
| `status` | TEXT | `published` / `mock_published` / `failed` |
| `external_post_id` | TEXT | ID bài đăng trên nền tảng |
| `external_url` | TEXT | URL bài đã đăng |

---

## Kiểm thử

```bash
# Chạy toàn bộ test
pytest

# Chi tiết
pytest -v

# Một file cụ thể
pytest tests/test_deduplicator.py -v
```

| File | Test gì |
|------|---------|
| `test_schemas.py` | Pydantic v2 schema validation |
| `test_deduplicator.py` | Khử trùng lặp URL và tiêu đề |
| `test_llm_parsing.py` | Parse JSON từ Claude, mock mode |
| `test_publishers_mock.py` | Mock publish, không rò rỉ secrets |

---

## Linting & Code Quality

```bash
ruff check .         # Kiểm tra
ruff check . --fix   # Auto-fix
```

---

## Giới hạn & lưu ý

| Giới hạn | Chi tiết |
|----------|----------|
| **Trích xuất nội dung** | Không truy cập được trang yêu cầu đăng nhập, paywall, hoặc CAPTCHA |
| **Ký tự mỗi nguồn** | Tối đa 8.000 ký tự (cấu hình `MAX_EXTRACTED_CHARS_PER_SOURCE`) |
| **TikTok upload** | Video upload ở trạng thái `uploaded_private`, chưa public ngay |
| **Facebook token** | Page Access Token hết hạn sau 60 ngày, cần refresh định kỳ |
| **Video quality** | Độ phân giải cố định 1080×1920, font Arial |
| **Concurrency** | Mỗi lần chỉ chạy một pipeline, không song song nhiều job |
| **Nội dung** | Luôn review trước khi đăng — không copy nguyên văn bài nguồn |

---

## Xử lý sự cố

### `streamlit: command not found`

```bash
.venv\Scripts\activate      # Kích hoạt lại venv
python -m streamlit run app.py
```

### Lỗi Anthropic API 400 "credit balance is too low"

Có hai hướng giải quyết:
- **Nạp credit** tại https://console.anthropic.com/
- **Dùng Claude Code Agent mode** — chạy `/tao-noi-dung` từ Claude Code để không cần API credits

### Video không được tạo

```bash
ffmpeg -version   # Kiểm tra FFmpeg
# Nếu thiếu: https://ffmpeg.org/download.html → thêm vào PATH → restart terminal
```

### Không thấy bài đăng trên Facebook

1. Kiểm tra `ENABLE_REAL_PUBLISHING=true` trong `.env`
2. Kiểm tra `FACEBOOK_PAGE_ID` và `FACEBOOK_PAGE_ACCESS_TOKEN`
3. Token cần quyền `pages_manage_posts` và `pages_read_engagement`
4. Thử lại token tại Meta Graph API Explorer

### `pipeline.py gather` không tìm được nguồn tốt

Nhiều trang tin tức lớn (Reuters, Bloomberg, Investing.com) chặn scraping. Pipeline vẫn hoạt động bằng cách dùng snippet từ kết quả Tavily. Kết quả tổng hợp sẽ ít chi tiết hơn nhưng vẫn có giá trị.

### Port 8501 đang bị dùng

```bash
streamlit run app.py --server.port 8502
```

---

## Thư viện chính

| Thư viện | Mục đích |
|----------|---------|
| streamlit | Web UI framework |
| pydantic ≥2.7 | Data validation |
| sqlalchemy ≥2.0 | ORM + SQLite |
| anthropic | Claude API (Streamlit mode) |
| mcp | MCP client — giao tiếp Tavily MCP server |
| trafilatura | Article extraction |
| beautifulsoup4 | HTML parsing fallback |
| edge-tts | Text-to-speech |
| Pillow | Image generation |
| httpx | HTTP client |
| python-dotenv | ENV file loading |
| pytest | Testing |
| ruff | Linting |

---

## License

MIT License
