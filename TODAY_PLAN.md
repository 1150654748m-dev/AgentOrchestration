# AgentOrchestration Bounty 执行计划

**日期**: 2026-05-23  
**状态**: PR #2000 等待审核中，开始新任务

---

## PR #2000 状态

| 项目 | 状态 |
|------|------|
| 状态 | 🟡 OPEN |
| 提交时间 | 2026-05-22 03:30 UTC (约30小时前) |
| 评论 | 无 |
| 审核 | 待审核 |
| 预计审核 | 1-3天 |

---

## 🎯 今日执行任务

### 任务1: #2623 - $6,000 - SDK Task Timeout验证

**问题**: task decorator 接受 0 或负数 timeout，导致 asyncio.wait_for 立即失败

**修复方案**:
```python
def task(name: Optional[str] = None, retries: int = 0, timeout: int = 300):
    # 验证 timeout 为正数
    if timeout <= 0:
        raise ValueError(f"timeout must be positive, got {timeout}")
    ...
```

**测试**:
```python
def test_task_rejects_non_positive_timeout(self):
    with pytest.raises(ValueError):
        @task(timeout=0)
        async def bad_task(): pass
    
    with pytest.raises(ValueError):
        @task(timeout=-1)
        async def bad_task2(): pass
```

**估计时间**: 2小时  
**时薪**: $3,000/h

---

### 任务2: #2618 - $3,000 - SDK 空白Agent名验证

**问题**: register_agent 接受空或空白字符的 agent name

**修复方案**:
```python
def register_agent(self, name: str, agent_type: str, config: Dict = None) -> Dict:
    # 验证 name 非空
    if not name or not name.strip():
        raise ValueError("agent name cannot be empty or whitespace")
    name = name.strip()
    ...
```

**测试**:
```python
def test_register_agent_rejects_blank_name(self):
    client = OrchestratorClient()
    with pytest.raises(ValueError):
        client.register_agent("", "test_type")
    with pytest.raises(ValueError):
        client.register_agent("   ", "test_type")
```

**估计时间**: 1小时  
**时薪**: $3,000/h

---

## 📋 后续任务队列

| Issue | 赏金 | 任务 | 优先级 |
|-------|------|------|--------|
| #2676 | $2,000 | Webhook 订阅过滤验证 | 高 |
| #2594 | $2,000 | Queue 异常payload处理 | 高 |
| #2671 | $6,000 | Auth 防止绕过 | 中 |
| #2658 | $7,000 | API SSE cursor | 中 |

---

## 执行步骤

1. ✅ 克隆仓库
2. 🔄 创建分支 `fix-2623-task-timeout`
3. ⏳ 修复 decorators.py
4. ⏳ 添加测试
5. ⏳ 提交 PR
6. ⏳ 创建分支 `fix-2618-blank-agent-name`
7. ⏳ 修复 client.py
8. ⏳ 添加测试
9. ⏳ 提交 PR

---

**开始时间**: 2026-05-23 09:45  
**预计完成**: 2026-05-23 13:00
