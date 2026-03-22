# 开发规范

## 代码规范

### Python 代码规范

1. **格式化**
   - 使用 `black` 格式化所有 Python 代码
   - 使用 `isort` 排序 imports

2. **类型检查**
   - 使用 `mypy` 进行类型检查
   - 所有公共函数必须有类型注解

3. **代码风格**
   - 遵循 PEP 8
   - 最大行长 120 字符

4. **导入顺序**
   ```python
   # 标准库
   import os
   import sys

   # 第三方库
   import flask
   import sqlalchemy

   # 本地库
   from app import models
   from app.services import xxx
   ```

### JavaScript 代码规范

1. **格式化**
   - 使用 Prettier 格式化代码
   - 使用 ESLint 检查代码

2. **代码风格**
   - 使用 ES6+ 语法
   - 使用 const/let 而不是 var

## Git 规范

### 分支命名
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `refactor/xxx` - 重构
- `docs/xxx` - 文档更新

### Commit 规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档
- `style`: 格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 示例
```
feat(auth): 添加用户注册功能

添加用户注册功能，包括：
- 验证码发送
- 密码强度验证
- 邮箱验证

Closes #123
```

## 代码审查规范

### Review 清单
- [ ] 代码符合规范
- [ ] 有适当的测试
- [ ] 没有明显的 bug
- [ ] 注释清晰完整
- [ ] 性能考虑
- [ ] 安全性考虑

### Review 流程
1. 创建 Pull Request
2. 至少 1 人 Review
3. 所有问题解决
4. 合并到主分支
