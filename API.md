# Laya Service 接口文档 (Jev 兼容 System One API)

> @author hubin

本文档详细描述 Laya Service 提供的 API 规范、请求响应结构、鉴权方式及调用示例。Laya Service 实现了兼容 Jev 的 `POST /v1/systemone` 快速直觉决策（System One）接口，专为结构化决策设计（返回确定性的选项/评分/判断，而非自由生成的文本补全）。

---

## 1. 基础信息

- **服务基准路径**: `http://<host>:<port>`（默认端口 `8000`）
- **数据格式**: 请求与响应均为 `application/json`
- **字符编码**: `UTF-8`
- **鉴权方式**: HTTP Bearer Token（当服务端环境变量 `LAYA_API_KEY` 有配置时生效）：
  ```http
  Authorization: Bearer <YOUR_API_KEY>
  ```
- **全局自定义响应头**:
  - `X-Request-Id`: 请求的唯一追踪 UUID
  - `X-Laya-Latency-Ms`: 模型推理耗时（毫秒）
  - `X-Laya-Model`: 实际执行推理的模型或路由标识

---

## 2. 接口列表概览

| 方法 | 端点 | 鉴权要求 | 说明 |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | 无需鉴权 | 存活探针（Liveness Probe） |
| `GET` | `/readyz` | 无需鉴权 | 就绪探针（Readiness Probe，检查模型是否已就绪） |
| `GET` | `/v1/models` | 需要鉴权 | 获取当前支持的模型列表及别名映射 |
| `POST` | `/v1/systemone` | 需要鉴权 | 核心决策接口（执行 System One 快速决策） |

---

## 3. 接口详细说明

### 3.1 存活探针: `GET /healthz`

用于服务存活状态检测。

- **请求示例**:
  ```bash
  curl -X GET http://localhost:8000/healthz
  ```
- **响应示例**:
  ```json
  {
    "status": "ok"
  }
  ```

---

### 3.2 就绪探针: `GET /readyz`

用于检测服务底层模型是否完成初始化/预加载。

- **成功响应** (200 OK):
  ```json
  {
    "status": "ready"
  }
  ```
- **未就绪响应** (503 Service Unavailable):
  ```json
  {
    "status": "not_ready"
  }
  ```

---

### 3.3 模型列表: `GET /v1/models`

查询可用的决策模型 ID 与其对应底层实现。

- **请求头**:
  ```http
  Authorization: Bearer <API_KEY>
  ```
- **响应示例** (200 OK):
  ```json
  {
    "object": "list",
    "data": [
      { "id": "jev-latest", "implementation": "router" },
      { "id": "laya", "implementation": "english" },
      { "id": "laya-english", "implementation": "english" },
      { "id": "laya-multilingual", "implementation": "multilingual" },
      { "id": "laya-typed-decisions", "implementation": "typed-decisions" }
    ]
  }
  ```

---

### 3.4 核心决策接口: `POST /v1/systemone`

输入当前上下文状态（`state`）及一组决策问题（`questions`），输出确定性的决策结论（`answers`）。

#### 3.4.1 请求体（Request Body）

完整请求结构示例：

```json
{
  "model": "jev-latest",
  "state": {
    "agent_id": "character_007",
    "name": "矿工小人-阿尔法",
    "status": "working",
    "hp": 35,
    "max_hp": 100,
    "energy": 20,
    "position": { "x": 124.5, "y": 48.0 },
    "inventory": [
      { "item": "iron_ore", "count": 15 },
      { "item": "pickaxe", "durability": 12 }
    ],
    "environment": {
      "weather": "rainy",
      "nearby_threats": [
        { "type": "goblin", "distance": 6.5, "level": 3 }
      ],
      "nearby_facilities": [
        { "type": "camp", "distance": 85.0 }
      ]
    },
    "recent_events": [
      "挖掘铁矿成功",
      "遭遇哥布林靠近攻击，损失了 25 点生命值"
    ]
  },
  "questions": {
    "next_action": {
      "type": "choice",
      "instructions": "根据小人当前的 `hp`、`energy` 以及 `environment.nearby_threats`，小人下一步应该做什么？",
      "criteria": {
        "flee": "生命值偏低（<=40）且周围有敌人威胁，必须立即撤退逃跑",
        "attack": "自身状态良好且敌人已进入攻击范围，进行自卫还击",
        "rest": "周围无威胁但体力不足，就地休息恢复体力",
        "continue_mining": "周围安全且体力充沛，继续开采矿石"
      }
    },
    "is_in_danger": {
      "type": "noul",
      "instructions": "小人当前是否处于紧急危险状态？"
    },
    "threat_level": {
      "type": "score",
      "instructions": "评估小人当前面临的危险程度？",
      "criteria": [
        "完全安全，无威胁",
        "有潜在危险，但尚在可控范围",
        "高度危险，受到直接攻击威胁",
        "极度致命，需最高优先级处理"
      ]
    }
  }
}
```

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :---: | :--- |
| `model` | string | 否 | `"jev-latest"` | 模型标识，推荐使用默认路由模型 `"jev-latest"` 自动根据语言脚本与意图分流 |
| `state` | string \| object \| array | 是 | - | **当前状态上下文**。可以是小人的结构化属性字典、自然语言描述文本、或事件时序列表。受 `LAYA_MAX_STATE_BYTES` 约束（默认最大 256KB） |
| `questions` | dict[string, Question] | 是 | - | 决策问题字典，键为该决策项唯一标识（如 `"next_action"`, `"is_in_danger"`），数量受 `LAYA_MAX_QUESTIONS` 限制（默认 64） |

#### 3.4.1.1 当前状态（`state`）的三种传参形态

底层服务会将 `state` 自动序列化并作为背景上下文（Context）输入给模型推理。在小人/智能体场景下，支持以下三种组织方式：

1. **结构化对象 / 字典（推荐形态）**：
   直接传入小人的当前实时属性、背包、环境感知、数值指标等：
   ```json
   "state": {
     "id": "npc_102",
     "hp": 25,
     "hunger": 85,
     "current_task": "patrol",
     "target": "slime_01",
     "target_distance": 3.2
   }
   ```
   > **提示**：在各问题的 `instructions` 中，可以使用反引号引用状态字段名（例如 ``根据小人的 `hp` 和 `target_distance`...``），模型会精准关联对应属性进行决策。

2. **自然语言描述文本（字符串）**：
   如果您的游戏或智能体系统习惯使用自然语言描述小人的即时处境，可以直接传入文本：
   ```json
   "state": "小人当前生命值只剩25点，腹中饥饿，且正前方3米处有一只史莱姆正在发动攻击，背后不远处是安全营地。"
   ```

3. **时序动作 / 对话历史列表（数组）**：
   用于小人连续行为链、记忆流或上下文事件追踪：
   ```json
   "state": [
     { "time": "10:00", "event": "开始采集木材" },
     { "time": "10:05", "event": "遭遇野狼袭击，生命值下降至 30%" },
     { "time": "10:06", "event": "武器损坏，周围无队友支援" }
   ]
   ```


#### 3.4.2 问题类型定义（Question Types）

系统支持三种标准决策问题类型：

##### 1. `noul` (布尔 / 是否判断)
用于二元判断（是/否）。
```json
{
  "type": "noul",
  "instructions": "小人当前是否处于危险或需要撤退的状态？",
  "criteria": null
}
```
- `instructions` (必填): 判定指令/题干。
- `criteria` (可选): 可附加附加判定补充条件。

##### 2. `choice` (离散单选题)
从给定的多个预定义候选项中选取最佳选项。
```json
{
  "type": "choice",
  "instructions": "根据当前小人的生命值和周围环境，小人应该采取什么行动？",
  "criteria": {
    "attack": "敌人进入射程且自身血量充沛",
    "flee": "自身血量偏低或者被敌人包围",
    "patrol": "附近无异常，在区域内巡逻",
    "idle": "原地待命休整"
  }
}
```
- `criteria` (必填): 键值对字典（数量最多不超过 32，受 `LAYA_MAX_CHOICE_OPTIONS` 约束）。键为候选结果 ID，值为该选项的判定标准说明。

##### 3. `score` (阶梯评分题)
给出多级程度评分（按从低到高的等级数组评估）。
```json
{
  "type": "score",
  "instructions": "评估当前小人面临的威胁等级？",
  "criteria": [
    "完全安全，无威胁",
    "轻微警觉，有潜在敌人",
    "高度危险，受到直接攻击",
    "濒死绝境，即将阵亡"
  ]
}
```
- `criteria` (必填): 列表，必须至少包含 2 个等级描述，上限由 `LAYA_MAX_SCORE_LEVELS` 限制（默认 10）。

---

#### 3.4.3 响应体（Response Body）

```json
{
  "model": "laya-multilingual",
  "answers": {
    "next_action": {
      "choice": "flee",
      "confidence": 0.92
    },
    "is_in_danger": {
      "noul": true,
      "confidence": 0.89
    },
    "threat_level": {
      "score": 2,
      "level": "高度危险，受到直接攻击威胁",
      "confidence": 0.94
    }
  },
  "usage": {
    "input_tokens": 168,
    "output_tokens": 0
  }
}
```

- `answers`: 对应请求中各问题 key 的决策结果字典。
- `usage`: Token 统计信息。

---

## 4. 关于多主体 / 多个小人状态传递的架构设计说明

针对业务常见疑问：**“是否应该把所有小人的状态参数包在一次请求里调用接口？”**

1. **协议层支持**:
   `state` 字段支持 `list` 或 `dict`，技术上完全可以将多个小人的状态作为一个整体数组或集合传入（例如 `{"agents": [agent1, agent2, ...]}`）。
2. **决策粒度区别**:
   - **全局战略判断（适合单次聚合请求）**:
     如果决策问题是宏观的，例如：*“在当前战场中，哪个小人处于最危急状态？”* 或 *“整体阵型是否需要撤退？”*，此时适合把所有小人状态放在一个 `state` 中做全局判断。
   - **个体微观行为决策（推荐各小人单独调用）**:
     `systemone` 接口针对传入的 `state` 输出一套统一维度的 `answers`。如果需要为每一个小人独立决策其具体动作（如：小人A做Attack、小人B做Flee、小人C做Patrol），模型设计上要求每次决策针对特定小人的主视角上下文。
     - **推荐方式**: 客户端通过异步（`asyncio.gather` 或多线程）并发向 `POST /v1/systemone` 发送各个小人的独立决策请求；
     - **注意并发度**: 服务端通过 `LAYA_MAX_INFLIGHT`（默认 2）控制并发推理数量，高并发场景可根据服务器 GPU/CPU 资源调大该配置。

---

## 5. 错误处理与状态码

统一错误响应格式：
```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "错误详细描述",
    "param": "出错的字段路径（可选）"
  }
}
```

| 状态码 | 含义 | 说明 |
| :--- | :--- | :--- |
| `401 Unauthorized` | 身份验证失败 | 缺少或提供了错误的 `Authorization: Bearer <token>` |
| `422 Unprocessable Entity` | 参数校验失败 | `questions` 为空、题目数超限、选项数超限、`state` 体积超限等 |
| `503 Service Unavailable` | 服务未就绪 | 模型预加载尚未完成 |
| `529 Site Overloaded` | 推理超时或模型不可用 | 超过 `LAYA_REQUEST_TIMEOUT_SECONDS`（默认 60s）或推理异常 |

---

## 6. 调用示例代码

### 6.1 cURL 示例

```bash
curl -X POST http://localhost:8000/v1/systemone \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "jev-latest",
    "state": {
      "character_id": "player_001",
      "hp": 85,
      "energy": 90,
      "surroundings": ["tree", "friendly_npc", "river"],
      "last_action": "walk"
    },
    "questions": {
      "next_behavior": {
        "type": "choice",
        "instructions": "小人当前应该做什么？",
        "criteria": {
          "rest": "体力不足或疲惫时休息",
          "explore": "环境安全且状态良好时继续探索",
          "combat": "遇到敌人时战斗"
        }
      },
      "need_heal": {
        "type": "noul",
        "instructions": "小人是否需要立即回血补给？"
      }
    }
  }'
```

### 6.2 Python 异步批量并发调用（多小人独立决策最佳实践）

```python
"""
多小人独立状态并发调用 Laya Service 示例
@author hubin
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key"

# 定义决策问题模板
DECISION_QUESTIONS = {
    "action": {
        "type": "choice",
        "instructions": "根据小人自身状态选择下一步行动",
        "criteria": {
            "attack": "敌人距离小于5米且自身HP>30",
            "flee": "自身HP<=30且周围有敌人",
            "gather": "周围有可采集资源且无威胁",
            "idle": "无其他目标时待命",
        },
    },
    "in_danger": {
        "type": "noul",
        "instructions": "当前小人是否处于即时危险中？",
    },
}

async def decide_for_character(client: httpx.AsyncClient, character: dict):
    payload = {
        "model": "jev-latest",
        "state": character,
        "questions": DECISION_QUESTIONS,
    }
    response = await client.post(
        f"{BASE_URL}/v1/systemone",
        json=payload,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()
    return character["id"], result["answers"]

async def main():
    characters = [
        {"id": "c1", "name": "小人A", "hp": 20, "nearby_enemies": 2},
        {"id": "c2", "name": "小人B", "hp": 95, "nearby_enemies": 0, "has_wood": True},
        {"id": "c3", "name": "小人C", "hp": 80, "nearby_enemies": 1},
    ]

    async with httpx.AsyncClient() as client:
        tasks = [decide_for_character(client, char) for char in characters]
        results = await asyncio.gather(*tasks)

        for char_id, answers in results:
            print(f"[{char_id}] 决策结果: {answers}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. 环境变量配置参考

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `LAYA_API_KEY` | `""` | 服务 API Key，留空表示无需认证 |
| `LAYA_DEFAULT_MODEL` | `jev-latest` | 默认模型别名 |
| `LAYA_DEVICE` | `None` (auto) | 推理硬件平台，可设为 `cpu`, `cuda`, `auto` |
| `LAYA_PRELOAD` | `true` | 是否在服务启动时预加载 Router 模型权重 |
| `LAYA_HF_TOKEN` | `None` | Hugging Face 访问 Token（拉取权重时使用） |
| `LAYA_MAX_INFLIGHT` | `2` | 最大并发推理数信号量 |
| `LAYA_REQUEST_TIMEOUT_SECONDS` | `60.0` | 单次请求最大超时时间 |
| `LAYA_MAX_STATE_BYTES` | `262144` | 单次请求 `state` 序列化最大字节数（256KB） |
| `LAYA_MAX_QUESTIONS` | `64` | 单次请求包含的最大 question 个数 |
| `LAYA_MAX_CHOICE_OPTIONS` | `32` | 单个 choice 题型的最大选项数 |
| `LAYA_MAX_SCORE_LEVELS` | `10` | 单个 score 题型的最大层级数 |
| `LAYA_LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
