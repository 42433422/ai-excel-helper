# RBAC 权限系统实现计划

## 现状分析

- **User 模型**：已有 `username`, `password`, `role` 字段（role 默认 "user"）
- **Session 模型**：已定义但未使用
- **无认证**：所有 API 公开访问
- **部署方式**：本地部署

---

## 目标

为本地部署版本实现完整的 RBAC 权限系统，包括：
1. 用户认证（登录/登出）
2. 基于角色的访问控制
3. 权限装饰器
4. 用户管理 API

---

## 实现步骤

### Phase 1: 数据模型扩展

#### 1.1 创建 Permission 模型
- **文件**: `app/db/models/permission.py`
- **内容**:
  - `Permission` 表：id, name, code, description, module
  - 预定义权限：customer.view, customer.edit, product.view, product.edit, shipment.view, shipment.edit, shipment.approve, print, admin.manage_users, admin.system_config

#### 1.2 创建 RolePermission 关联表
- **文件**: `app/db/models/permission.py`
- **内容**:
  - `role_permissions` 多对多关联表

#### 1.3 扩展 User 模型
- **文件**: `app/db/models/user.py`
- **修改**:
  - 添加 `email` 字段
  - 添加 `is_active` 字段
  - 添加 `created_by` 字段

#### 1.4 创建 Alembic 迁移
- **命令**: `alembic revision --autogenerate -m "add_rbac_tables"`

---

### Phase 2: 认证服务

#### 2.1 创建认证服务
- **文件**: `app/services/auth_service.py`
- **功能**:
  - `authenticate(username, password)` - 验证用户密码
  - `create_session(user_id)` - 创建会话
  - `validate_session(session_id)` - 验证会话
  - `logout(session_id)` - 删除会话
  - 密码加密使用 werkzeug.security

#### 2.2 创建 Session 管理
- **文件**: `app/services/session_service.py`
- **功能**:
  - Session 存储（SQLite）
  - 过期时间检查
  - 自动清理过期 Session

---

### Phase 3: 权限装饰器

#### 3.1 创建权限装饰器
- **文件**: `app/extensions/auth.py`
- **装饰器**:
  - `@login_required` - 检查登录状态
  - `@role_required(roles)` - 检查角色
  - `@permission_required(permission_code)` - 检查权限

#### 3.2 创建请求上下文
- **文件**: `app/extensions/auth.py`
- **内容**:
  - `get_current_user()` - 获取当前登录用户
  - `get_current_session()` - 获取当前会话

---

### Phase 4: 认证 API 路由

#### 4.1 创建认证路由
- **文件**: `app/routes/auth.py`
- **端点**:
  - `POST /api/auth/login` - 登录
  - `POST /api/auth/logout` - 登出
  - `GET /api/auth/me` - 获取当前用户信息
  - `GET /api/auth/session/validate` - 验证会话

#### 4.2 注册蓝图
- **文件**: `app/routes/__init__.py`
- **修改**: 注册 auth_bp

---

### Phase 5: 用户管理 API

#### 5.1 创建用户管理路由
- **文件**: `app/routes/auth.py`
- **端点**:
  - `GET /api/users` - 列出用户（仅 admin）
  - `POST /api/users` - 创建用户（仅 admin）
  - `PUT /api/users/<id>` - 更新用户（仅 admin）
  - `DELETE /api/users/<id>` - 删除用户（仅 admin）
  - `GET /api/users/<id>` - 获取用户详情（仅 admin）

#### 5.2 创建用户服务
- **文件**: `app/services/user_service.py`
- **功能**:
  - CRUD 操作
  - 密码重置
  - 角色分配

---

### Phase 6: 数据库迁移

#### 6.1 执行迁移
```bash
cd e:\FHD\XCAGI
alembic upgrade head
```

#### 6.2 创建默认管理员
- 在迁移脚本或启动时创建默认 admin 用户（用户名: admin, 密码: admin123）

---

### Phase 7: 前端集成（可选）

#### 7.1 前端适配
- 创建登录页面组件
- 添加请求拦截器携带 Session
- 添加登出功能
- 添加用户管理界面

---

## 权限矩阵

| 功能模块 | viewer | operator | admin |
|---------|--------|----------|-------|
| 查看客户 | ✅ | ✅ | ✅ |
| 编辑客户 | ❌ | ✅ | ✅ |
| 查看产品 | ✅ | ✅ | ✅ |
| 编辑产品 | ❌ | ✅ | ✅ |
| 查看出货单 | ✅ | ✅ | ✅ |
| 创建出货单 | ❌ | ✅ | ✅ |
| 审批出货单 | ❌ | ❌ | ✅ |
| 标签打印 | ❌ | ✅ | ✅ |
| 用户管理 | ❌ | ❌ | ✅ |
| 系统配置 | ❌ | ❌ | ✅ |

---

## 关键文件清单

```
新建文件:
- app/db/models/permission.py          # 权限模型
- app/services/auth_service.py         # 认证服务
- app/services/session_service.py      # Session 服务
- app/services/user_service.py         # 用户服务
- app/extensions/auth.py               # 权限装饰器
- app/routes/auth.py                   # 认证 API
- alembic/versions/xxxx_add_rbac.py    # 数据库迁移

修改文件:
- app/db/models/user.py                # 扩展 User 模型
- app/db/models/__init__.py            # 导出新模型
- app/routes/__init__.py               # 注册 auth 蓝图
- app/db/init_db.py                    # 创建默认管理员
```

---

## 技术选型

- **密码加密**: werkzeug.security（Flask 内置）
- **Session 管理**: SQLite + 自定义服务
- **权限装饰器**: 自定义装饰器 + functools.wraps
