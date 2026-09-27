# tools/

Script phụ trợ, không phải phần của Edge Server.

| Script | Mục đích | Trạng thái |
|---|---|---|
| `check_env.py` | Kiểm tra môi trường phát triển (Python, pytest, git, GPU, broker, toolchain firmware) | ✅ Phase 0 |
| `gen_topics_header.py` | Sinh `topics_gen.h` cho firmware từ `contracts/mqtt/topics.toml` | Phase 1 |
| `replay_events.py` | Phát lại log JSONL để test lại pipeline quyết định | Phase 4 |

Chạy: `python tools/check_env.py`
