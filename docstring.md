## 其实就是方便我记一下这个谷歌风格注释的关键词

### 常用 Section 一览

| Section | 用途 |
| --- | --- |
| `Args:` | 参数说明 |
| `Returns:` | 返回值说明 |
| `Yields:` | 生成器函数用，替代 Returns |
| `Raises:` | 可能抛出的异常 |
| `Attributes:` | 类的属性（写在类的 docstring 里） |
| `Example:` / `Examples:` | 使用示例 |
| `Note:` | 需要特别提醒的事项 |
| `Todo:` | 待办事项 |

### 常用仓库 commit 信息

格式如下:
```
<type>(<scope>): <subject>

<body>

<footer>
```
type 常见取值：

| type | 含义 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档修改 |
| `style` | 格式调整（不影响代码逻辑，如空格、分号） |
| `refactor` | 重构（既不是新功能也不是修 bug） |
| `perf` | 性能优化 |
| `test` | 增加或修改测试 |
| `build` | 构建系统或依赖变更（如 webpack、npm） |
| `ci` | CI 配置文件和脚本的变化 |
| `chore` | 其他杂项（不涉及 src 或 test） |
| `revert` | 回滚之前的 commit |
|

示例:
```
feat(auth): 添加用户登录接口

fix(api): 修复分页参数越界导致的 500 错误

docs(readme): 更新安装说明
```

破坏性变更要在 footer 标注 BREAKING CHANGE:,或者在 type/scope 后加 !:
```
feat(api)!: 修改用户接口返回结构

BREAKING CHANGE: user.name 拆分为 firstName 和 lastName
```
这种格式的好处是可以配合工具(如 semantic-release、commitlint)自动生成 changelog、自动决定版本号(major/minor/patch)。
