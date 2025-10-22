# auto-bug CLI MVP

最小可行 CLI：将 IDE/测试执行日志通过 LLM 转换为 Obsidian 中的 Bug 表单。现已支持 MCP Server，便于在 Cursor 等 IDE 中直接调用。

## 基本流程

1. 准备配置：
   - 在仓库根目录创建 `config.toml`（示例见 `examples/config.toml`）。
   - 写入 Obsidian Vault 路径、默认项目名、使用的 LLM 提供方以及对应 API Key。
   - API Key 可放到 `.env`，程序会自动加载。
2. 运行命令：
   ```bash
   cursor run tests > latest.log
   auto-bug ingest my_project latest.log
   ```
   或直接从标准输入读取：
   ```bash
   cursor run tests | auto-bug ingest my_project -
   ```
3. 工具会：
   - 解析日志（截取关键片段）。
   - 向 LLM 发送结构化请求，生成 Bug 报告 JSON。
   - 使用模板渲染 Markdown，并写入 `ObsidianVault/<project>/bugNNN.md`。

## 当前能力

- 支持 OpenAI（GPT 系列）和 DeepSeek 两类提供方，统一 HTTP 调用。
- 失败时提供最小错误提示，不会覆盖已有文件。
- 模板可按需自定义（参见 `templates/bug_report.md.j2`）。

## TODO

- 日志签名去重与聚合。
- 增强错误分类、标题生成策略。
- 更丰富的 CLI 子命令（例如 `config list`、`vault sync`）。

## MCP 使用指南（实验性）

**准备条件**
- 已在项目根目录配置 `config.toml` 与 `.env`（参考 `examples/`）。
- 先安装基础 CLI：`uv pip install --editable .` 或 `pip install -e .`。
- 再安装 MCP 依赖：`uv pip install --editable '.[mcp]'`（或 `pip install -e '.[mcp]'`）。若处于离线环境，请在有网的机器上下载 `mcp[cli]` 对应的 wheel 文件后再安装。
- 确保 Obsidian Vault 路径可写，LLM API Key 可正常访问。

**启动服务**
```bash
auto-bug-mcp --host 127.0.0.1 --port 8001 --transport sse
```
默认使用 SSE 方式提供 HTTP 接口，地址为 `http://127.0.0.1:8001/sse`（消息回传路径 `http://127.0.0.1:8001/messages/`）。若仅想本地调试，可改为 `--transport stdio`。

**在客户端登记（以 Cursor 为例）**
1. 打开 Cursor → `Settings` → `Model Providers` → `Model Context Protocol (MCP)`。
2. 添加自定义服务：名称自定，`URL` 填 `http://127.0.0.1:8001/sse`，`Transport` 选择 SSE。
3. 保存后，Cursor 会自动列出 `generate_bug_report` 工具。

**发送请求**
- 在 Cursor 命令面板选择 `generate_bug_report`，按提示输入 JSON 负载，例如：
  ```json
  {
    "project": "demo_project",
    "log_text": "Traceback (most recent call last): ...",
    "command": "python test.py --data orders_bad.json",
    "environment": "local-dev",
    "persist": true
  }
  ```
- 若 `persist=true`，服务会创建 `vault_root/project/bugNNN.md` 并把 Markdown 返回给客户端；`persist=false` 时仅返回内容，不写文件。
- 工具参数说明：
  - `log_text` (`str`, 必填)：完整的终端或测试日志文本，用于分析缺陷。
  - `project` (`str | null`, 默认 `None`)：项目名；未提供时回退到配置文件里的默认项目。
  - `command` (`str`, 默认 `unknown`)：触发该日志的命令或操作描述。
  - `environment` (`str`, 默认 `local`)：执行环境标识，例如 `local-dev`、`CI`。
  - `persist` (`bool`, 默认 `True`)：是否把生成的 Markdown 写入 Obsidian Vault；设为 `False` 时仅返回内容。
  - `config_path` (`str | null`, 默认 `None`)：自定义配置文件路径；留空则使用当前工作目录下的 `config.toml`。

**命令行快速验证（SSE）**
```bash
python - <<'PY'
import anyio, json
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    payload = json.load(open("examples/mcp_request.json"))
    async with sse_client("http://127.0.0.1:8001/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("generate_bug_report", payload)
            print(result.content[0].text)
            await session.shutdown()

anyio.run(main)
PY
```

**常见问题**
- `请求参数错误`：确认 JSON 结构与字段名称正确，可参考 `examples/mcp_request.json`。
- `配置加载失败`：检查 `config.toml` 路径；如需指定其他配置文件，在请求体中传入 `config_path`。
- `生成缺陷报告失败`：多为 LLM API Key 未设置或网络问题，检查 `.env` 与代理设置；必要时加大日志截取范围后重试。
