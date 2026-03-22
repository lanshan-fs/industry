# Django Auth Backend

当前目录承接平台的 Django 版认证后端，只接管 `/api/auth/*`：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/send-code`
- `POST /api/auth/reset-password`
- `GET /api/auth/health`

## 运行方式

```bash
python3 -m pip install -r /Users/bluem/Projects/Web/industrial_chain/backend_django/requirements.txt
python3 /Users/bluem/Projects/Web/industrial_chain/backend_django/manage.py runserver 127.0.0.1:8000
```

## 数据约定

- 使用根目录 `.env` 中的 `DB_*`、`JWT_SECRET`、`EMAIL_*`
- 直接连接 MySQL 中的 `users` 和 `user_domains`
- 不再使用 `user_basic`

## 当前边界

- 只重构认证模块，不接管其余 `/api/*`
- 前端开发态通过 `project/vite.config.ts` 将 `/api/auth` 代理到 `127.0.0.1:8000`
- 其余 `/api` 仍由现有 Express 服务处理
