# 数据库表结构

本文档详细说明了冒险者协会插件使用的数据库表结构。

## 1️⃣ 冒险者表（adventurer）

```sql
CREATE TABLE adventurer (
    id            VARCHAR(36) PRIMARY KEY COMMENT '冒险者唯一ID，UUID',
    name          VARCHAR(36) NOT NULL COMMENT '冒险者名称',
    status        ENUM('IDLE', 'WORKING', 'REST', 'QUIT') DEFAULT 'IDLE' COMMENT '当前状态：IDLE=空闲, WORKING=执行任务, REST=休息, QUIT=退出',
    contact_way       VARCHAR(36) NOT NULL COMMENT '联系方式',
    contact_number       VARCHAR(36) NOT NULL COMMENT '联系号码',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='冒险者表，记录所有冒险者及其当前状态';
```

---

## 2️⃣ 委托人表（clienter）

```sql
CREATE TABLE clienter (
    id             VARCHAR(36) PRIMARY KEY COMMENT '委托人唯一ID，UUID',
    name           VARCHAR(36) NOT NULL COMMENT '委托人名称',
    contact_way    VARCHAR(36) NOT NULL COMMENT '联系方式（平台名称）',
    contact_number VARCHAR(36) NOT NULL COMMENT '联系号码（平台用户ID）',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='委托人表，记录所有发布任务的委托人信息';
```

---

## 3️⃣ 委托任务表（quest）

```sql
CREATE TABLE quest (
    id              VARCHAR(36) PRIMARY KEY COMMENT '委托唯一ID，UUID',
    clienter_id     VARCHAR(36) NOT NULL COMMENT '发布任务的委托人ID',
    adventurer_id   VARCHAR(36) COMMENT '当前接取任务的冒险者ID（NULL表示未被接取）',
    title           VARCHAR(100) NOT NULL COMMENT '任务标题',
    description     TEXT COMMENT '任务描述',
    reward          DECIMAL(10,2) NOT NULL COMMENT '任务报酬',
    deadline        DATETIME COMMENT '任务截止时间',
    status          VARCHAR(20) DEFAULT 'PUBLISHED' CHECK (status IN ('PUBLISHED', 'ASSIGNED', 'COMPLETED', 'TIMEOUT', 'CLOSED')) COMMENT '任务状态：PUBLISHED=已发布, ASSIGNED=已接取, COMPLETED=已完成, TIMEOUT=超时未完成, CLOSED=已关闭',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    FOREIGN KEY (clienter_id) REFERENCES clienter(id) ON DELETE CASCADE,
    FOREIGN KEY (adventurer_id) REFERENCES adventurer(id) ON DELETE SET NULL
) COMMENT='委托任务表，记录任务信息及状态';
```

> 注：
> - `clienter_id` 为 NOT NULL，每个任务必须有委托人
> - `adventurer_id` 可为空，表示任务尚未被接取
> - 当任务被接取时，`adventurer_id` 指向当前执行任务的冒险者
> - `quest_assign` 表记录完整的任务分配历史，而此字段仅记录当前状态

---

## 4️⃣ 冒险者任务分配表（quest_assign）

```sql
CREATE TABLE quest_assign (
    id            VARCHAR(36) PRIMARY KEY COMMENT '分配记录ID，UUID',
    quest_id      VARCHAR(36) NOT NULL COMMENT '关联任务ID',
    adventurer_id VARCHAR(36) NOT NULL COMMENT '关联冒险者ID',
    assign_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '任务接取时间',
    finish_time   TIMESTAMP COMMENT '任务完成时间',
    status        VARCHAR(20) DEFAULT 'ONGOING' CHECK (status IN ('ONGOING', 'FINISHED', 'FORCED_END', 'TIMEOUT', 'CHECK_FINISHED')) COMMENT '任务分配状态：ONGOING=执行中, FINISHED=完成, FORCED_END=强制终止, TIMEOUT=超时, CHECK_FINISHED=确认完成',

    FOREIGN KEY (quest_id) REFERENCES quest(id) ON DELETE CASCADE,
    FOREIGN KEY (adventurer_id) REFERENCES adventurer(id) ON DELETE CASCADE
) COMMENT='冒险者任务分配表，记录冒险者接取任务及进度';

CREATE UNIQUE INDEX uq_adventurer_ongoing_quest
    ON quest_assign(adventurer_id)
    WHERE status = 'ONGOING';
```

> 注：
> - `uq_adventurer_ongoing_quest` 唯一索引确保冒险者不能同时接多个 `ONGOING` 任务
> - 此表记录完整的任务分配历史，包括已完成、超时、强制终止的记录
> - 当前正在执行的任务同时会反映在 `quest.adventurer_id` 字段中
> - 支持未来功能：任务材料提交、任务重新分配、超时处理等

---

## 5️⃣ 任务材料表（quest_material）

```sql
CREATE TABLE quest_material (
    id              VARCHAR(36) PRIMARY KEY COMMENT '材料ID，UUID',
    quest_assign_id VARCHAR(36) NOT NULL COMMENT '关联任务分配记录ID',
    material_name   VARCHAR(100) NOT NULL COMMENT '材料名称',
    amount          INT DEFAULT 1 COMMENT '材料数量',

    FOREIGN KEY (quest_assign_id) REFERENCES quest_assign(id) ON DELETE CASCADE
) COMMENT='任务材料表，记录冒险者提交的任务材料';
```

---

## 6️⃣ 系统日志表（system_log）

```sql
CREATE TABLE system_log (
    id            VARCHAR(36) PRIMARY KEY COMMENT '日志ID，UUID',
    event         VARCHAR(100) NOT NULL COMMENT '事件类型，例如：发布任务、接取任务、完成任务、更换冒险者等',
    detail        TEXT COMMENT '事件详细描述，可存储JSON或文字信息',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '事件发生时间'
) COMMENT='系统操作日志表，记录任务系统各类操作';
```

## 表关系说明

- **冒险者 ↔ 任务**：一对多关系，一个冒险者可以接多个任务（但同时只能有一个 ONGOING 状态）
- **委托人 → 任务**：一对多关系，一个委托人可以发布多个任务
- **任务 ↔ 分配记录**：一对多关系，一个任务可以有多条分配记录（支持任务重新分配）
- **分配记录 → 材料**：一对多关系，一次任务分配可以提交多个材料

## 任务生命周期

1. **PUBLISHED**（已发布）：委托人创建任务 → 自动推送给 IDLE 状态的冒险者
2. **ASSIGNED**（已分配）：冒险者接取任务 → 冒险者状态变为 WORKING
3. **COMPLETED**（已完成）：冒险者提交任务 → 委托人收到通知
4. **CLOSED**（已关闭）：委托人确认任务 → 冒险者状态恢复为 IDLE
