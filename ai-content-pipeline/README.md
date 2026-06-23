# AI Content Pipeline

Ứng dụng tự động hoá toàn bộ luồng từ **tìm kiếm web → tổng hợp nghiên cứu bằng LLM → tạo nội dung mạng xã hội → đăng bài** lên Facebook và TikTok, xây dựng trên Streamlit + Claude API.

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
3. [Luồng xử lý pipeline](#luồng-xử-lý-pipeline)
4. [Cấu trúc dự án](#cấu-trúc-dự-án)
5. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
6. [Cài đặt](#cài-đặt)
7. [Cấu hình biến môi trường](#cấu-hình-biến-môi-trường)
8. [Chạy ứng dụng](#chạy-ứng-dụng)
9. [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
10. [Tích hợp API](#tích-hợp-api)
11. [Tạo video TikTok](#tạo-video-tiktok)
12. [Chế độ Mock](#chế-độ-mock)
13. [Cơ sở dữ liệu](#cơ-sở-dữ-liệu)
14. [Kiểm thử](#kiểm-thử)
15. [Linting & Code Quality](#linting--code-quality)
16. [File đầu ra](#file-đầu-ra)
17. [Giới hạn & lưu ý](#giới-hạn--lưu-ý)
18. [Xử lý sự cố thường gặp](#xử-lý-sự-cố-thường-gặp)

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Tìm kiếm web tự động** | Tích hợp Tavily MCP server (qua `npx`), tìm và thu thập tối đa 10 nguồn liên quan |
| **Trích xuất nội dung** | Dùng trafilatura + BeautifulSoup4 để trích xuất văn bản từ bài báo |
| **Khử trùng lặp nguồn** | Loại bỏ các nguồn trùng URL hoặc tiêu đề tương tự |
| **Tổng hợp nghiên cứu (LLM)** | Claude API tóm tắt, trích dẫn nguồn `[S1]`, `[S2]`, phân tích điểm không chắc chắn |
| **Tạo nội dung mạng xã hội** | Tạo bài Facebook và kịch bản TikTok riêng biệt, phù hợp với từng nền tảng |
| **Text-to-Speech** | edge-tts tạo giọng đọc MP3 (tiếng Việt & tiếng Anh) |
| **Tạo video dọc** | FFmpeg ghép ảnh + âm thanh thành MP4 1080×1920 (định dạng TikTok) |
| **Chỉnh sửa trước khi đăng** | Sửa nội dung trực tiếp trên giao diện trước khi publish |
| **Đăng bài lên Facebook** | Graph API v19.0; hỗ trợ mock khi thiếu token |
| **Đăng video lên TikTok** | TikTok Open APIs v2; upload private, hỗ trợ mock |
| **Lịch sử job** | SQLite lưu toàn bộ lịch sử chạy, trạng thái, kết quả đăng bài |
| **Đa ngôn ngữ** | Hỗ trợ tiếng Việt và tiếng Anh đầu ra |
| **Chế độ Mock** | Chạy demo không cần API key — tất cả bước đều có dữ liệu mẫu |

---

## Kiến trúc tổng quan

```
┌────────────────────────────────────────────────┐
│              Streamlit Web UI                  │
│  ┌─────────────────┐   ┌────────────────────┐  │
│  │  research_page  │   │   history_page     │  │
│  └────────┬────────┘   └────────────────────┘  │
└───────────┼────────────────────────────────────┘
            │
     ┌──────▼──────┐
     │   Pipeline  │
     └──────┬──────┘
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
   │   llm_service   │ ──► Anthropic Claude API
   └────────┬────────┘
            │
   ┌────────▼──────────────────┐
   │ content_generation_service│ ──► Claude API
   └────────┬──────────────────┘
            │
   ┌────────▼──────────┐   ┌──────────────┐
   │   video_builder   │──►│  tts_service │ ──► edge-tts
   └────────┬──────────┘   └──────────────┘
            │                      │
            └──────────┬───────────┘
                  ┌────▼────┐
                  │ FFmpeg  │  (hệ thống)
                  └────┬────┘
                       │
          ┌────────────▼────────────────┐
          │        Publishers           │
          │  ┌────────────┐  ┌────────┐ │
          │  │  Facebook  │  │TikTok  │ │
          │  └────────────┘  └────────┘ │
          └─────────────────────────────┘
                       │
              ┌────────▼────────┐
              │ storage_service │ ──► SQLite (data/app.db)
              └─────────────────┘
```

---

## Luồng xử lý pipeline

```
1. Người dùng nhập prompt (chủ đề)
        │
2. Tìm kiếm web [Tavily API]
   └── Lấy tối đa max_sources+3 kết quả
        │
3. Tạo SourceItem (S1, S2, ..., Sn)
        │
4. Khử trùng lặp nguồn
   ├── Loại URL trùng
   └── Loại tiêu đề tương tự
        │
5. Trích xuất nội dung từng URL
   ├── Thử trafilatura (ưu tiên)
   └── Fallback: requests + BeautifulSoup4
        │
6. Lọc nguồn chất lượng thấp (< 100 ký tự)
        │
7. Tổng hợp nghiên cứu [Claude API]
   ├── Input: danh sách nguồn + prompt
   ├── Output: title, summaries, key_points, citations [S1]...[Sn]
   └── Gắn flag uncertainties / safety_notes
        │
8. Tạo nội dung mạng xã hội [Claude API]
   ├── Facebook: tiêu đề + bài viết + hashtag + trích dẫn nguồn
   └── TikTok: hook + kịch bản (30-45 giây) + caption + cảnh (scenes)
        │
9. Tạo video TikTok [FFmpeg + edge-tts]
   ├── Tạo giọng đọc MP3 từ narration_script
   ├── Tạo ảnh JPG cho từng scene (PIL, 1080×1920)
   ├── FFmpeg: ảnh → clip MP4 theo duration từng scene
   ├── FFmpeg: ghép tất cả clips
   └── FFmpeg: mix video + audio
        │
10. Lưu job vào SQLite
        │
11. Hiển thị kết quả trong 5 tab UI
    ├── Research: tóm tắt + điểm chính
    ├── Facebook Draft: chỉnh sửa được
    ├── TikTok Draft: chỉnh sửa được
    ├── Video: xem trước MP4
    └── Publish: nút đăng lên Facebook / TikTok
        │
12. Đăng bài (nếu chọn)
    ├── Facebook → Graph API v19.0
    └── TikTok → Open APIs v2 (uploaded_private)
        │
13. Lưu publish result vào SQLite
```

---

## Cấu trúc dự án

```
ai-content-pipeline/
├── app.py                              # Entry point Streamlit
├── requirements.txt                    # Thư viện Python
├── pyproject.toml                      # pytest & ruff config
├── .env.example                        # Mẫu file biến môi trường
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

---

## Yêu cầu hệ thống

### Python
- Python **3.11** trở lên

### Node.js & npx (cần để chạy Tavily MCP server)
- Tải tại: https://nodejs.org/
- Kiểm tra: `node --version` và `npx --version`
- Tavily MCP server tự tải về qua `npx -y tavily-mcp@latest` khi lần đầu chạy

### FFmpeg (tùy chọn, cần để tạo video)
- Tải tại: https://ffmpeg.org/download.html
- Thêm vào PATH hệ thống
- Kiểm tra: `ffmpeg -version`

Nếu FFmpeg không có, ứng dụng vẫn chạy bình thường — bước tạo video sẽ được bỏ qua.

---

## Cài đặt

### Bước 1: Mở thư mục dự án

```bash
cd "C:\Users\soico\OneDrive\Desktop\NewDemo\ai-content-pipeline"
```

### Bước 2: Tạo môi trường ảo

```bash
# Tạo venv
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate
```

### Bước 3: Cài thư viện

```bash
pip install -r requirements.txt
```

### Bước 4: Tạo file `.env`

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Mở `.env` và điền API key (xem phần [Cấu hình biến môi trường](#cấu-hình-biến-môi-trường)).

---

## Cấu hình biến môi trường

Tạo file `.env` từ `.env.example`. Tất cả biến đều **tùy chọn** — ứng dụng chạy ở chế độ mock khi thiếu key.

```env
# ─── Ứng dụng ──────────────────────────────────────────────────
APP_ENV=development
# Môi trường: development | production

DATABASE_URL=sqlite:///data/app.db
# Đường dẫn SQLite. Thư mục data/ tự tạo khi khởi động.

OUTPUT_DIR=output
# Thư mục lưu file âm thanh, ảnh, video.

# ─── Tìm kiếm web ──────────────────────────────────────────────
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
# Lấy tại: https://app.tavily.com/
# Khi thiếu: dùng 5 bài báo mẫu về AI cố định.

MAX_SOURCES=5
# Số nguồn tối đa mỗi job (mặc định: 5, tối đa: 10).

# ─── Claude LLM ────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
# Lấy tại: https://console.anthropic.com/
# Khi thiếu: dùng kết quả tổng hợp và nội dung mẫu cố định.

ANTHROPIC_MODEL=claude-sonnet-4-6
# Model Claude sử dụng. Tùy chọn: claude-opus-4-8, claude-haiku-4-5-20251001

# ─── Giới hạn trích xuất ───────────────────────────────────────
MAX_EXTRACTED_CHARS_PER_SOURCE=8000
# Số ký tự tối đa trích xuất từ mỗi nguồn (mặc định: 8000).

# ─── Facebook ──────────────────────────────────────────────────
FACEBOOK_PAGE_ID=123456789012345
# ID của Facebook Page (không phải profile cá nhân).
# Lấy từ: Page Settings → About → Page ID.

FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxx...
# Page Access Token (long-lived, 60 ngày).
# Lấy từ: Meta for Developers → Graph API Explorer.

# ─── TikTok ────────────────────────────────────────────────────
TIKTOK_CLIENT_KEY=awxxxxxxxxxxxxxx
# TikTok Open Platform: Manage Apps → App Key.

TIKTOK_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# TikTok Open Platform: App Secret.

TIKTOK_ACCESS_TOKEN=act.xxxxxxxx...
# OAuth 2.0 access token của tài khoản TikTok cần đăng.

# ─── Bật đăng bài thật ─────────────────────────────────────────
ENABLE_REAL_PUBLISHING=false
# false (mặc định): chạy mock, không gọi API đăng bài.
# true: gọi Facebook Graph API và TikTok Open API thật sự.
# Chỉ bật khi đã cấu hình đủ PAGE_ID, ACCESS_TOKEN và app đã được duyệt.
```

---

## Chạy ứng dụng

Chạy từ **thư mục gốc của project** (`ai-content-pipeline/`):

```bash
streamlit run app.py
```

Mở trình duyệt tại: **http://localhost:8501**

> Nếu port 8501 bị chiếm, Streamlit tự chọn port kế tiếp (8502, 8503...).

### Chạy không mở trình duyệt (server/headless)

```bash
streamlit run app.py --server.headless true
```

---

## Hướng dẫn sử dụng

### Trang chính (Research)

1. **Nhập chủ đề** vào ô "Chủ đề / Prompt" — ví dụ: *"Trí tuệ nhân tạo trong giáo dục 2024"*
2. **Chọn ngôn ngữ** đầu ra: Tiếng Việt hoặc English
3. **Chọn số nguồn** muốn tổng hợp (3–10)
4. **Tích chọn** loại nội dung cần tạo: Facebook, TikTok, hoặc cả hai
5. Nhấn **"Bắt đầu nghiên cứu"**

Pipeline chạy tự động và hiển thị tiến trình. Kết quả hiển thị trong **5 tab**:

| Tab | Nội dung |
|-----|----------|
| **Research** | Tiêu đề, tóm tắt ngắn, điểm chính có trích dẫn `[S1]`, tóm tắt chi tiết, điểm chưa rõ |
| **Facebook Draft** | Tiêu đề, nội dung bài viết, hashtag — chỉnh sửa được |
| **TikTok Draft** | Hook, kịch bản đọc, caption, hashtag, danh sách cảnh — chỉnh sửa được |
| **Video** | Xem trước video MP4 nếu đã tạo thành công |
| **Publish** | Nút đăng lên Facebook / TikTok sau khi xác nhận checkbox |

### Trang lịch sử (History)

Nhấn **"Lịch sử"** trong sidebar để xem 50 job gần nhất:
- Trạng thái: ✅ done / ⏳ running / ❌ failed
- Thời gian tạo, prompt, ngôn ngữ
- Kết quả đăng bài từng nền tảng

---

## Tích hợp API

### Tavily (Tìm kiếm web)

- **Cơ chế:** Tavily MCP server khởi chạy qua `npx -y tavily-mcp@latest`
- **Yêu cầu:** Node.js + npx đã cài, biến `TAVILY_API_KEY` trong `.env`
- **Thư viện Python:** `mcp` (MCP client protocol)
- **Hành vi khi thiếu key:** Trả về 5 bài báo mẫu cố định về AI

Kết quả trả về dạng:
```json
{
  "title": "...",
  "url": "https://...",
  "content": "...",
  "score": 0.95
}
```

### Anthropic Claude (LLM)

- **Model mặc định:** `claude-sonnet-4-6`
- **Sử dụng 2 lần mỗi pipeline job:**
  1. Tổng hợp nghiên cứu (`research_system_prompt.txt`)
  2. Tạo nội dung mạng xã hội (`content_generation_prompt.txt`)
- **Định dạng output:** JSON (tự động parse, retry khi lỗi parse)
- **Hành vi khi thiếu key:** Trả về template mẫu cố định

**Cấu trúc JSON đầu ra — Research:**

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

**Cấu trúc JSON đầu ra — Social Content:**

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
      {
        "scene_number": 1,
        "duration_seconds": 5,
        "narration": "Giọng đọc cảnh này...",
        "on_screen_text": "Chữ hiển thị trên màn hình"
      }
    ],
    "call_to_action": "Follow để cập nhật thêm!"
  }
}
```

### Facebook Graph API

- **Phiên bản:** v19.0
- **Endpoint:** `POST /v19.0/{PAGE_ID}/feed`
- **Payload:** `message` (title + body + hashtags), `access_token`
- **Kết quả:** `external_post_id`, URL bài đăng
- **Yêu cầu:** Page Access Token có quyền `pages_manage_posts`

### TikTok Open APIs

- **Phiên bản:** v2
- **Endpoint upload:** `POST /v2/post/publish/inbox/video/init/`
- **Trạng thái sau upload:** `uploaded_private` (video chưa public ngay)
- **Yêu cầu:** OAuth 2.0 access token, app đã qua TikTok review

---

## Tạo video TikTok

### Yêu cầu

- FFmpeg đã cài và có trong PATH
- TikTok content đã được tạo (scenes list)

### Quy trình

```
TikTokPackage (scenes + narration_script)
    │
    ├─ tts_service: narration_script → MP3 (edge-tts)
    │   ├─ Tiếng Việt: vi-VN-NamMinhNeural
    │   └─ Tiếng Anh:  en-US-AriaNeural
    │
    ├─ Cho mỗi scene:
    │   ├─ PIL: tạo ảnh 1080×1920 px (nền màu xoay vòng)
    │   ├─ Vẽ on_screen_text lên ảnh (Arial, word-wrap tự động)
    │   └─ FFmpeg: ảnh → clip MP4 (duration = scene.duration_seconds)
    │
    ├─ FFmpeg: ghép tất cả clips theo thứ tự
    └─ FFmpeg: mix video + audio (narration MP3)
```

### File đầu ra

```
output/
├── audio/{job_id}_narration.mp3
├── images/{job_id}_scene1.jpg  ...
├── videos/{job_id}_clip1.mp4   ...
└── videos/{job_id}_final.mp4   ← file dùng để đăng TikTok
```

---

## Chế độ Mock

Ứng dụng hoạt động đầy đủ **mà không cần bất kỳ API key nào**. Từng service có fallback riêng:

| Service | Hành vi khi thiếu key |
|---------|----------------------|
| Tavily MCP | 5 bài báo mẫu về AI (tiếng Việt) |
| Claude LLM | Template nghiên cứu mẫu với trích dẫn giả |
| Claude content gen | Template Facebook + TikTok mẫu |
| Facebook publisher | Log "mock publish", trả về `status="mock_published"` |
| TikTok publisher | Log "mock publish", trả về `status="mock_published"` |
| FFmpeg | Bỏ qua bước tạo video, hiển thị cảnh báo |

Sidebar hiển thị trạng thái từng service (✅ Đã cấu hình / ⚠️ Mock mode).

> Để bật đăng bài thật sau khi có đủ credentials: đặt `ENABLE_REAL_PUBLISHING=true` trong `.env`.

---

## Cơ sở dữ liệu

Ứng dụng dùng **SQLite** tại `data/app.db`, tự tạo khi khởi động lần đầu.

### Bảng `jobs`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | TEXT (UUID) | Primary key |
| `prompt` | TEXT | Chủ đề người dùng nhập |
| `language` | TEXT | `vi` hoặc `en` |
| `max_sources` | INT | Số nguồn yêu cầu |
| `generate_facebook` | BOOL | Có tạo Facebook không |
| `generate_tiktok` | BOOL | Có tạo TikTok không |
| `status` | TEXT | `running` / `done` / `failed` |
| `created_at` | DATETIME | Thời điểm tạo |
| `updated_at` | DATETIME | Thời điểm cập nhật cuối |
| `research_title` | TEXT | Tiêu đề nghiên cứu |
| `research_summary` | TEXT | Tóm tắt ngắn |
| `facebook_body` | TEXT | Nội dung bài Facebook |
| `tiktok_script` | TEXT | Kịch bản TikTok |
| `video_path` | TEXT | Đường dẫn file MP4 |
| `error_message` | TEXT | Lỗi (nếu status=failed) |

### Bảng `sources`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | INT (auto) | Primary key |
| `job_id` | TEXT | FK → jobs.id |
| `source_id` | TEXT | S1, S2, ... |
| `title` | TEXT | Tiêu đề bài viết |
| `url` | TEXT | URL nguồn |
| `domain` | TEXT | Domain (ví dụ: vnexpress.net) |
| `extraction_status` | TEXT | `success` / `partial` / `failed` |
| `retrieved_at` | DATETIME | Thời điểm tìm kiếm |
| `published_date` | DATETIME | Ngày đăng bài gốc |
| `content_preview` | TEXT | 500 ký tự đầu nội dung |

### Bảng `publish_results`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | INT (auto) | Primary key |
| `job_id` | TEXT | FK → jobs.id |
| `platform` | TEXT | `facebook` / `tiktok` |
| `status` | TEXT | `mock_published` / `published` / `uploaded_private` / `failed` |
| `external_post_id` | TEXT | ID bài đăng trên nền tảng |
| `external_url` | TEXT | URL bài đã đăng |
| `error_message` | TEXT | Lỗi nếu thất bại |
| `published_at` | DATETIME | Thời điểm đăng |

---

## Kiểm thử

```bash
# Chạy toàn bộ test
pytest

# Chạy với output chi tiết
pytest -v

# Chạy một file test cụ thể
pytest tests/test_deduplicator.py -v
```

### Mô tả các test

| File | Test gì |
|------|---------|
| `test_schemas.py` | Pydantic v2 schema: trường hợp hợp lệ, không hợp lệ, URL, nested |
| `test_deduplicator.py` | Khử trùng lặp URL, khử trùng lặp tiêu đề, lọc nguồn ngắn |
| `test_llm_parsing.py` | Parse JSON từ Claude, mock mode khi thiếu key, retry logic |
| `test_publishers_mock.py` | Mock publish Facebook/TikTok, không rò rỉ secrets trong error |

---

## Linting & Code Quality

```bash
# Kiểm tra linting
ruff check .

# Auto-fix một số lỗi
ruff check . --fix
```

Cấu hình ruff trong `pyproject.toml`.

---

## File đầu ra

Sau khi chạy pipeline, các file được tạo tại thư mục `output/`:

```
output/
├── audio/
│   └── {uuid}_narration.mp3         # Giọng đọc TTS
├── images/
│   ├── {uuid}_scene1.jpg            # Ảnh cảnh 1 (1080×1920)
│   └── ...
├── videos/
│   ├── {uuid}_clip1.mp4             # Clip từng cảnh
│   └── {uuid}_final.mp4             # Video hoàn chỉnh (dùng để đăng TikTok)
└── subtitles/                       # Dành cho phụ đề (tương lai)
```

---

## Giới hạn & lưu ý

| Giới hạn | Chi tiết |
|----------|----------|
| **Trích xuất nội dung** | Không truy cập được trang yêu cầu đăng nhập, paywall, hoặc CAPTCHA |
| **Ký tự mỗi nguồn** | Tối đa 8.000 ký tự (cấu hình qua `MAX_EXTRACTED_CHARS_PER_SOURCE`) |
| **TikTok upload** | Video upload ở trạng thái `uploaded_private`, chưa public ngay |
| **TikTok app review** | Tính năng publish yêu cầu app TikTok được duyệt |
| **Facebook token** | Page Access Token hết hạn sau 60 ngày, cần refresh định kỳ |
| **Rate limit API** | Không có rate limiting tích hợp — tuân thủ quota của từng API |
| **Video quality** | Độ phân giải cố định 1080×1920, font Arial (fallback nếu không có) |
| **Concurrency** | Mỗi lần chỉ chạy một pipeline; không hỗ trợ chạy song song nhiều job |
| **Nội dung** | Chỉ tóm tắt thông tin, không copy nguyên văn bài nguồn — luôn review trước khi đăng |

---

## Xử lý sự cố thường gặp

### `streamlit: command not found`

```bash
# Đảm bảo venv đang active
.venv\Scripts\activate   # Windows

# Hoặc dùng python -m
python -m streamlit run app.py
```

### Lỗi `DetachedInstanceError` (SQLAlchemy lazy loading)

Đã được sửa trong `storage_service.py` bằng `joinedload`. Đảm bảo dùng phiên bản mới nhất của file.

### Video không được tạo

```bash
# Kiểm tra FFmpeg
ffmpeg -version

# Nếu chưa cài: https://ffmpeg.org/download.html
# Sau khi cài, thêm vào PATH và khởi động lại terminal
```

### Lỗi `ANTHROPIC_API_KEY` / không có kết quả LLM thật

- Kiểm tra file `.env` có dòng `ANTHROPIC_API_KEY=sk-ant-...`
- Kiểm tra key còn hạn tại https://console.anthropic.com/

### Không thấy bài đăng trên Facebook

1. Kiểm tra `ENABLE_REAL_PUBLISHING=true` trong `.env`
2. Kiểm tra `FACEBOOK_PAGE_ID` và `FACEBOOK_PAGE_ACCESS_TOKEN` đúng
3. Token cần quyền `pages_manage_posts` và `pages_read_engagement`
4. Thử lại token tại Meta Graph API Explorer

### Lỗi khi chạy test

```bash
# Đảm bảo đang ở thư mục gốc project
cd ai-content-pipeline
pytest -v
```

### Port 8501 đang bị dùng

```bash
streamlit run app.py --server.port 8502
```

---

## Thư viện chính

| Thư viện | Phiên bản | Mục đích |
|----------|-----------|----------|
| streamlit | ≥1.35.0 | Web UI framework |
| pydantic | ≥2.7.0 | Data validation |
| sqlalchemy | ≥2.0.0 | ORM + SQLite |
| anthropic | ≥0.25.0 | Claude API |
| mcp | ≥1.0.0 | MCP client — giao tiếp với Tavily MCP server |
| trafilatura | ≥1.8.0 | Article extraction |
| beautifulsoup4 | ≥4.12.0 | HTML parsing fallback |
| edge-tts | ≥6.1.9 | Text-to-speech |
| Pillow | ≥10.3.0 | Image generation |
| requests | ≥2.31.0 | HTTP requests |
| httpx | ≥0.27.0 | Async HTTP |
| python-dotenv | ≥1.0.0 | ENV file loading |
| pytest | ≥8.0.0 | Testing |
| ruff | ≥0.4.0 | Linting |

---

## License

MIT License — xem file `LICENSE` để biết thêm chi tiết.
