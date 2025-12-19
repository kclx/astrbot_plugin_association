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
    title           VARCHAR(100) NOT NULL COMMENT '任务标题',
    description     TEXT COMMENT '任务描述',
    reward          DECIMAL(10,2) NOT NULL COMMENT '任务报酬',
    deadline        DATETIME COMMENT '任务截止时间',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    FOREIGN KEY (clienter_id) REFERENCES clienter(id) ON DELETE CASCADE
) COMMENT='委托任务表，仅记录任务的基本信息';
```

> 注：
>
> - `clienter_id` 为 NOT NULL，每个任务必须有委托人
> - 不再包含 `status` 和 `adventurer_id` 字段，任务状态管理完全由 `quest_assign` 表负责
> - 此表仅存储任务的详情信息（标题、描述、报酬、截止时间等）
> - 任务的分配、执行、完成等状态由 `quest_assign` 表记录

---

## 4️⃣ 冒险者任务分配表（quest_assign）

```sql
CREATE TABLE quest_assign (
    id            VARCHAR(36) PRIMARY KEY COMMENT '分配记录ID，UUID',
    quest_id      VARCHAR(36) NOT NULL COMMENT '关联任务ID',
    adventurer_id VARCHAR(36) NOT NULL COMMENT '关联冒险者ID',
    assign_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '任务接取时间',
    submit_time   TIMESTAMP COMMENT '任务提交时间',
    confirm_time  TIMESTAMP COMMENT '任务确认完成时间',
    status        VARCHAR(20) DEFAULT 'ONGOING' CHECK (status IN ('UNANSWERED', 'ONGOING', 'SUBMITTED', 'CONFIRMED', 'FORCED_END', 'TIMEOUT')) COMMENT '任务分配状态：UNANSWERED=未接取, ONGOING=执行中, SUBMITTED=已提交, CONFIRMED=已确认, FORCED_END=强制终止, TIMEOUT=超时',

    FOREIGN KEY (quest_id) REFERENCES quest(id) ON DELETE CASCADE,
    FOREIGN KEY (adventurer_id) REFERENCES adventurer(id) ON DELETE CASCADE
) COMMENT='冒险者任务分配表，记录冒险者接取任务及进度，管理任务的完整生命周期';

CREATE UNIQUE INDEX uq_adventurer_active_quest
    ON quest_assign(adventurer_id)
    WHERE status IN ('ONGOING', 'SUBMITTED');
```

> 注：
>
> - **核心状态管理表**：任务的所有状态（接取、提交、确认等）都在此表管理
> - **时间戳字段**：
>   - `assign_time`：冒险者接取任务的时间
>   - `submit_time`：冒险者提交任务的时间
>   - `confirm_time`：委托人确认任务完成的时间
> - **唯一索引 `uq_adventurer_active_quest`**：
>   - 确保冒险者不能同时接取多个活跃任务（ONGOING 或 SUBMITTED 状态）
>   - SUBMITTED 状态也视为活跃，因为任务尚未最终确认完成
> - **完整历史记录**：记录所有任务分配的完整历史，包括已确认、超时、强制终止的记录
> - **状态含义**：
>   - `ONGOING`：任务执行中，冒险者正在完成任务
>   - `SUBMITTED`：冒险者已提交任务，等待委托人确认
>   - `CONFIRMED`：委托人确认任务完成，任务结束
>   - `TIMEOUT`：任务超时未完成
>   - `FORCED_END`：任务被强制终止（如冒险者休息或退出）

---

## 5️⃣ 任务材料表（quest_material）

```sql
CREATE TABLE quest_material (
    id              VARCHAR(36) PRIMARY KEY COMMENT '材料ID，UUID',
    quest_id        VARCHAR(36) NOT NULL COMMENT '关联任务ID',
    material_name   VARCHAR(100) NOT NULL COMMENT '材料名称',
    file_path       TEXT COMMENT '材料文件路径',
    upload_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '材料上传时间',
    type            VARCHAR(20) DEFAULT 'NONE' CHECK (type IN ('ILLUSTRATE', 'PROOF', 'NONE')) COMMENT '附件种类：ILLUSTRATE=任务需求, PROOF=任务完成证明',

    FOREIGN KEY (quest_id) REFERENCES quest(id) ON DELETE CASCADE
) COMMENT='任务材料表，记录冒险者提交的任务材料及文件';
```

> 注：
>
> - **材料提交**：冒险者在提交任务时可以附带材料（文本或文件）
> - **字段说明**：
>   - `material_name`：材料的名称或描述
>   - `file_path`：如果材料是文件，存储文件路径；如果是文本材料，可为空
>   - `upload_time`：材料上传的时间戳
> - **关联关系**：通过 `quest_assign_id` 关联到具体的任务分配记录
> - **级联删除**：当任务分配记录被删除时，关联的材料记录也会被删除

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

- **冒险者 ↔ 任务分配**：一对多关系，一个冒险者可以接多个任务（但同时只能有一个活跃任务）
- **委托人 → 任务**：一对多关系，一个委托人可以发布多个任务
- **任务 ↔ 分配记录**：一对多关系，一个任务可以有多条分配记录（支持任务重新分配）
- **分配记录 → 材料**：一对多关系，一次任务分配可以提交多个材料

## 任务生命周期

任务的状态管理完全由 `quest_assign` 表负责，`quest` 表仅存储任务详情。

### 正常流程

1. **任务发布**

   - 委托人创建任务，记录插入 `quest` 表
   - 系统自动推送给所有 IDLE 状态的冒险者

2. **UNANSWERED**（未接取）

   - 任务已发布但尚未被冒险者接取
   - 可选：在 `quest_assign` 表预创建记录，状态为 `UNANSWERED`
   - 或者不创建记录，仅在 `quest` 表中存在
   - 任务对所有符合条件的冒险者可见

3. **ONGOING**（执行中）

   - 冒险者接取任务，在 `quest_assign` 表创建记录（或更新状态为 `ONGOING`）
   - 冒险者状态（`adventurer.status`）变为 `WORKING`
   - `quest_assign.assign_time` 记录接取时间

4. **SUBMITTED**（已提交）

   - 冒险者完成任务并提交
   - `quest_assign.status` 更新为 `SUBMITTED`
   - `quest_assign.submit_time` 记录提交时间
   - 可选：在 `quest_material` 表中记录提交的材料
   - 系统通知委托人任务已提交

5. **CONFIRMED**（已确认）
   - 委托人确认任务完成
   - `quest_assign.status` 更新为 `CONFIRMED`
   - `quest_assign.confirm_time` 记录确认时间
   - 冒险者状态恢复为 `IDLE`
   - 任务生命周期结束

### 异常流程

6. **TIMEOUT**（超时）

   - 任务超过 `quest.deadline` 仍未完成
   - `quest_assign.status` 更新为 `TIMEOUT`
   - 冒险者状态恢复为 `IDLE`

7. **FORCED_END**（强制终止）
   - 冒险者在任务执行期间选择休息或退出
   - `quest_assign.status` 更新为 `FORCED_END`
   - 冒险者状态更新为 `REST` 或 `QUIT`
   - 任务可重新分配给其他冒险者

## 状态转移图

```
quest_assign.status 状态转移：

UNANSWERED ──→ ONGOING ────┐
                           ├──→ SUBMITTED ──→ CONFIRMED（正常完成）
                           │
            ├──→ TIMEOUT（超时）
            │
            └──→ FORCED_END（强制终止）
```

## 关键约束

1. **唯一活跃任务**：`uq_adventurer_active_quest` 索引确保每个冒险者同时只能有一个 `ONGOING` 或 `SUBMITTED` 状态的任务
2. **状态一致性**：冒险者状态（`adventurer.status`）必须与任务分配状态（`quest_assign.status`）保持一致
3. **时间戳完整性**：
   - `assign_time`：必填，任务接取时自动生成
   - `submit_time`：仅在状态为 `SUBMITTED` 或 `CONFIRMED` 时有值
   - `confirm_time`：仅在状态为 `CONFIRMED` 时有值
