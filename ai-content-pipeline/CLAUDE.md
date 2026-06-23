# AI Content Pipeline — Claude Code Agent Mode

Pipeline này tạo nội dung Facebook/TikTok mà **không cần Anthropic API credits riêng**.
Claude Code (chạy bằng subscription của bạn) đóng vai trò AI engine.

## Kiến trúc

```
Python gather → Claude Code synthesize → Claude Code generate → Python publish
     ↓                    ↓                        ↓                    ↓
 Tavily search     Tổng hợp nghiên cứu      Viết Facebook/TikTok   Facebook API
 Web extraction    (Claude Code làm)        (Claude Code làm)
 (không LLM)
```

## Slash command

```
/tao-noi-dung <chủ đề>
```

Ví dụ:
```
/tao-noi-dung Bitcoin và xu hướng crypto 2025
/tao-noi-dung AI thay thế lập trình viên
```

## Chạy thủ công từng bước

### Bước 1 — Thu thập nguồn
```bash
cd ai-content-pipeline
python pipeline.py gather --topic "chủ đề của bạn" --output sources.json
```
→ Tạo `sources.json` chứa nội dung từ các nguồn web (không gọi LLM)

### Bước 2 — Claude Code tổng hợp nghiên cứu
Đọc `sources.json` rồi hỏi Claude: *"Tổng hợp nghiên cứu từ sources.json"*

### Bước 3 — Claude Code tạo nội dung
Hỏi Claude: *"Tạo Facebook post và TikTok script, lưu vào content.json"*

### Bước 4 — Đăng lên mạng xã hội
```bash
python pipeline.py publish --content-file content.json
```

## Cấu hình `.env` cần thiết

| Biến | Bắt buộc | Ghi chú |
|------|----------|---------|
| `TAVILY_API_KEY` | ✅ | Web search |
| `FACEBOOK_PAGE_ID` | ✅ | ID trang Facebook |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | ✅ | Token đăng bài |
| `ANTHROPIC_API_KEY` | ❌ | Không cần khi dùng Claude Code |
| `ENABLE_REAL_PUBLISHING` | Tuỳ | `true` để đăng thật, `false` để mock |

## File tạm thời

| File | Mô tả |
|------|-------|
| `sources.json` | Kết quả gather (input cho Claude Code) |
| `content.json` | Nội dung do Claude Code tạo (input cho publish) |
