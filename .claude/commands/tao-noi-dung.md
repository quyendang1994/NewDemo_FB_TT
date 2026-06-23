Tạo nội dung social media cho chủ đề: $ARGUMENTS

Thực hiện tuần tự các bước sau:

## Bước 1: Thu thập nguồn web

Chạy lệnh này để tìm kiếm và trích xuất nội dung (không cần API key LLM):

```bash
cd ai-content-pipeline && python pipeline.py gather --topic "$ARGUMENTS" --output sources.json
```

Đọc kết quả từ `ai-content-pipeline/sources.json`.

## Bước 2: Tổng hợp nghiên cứu

Dựa trên các nguồn trong `sources.json`, tổng hợp nghiên cứu với quy tắc:
- Chỉ dùng thông tin từ các nguồn [S1], [S2]... đã được cung cấp, KHÔNG bịa thêm
- Trích dẫn đúng dạng [S1], [S2]
- Nếu hai nguồn mâu thuẫn nhau, nêu rõ mâu thuẫn
- Viết tiếng Việt, ngắn gọn, có cấu trúc

## Bước 3: Tạo nội dung Facebook và TikTok

Từ nghiên cứu trên, tạo nội dung cho:

**Facebook**: Ngắn gọn, dễ đọc, hook mạnh trong 2 dòng đầu, có nguồn tham khảo

**TikTok**: Hook 1-3 giây đầu rất hấp dẫn, kịch bản 30-45 giây sinh động, 4 scenes cụ thể

## Bước 4: Lưu vào content.json

Lưu kết quả vào file `ai-content-pipeline/content.json` với cấu trúc chính xác:

```json
{
  "facebook": {
    "title": "tiêu đề bài viết",
    "body": "nội dung bài viết dài",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "source_references": ["[S1] https://...", "[S2] https://..."]
  },
  "tiktok": {
    "hook": "câu hook 1-3 giây đầu rất hấp dẫn",
    "narration_script": "toàn bộ lời đọc 30-45 giây",
    "caption": "caption ngắn cho TikTok",
    "hashtags": ["#hashtag1", "#hashtag2"],
    "scenes": [
      {"scene_number": 1, "duration_seconds": 3, "narration": "hook mở đầu", "on_screen_text": "text hiển thị"},
      {"scene_number": 2, "duration_seconds": 15, "narration": "nội dung chính", "on_screen_text": "điểm chính"},
      {"scene_number": 3, "duration_seconds": 10, "narration": "chi tiết thêm", "on_screen_text": "chi tiết"},
      {"scene_number": 4, "duration_seconds": 7, "narration": "kết thúc", "on_screen_text": "kết luận"}
    ],
    "call_to_action": "lời kêu gọi theo dõi/tương tác"
  },
  "sources": []
}
```

Đặt danh sách sources từ `sources.json` vào trường `"sources"`.

## Bước 5: Đăng lên Facebook

```bash
cd ai-content-pipeline && python pipeline.py publish --content-file content.json
```

Báo kết quả publish cho người dùng.
