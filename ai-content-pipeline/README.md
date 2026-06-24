# AI Content Pipeline

Tự động hoá luồng **tìm kiếm web → tổng hợp nghiên cứu → tạo nội dung → đăng bài** lên Facebook và TikTok.

Vận hành theo mô hình **Claude Code Agent**: Claude Code (dùng subscription Claude Pro/Max) đóng vai AI engine — **không cần Anthropic API credits riêng**.

---

## Mục lục

1. [Tính năng](#tính-năng)
2. [Kiến trúc](#kiến-trúc)
3. [Cấu trúc dự án](#cấu-trúc-dự-án)
4. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
5. [Cài đặt](#cài-đặt)
6. [Cấu hình biến môi trường](#cấu-hình-biến-môi-trường)
7. [Cách dùng nhanh — Slash command](#cách-dùng-nhanh--slash-command)
8. [Chạy thủ công từng bước](#chạy-thủ-công-từng-bước)
9. [Tích hợp API](#tích-hợp-api)
10. [Tạo ảnh và video](#tạo-ảnh-và-video)
11. [Chế độ Mock](#chế-độ-mock)
12. [Kiểm thử](#kiểm-thử)
13. [Linting & Code Quality](#linting--code-quality)
14. [Giới hạn & lưu ý](#giới-hạn--lưu-ý)
15. [Xử lý sự cố](#xử-lý-sự-cố)
16. [Thư viện chính](#thư-viện-chính)

---

## Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Tìm kiếm web tự động** | Tích hợp Tavily MCP server (qua `npx`), thu thập tối đa 10 nguồn liên quan |
| **Trích xuất nội dung** | trafilatura + BeautifulSoup4 trích xuất văn bản từ bài báo |
| **Khử trùng lặp nguồn** | Loại bỏ các nguồn trùng URL hoặc tiêu đề tương tự |
| **Tổng hợp nghiên cứu** | Claude Code đọc nguồn và viết nội dung — dùng subscription, không tốn credit riêng |
| **Tạo nội dung mạng xã hội** | Bài Facebook (300–500 từ) và kịch bản TikTok (5 cảnh, 60–90 giây) |
| **Ảnh card Facebook** | Pillow tạo ảnh 1200×628 px với tiêu đề và hashtag |
| **Text-to-Speech** | edge-tts tạo giọng đọc MP3 (tiếng Việt & tiếng Anh) |
| **Video dọc TikTok** | FFmpeg ghép ảnh + âm thanh thành MP4 1080×1920 |
| **Đăng bài lên Facebook** | Graph API v19.0; hỗ trợ mock khi thiếu token |
| **Chế độ Mock** | Chạy demo không cần API key — tất cả bước đều có dữ liệu mẫu |

---

## Kiến trúc

```
python pipeline.py gather          python pipeline.py synthesize
  --topic "chủ đề"                   --sources-file sources.json
         │                                    │
   Tavily MCP Search                  claude -p <prompt>
   Web extraction                     (Claude Code subscription)
   source_deduplicator                         │
         │                             content.json
    sources.json                      (Facebook + TikTok JSON)
                                                │
                          ┌─────────────────────┤
                          │                     │
               pipeline.py build-image   pipeline.py build-video
                (Pillow 1200×628)         (edge-tts + FFmpeg)
                          │                     │
               pipeline.py publish
                (Facebook Graph API)
```

Claude Code đọc `sources.json` và tạo `content.json` — không gọi Anthropic API, chạy trực tiếp trong context của Claude Code.

---

## Cấu trúc dự án

```
ai-content-pipeline/
├── pipeline.py                    # CLI chính: gather / synthesize / build-image / build-video / publish
├── CLAUDE.md                      # Hướng dẫn Claude Code agent workflow
├── requirements.txt               # Thư viện Python
├── pyproject.toml                 # pytest & ruff config
├── .env                           # Biến môi trường (tạo từ mẫu bên dưới)
│
├── src/
│   ├── config.py                  # Đọc ENV, tạo thư mục output
│   │
│   ├── models/
│   │   └── schemas.py             # Pydantic v2: SourceItem, FacebookPost, TikTokPackage, PublishResult
│   │
│   ├── services/
│   │   ├── search_service.py      # Tavily MCP server (npx) / mock search
│   │   ├── content_extractor.py   # trafilatura + BS4 extraction
│   │   ├── source_deduplicator.py # Khử trùng lặp URL & tiêu đề
│   │   ├── tts_service.py         # edge-tts → MP3
│   │   └── video_builder.py       # PIL + FFmpeg → MP4 dọc
│   │
│   ├── publishers/
│   │   ├── base.py                # Abstract BasePublisher
│   │   ├── facebook_publisher.py  # Meta Graph API v19.0
│   │   └── tiktok_publisher.py    # TikTok Open APIs v2
│   │
│   └── utils/
│       ├── ffmpeg_utils.py        # check_ffmpeg(), run_ffmpeg()
│       ├── text_utils.py          # truncate(), strip_html(), normalize_whitespace()
│       └── url_utils.py           # extract_domain(), is_valid_url(), normalize_url()
│
├── tests/
│   ├── test_schemas.py            # Pydantic schema validation
│   ├── test_deduplicator.py       # Logic khử trùng lặp
│   ├── test_llm_parsing.py        # Parse JSON output từ Claude + mock mode
│   └── test_publishers_mock.py    # Publisher mock & bảo mật
│
├── data/                          # SQLite database (tự tạo)
│   └── app.db
│
└── output/                        # File đầu ra (tự tạo)
    ├── audio/                     # {job_id}_narration.mp3
    ├── images/                    # {job_id}_scene{N}.jpg, {job_id}_card.jpg
    └── videos/                    # {job_id}_final.mp4
```

File tạm thời (git-ignored):

```
ai-content-pipeline/
├── sources.json    # Kết quả gather — input cho Claude Code
└── content.json    # Nội dung do Claude Code tạo — input cho build/publish
```

---

## Yêu cầu hệ thống

| Yêu cầu | Bắt buộc | Ghi chú |
|---------|----------|---------|
| **Python 3.11+** | ✅ | |
| **Node.js + npx** | ✅ | Chạy Tavily MCP server; tải tại [nodejs.org](https://nodejs.org/) |
| **Claude Code CLI** | ✅ | Đăng nhập bằng tài khoản Claude Pro/Max; kiểm tra: `claude --version` |
| **FFmpeg** | Tùy chọn | Chỉ cần khi tạo video TikTok; tải tại [ffmpeg.org](https://ffmpeg.org/download.html) |

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
OUTPUT_DIR=output

# ─── Tìm kiếm web ──────────────────────────────────────────────
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
# Lấy tại: https://app.tavily.com/
# Khi thiếu: dùng 5 bài báo mẫu về AI

MAX_SOURCES=5
MAX_EXTRACTED_CHARS_PER_SOURCE=8000

# ─── Facebook ──────────────────────────────────────────────────
FACEBOOK_PAGE_ID=123456789012345
FACEBOOK_PAGE_ACCESS_TOKEN=EAAxxxxxx...
# Page Access Token có quyền pages_manage_posts (hết hạn sau 60 ngày)

# ─── TikTok ────────────────────────────────────────────────────
TIKTOK_CLIENT_KEY=awxxxxxxxxxxxxxx
TIKTOK_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TIKTOK_ACCESS_TOKEN=act.xxxxxxxx...

# ─── Bật đăng bài thật ─────────────────────────────────────────
ENABLE_REAL_PUBLISHING=false
# false: mock, không gọi API đăng bài thật
# true:  gọi Facebook Graph API và TikTok Open API thật sự
```

> `ANTHROPIC_API_KEY` **không cần thiết** — Claude Code dùng subscription của bạn thay thế.

---

## Cách dùng nhanh — Slash command

Mở Claude Code trong thư mục `ai-content-pipeline/` và gõ:

```
/tao-noi-dung <chủ đề>
```

Ví dụ:

```
/tao-noi-dung Bitcoin và xu hướng crypto 2025
/tao-noi-dung AI thay thế lập trình viên
/tao-noi-dung Thị trường bất động sản Hà Nội quý 3 2025
```

Claude Code sẽ tự động chạy toàn bộ pipeline theo các bước sau.

---

## Chạy thủ công từng bước

### Bước 1 — Thu thập nguồn

```bash
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

Không gọi LLM — chỉ tìm kiếm web và trích xuất nội dung. Kết quả lưu vào `sources.json`.

### Bước 2 — Tổng hợp và tạo nội dung

```bash
python pipeline.py synthesize --sources-file sources.json --output content.json
```

Lệnh này gọi `claude -p <prompt>` và yêu cầu Claude Code tổng hợp nghiên cứu, rồi viết bài Facebook + kịch bản TikTok. Kết quả lưu vào `content.json`.

> Yêu cầu: `claude` CLI đã đăng nhập (`claude --version` để kiểm tra).

### Bước 3 — Tạo ảnh card Facebook (tùy chọn)

```bash
python pipeline.py build-image --content-file content.json
```

Tạo ảnh 1200×628 px có tiêu đề và hashtag, lưu vào `output/images/`. Cập nhật `image_path` vào `content.json`.

### Bước 4 — Tạo video TikTok (tùy chọn)

```bash
python pipeline.py build-video --content-file content.json --language vi
```

Yêu cầu FFmpeg đã cài. Tạo file `output/videos/{job_id}_final.mp4`.

### Bước 5 — Đăng lên Facebook

```bash
python pipeline.py publish --content-file content.json
```

Đọc `content.json` và đăng lên Facebook. Ở mock mode (mặc định) sẽ in ra kết quả mà không gọi API thật.

---

## Tích hợp API

### Tavily (Tìm kiếm web)

- **Cơ chế:** Tavily MCP server khởi chạy qua `npx -y tavily-mcp@latest`
- **Yêu cầu:** Node.js + npx, biến `TAVILY_API_KEY`
- **Khi thiếu key:** Trả về 5 bài báo mẫu về AI

### Facebook Graph API

- **Phiên bản:** v19.0
- **Endpoint:** `POST /v19.0/{PAGE_ID}/feed`
- **Yêu cầu:** Page Access Token có quyền `pages_manage_posts`
- **Khi thiếu:** mock mode — in kết quả không gọi API

### TikTok Open APIs

- **Phiên bản:** v2
- **Trạng thái sau upload:** `uploaded_private`
- **Yêu cầu:** OAuth 2.0 access token, app đã qua TikTok review

### Cấu trúc `content.json`

```json
{
  "topic": "Chủ đề nghiên cứu",
  "language": "vi",
  "facebook": {
    "title": "Tiêu đề bài viết",
    "body": "Nội dung 300-500 từ...",
    "hashtags": ["#AI", "#CongNghe"],
    "source_references": ["domain1.com", "domain2.com"]
  },
  "tiktok": {
    "hook": "Hook dưới 10 từ",
    "narration_script": "Kịch bản đọc 60-90 giây...",
    "caption": "Caption dưới 150 ký tự",
    "hashtags": ["#TikTok", "#AI"],
    "call_to_action": "Follow để cập nhật thêm!",
    "scenes": [
      {"scene_number": 1, "duration_seconds": 5, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 2, "duration_seconds": 8, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 3, "duration_seconds": 8, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 4, "duration_seconds": 7, "narration": "...", "on_screen_text": "..."},
      {"scene_number": 5, "duration_seconds": 7, "narration": "...", "on_screen_text": "..."}
    ]
  }
}
```

---

## Tạo ảnh và video

### Ảnh card Facebook (`build-image`)

- Kích thước: **1200×628 px**
- Nền tối với thanh màu accent (tự động chọn theo hash tiêu đề)
- Hiển thị tiêu đề và hashtag
- Yêu cầu: Pillow (`pip install Pillow`)

### Video TikTok (`build-video`)

Yêu cầu FFmpeg đã cài và có trong PATH.

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

File đầu ra:

```
output/
├── audio/{job_id}_narration.mp3
├── images/{job_id}_scene1.jpg  ...
└── videos/{job_id}_final.mp4
```

---

## Chế độ Mock

Ứng dụng hoạt động đầy đủ **mà không cần bất kỳ API key nào**:

| Service | Hành vi khi thiếu key |
|---------|----------------------|
| Tavily MCP | 5 bài báo mẫu về AI (tiếng Việt) |
| Facebook publisher | `status="mock_published"`, không gọi API |
| TikTok publisher | `status="mock_published"`, không gọi API |
| FFmpeg | Lỗi rõ ràng nếu thiếu, bước video bị bỏ qua |

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
| **Nội dung** | Luôn review trước khi đăng — không copy nguyên văn bài nguồn |

---

## Xử lý sự cố

### `claude: command not found`

```bash
# Kiểm tra Claude Code CLI đã cài chưa
claude --version

# Nếu chưa: cài Claude Code và đăng nhập bằng tài khoản Claude Pro/Max
```

### `pipeline.py gather` không tìm được nguồn tốt

Nhiều trang tin tức lớn (Reuters, Bloomberg, Investing.com) chặn scraping. Pipeline vẫn hoạt động bằng cách dùng snippet từ kết quả Tavily — tổng hợp sẽ ít chi tiết hơn nhưng vẫn có giá trị.

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

### `synthesize` trả về lỗi JSON

Claude Code đôi khi bọc JSON trong markdown fences — lệnh `synthesize` tự xử lý trường hợp này. Nếu vẫn lỗi, chạy lại hoặc kiểm tra `claude -p "hello"` để xác nhận CLI hoạt động.

---

## Thư viện chính

| Thư viện | Mục đích |
|----------|---------|
| pydantic ≥2.7 | Data validation |
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
