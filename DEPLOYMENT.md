# 🚀 Deployment Instructions

## Шаг 1: Push в GitHub

```bash
cd /home/claude/financial-methodologies-kb

# Выполнить скрипт для push
./push-to-github.sh

# Или вручную:
git add .
git commit -m "Initial commit: Financial Methodologies KB v1.0.0"
git remote add origin https://github.com/leval907/financial-methodologies-kb.git
git push -u origin main
```

## Шаг 2: Клонирование на сервер

```bash
# На вашем сервере (kb.findbc.ru)
cd /var/www  # или где у вас проекты

# Клонировать репозиторий
git clone https://github.com/leval907/financial-methodologies-kb.git

cd financial-methodologies-kb

# Проверить что всё на месте
ls -la docs/
ls -la data/
```

## Шаг 3: Настройка finance-knowledge для интеграции

### 3.1 Добавить GitHub Sync Service

Создайте файл в `finance-knowledge`:

```python
# finance-knowledge/api/services/github_sync.py

import git
import json
from pathlib import Path
from .knowledge_indexer import KnowledgeIndexer
from .arango_service import ArangoService

class GitHubSyncService:
    def __init__(self):
        self.repo_path = Path("/var/www/financial-methodologies-kb")
        self.indexer = KnowledgeIndexer()
        self.db = ArangoService()
    
    async def sync_from_github(self, repository: str, commit: str):
        """Sync knowledge base from GitHub"""
        try:
            # 1. Pull latest
            if self.repo_path.exists():
                repo = git.Repo(self.repo_path)
                repo.remotes.origin.pull()
            else:
                git.Repo.clone_from(
                    f"https://github.com/{repository}.git",
                    self.repo_path
                )
            
            # 2. Index knowledge base
            await self.indexer.index_directory(
                path=self.repo_path / "docs",
                force_reindex=True
            )
            
            # 3. Load structured data
            await self._load_json_data()
            
            print(f"✅ Sync completed for commit {commit}")
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            raise
    
    async def _load_json_data(self):
        """Load indicators and methodologies from JSON"""
        
        # Load indicators
        indicators_path = self.repo_path / "data/indicators/indicators-library.json"
        if indicators_path.exists():
            with open(indicators_path) as f:
                data = json.load(f)
                await self.db.load_indicators(data["indicators"])
        
        # Load methodologies
        methodologies_path = self.repo_path / "data/methodologies/methodologies.json"
        if methodologies_path.exists():
            with open(methodologies_path) as f:
                data = json.load(f)
                await self.db.load_methodologies(data["methodologies"])
```

### 3.2 Добавить Admin Endpoint

```python
# finance-knowledge/api/routers/admin.py

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from ..services.github_sync import GitHubSyncService
from ..config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])
sync_service = GitHubSyncService()

def verify_sync_token(token: str):
    if token != settings.SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid sync token")

@router.post("/sync")
async def trigger_sync(
    request: dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_sync_token)
):
    """Triggered by GitHub webhook"""
    background_tasks.add_task(
        sync_service.sync_from_github,
        repository=request["repository"],
        commit=request["commit"]
    )
    return {"status": "sync_started", "commit": request["commit"]}
```

### 3.3 Добавить в .env

```bash
# /var/www/finance-knowledge/.env

SYNC_TOKEN=your-secret-token-here
# Генерируйте сильный токен:
# openssl rand -hex 32
```

## Шаг 4: Настройка GitHub Secrets

1. Перейдите в Settings → Secrets and variables → Actions
2. Создайте секрет `SYNC_TOKEN` с тем же значением, что в .env

## Шаг 5: Первая синхронизация

```bash
# На сервере
cd /var/www/finance-knowledge

# Активировать venv если используется
source venv/bin/activate

# Запустить первую синхронизацию
python -c "
import asyncio
from api.services.github_sync import GitHubSyncService

async def main():
    sync = GitHubSyncService()
    await sync.sync_from_github('leval907/financial-methodologies-kb', 'initial')

asyncio.run(main())
"
```

## Шаг 6: Настройка Frontend (Web UI)

### 6.1 Создать директорию для frontend

```bash
cd /var/www/finance-knowledge
mkdir -p web
cd web

# Инициализировать Vite + React + TypeScript
npm create vite@latest . -- --template react-ts

# Установить зависимости
npm install
npm install axios react-router-dom @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 6.2 Базовая структура

```
web/
├── src/
│   ├── components/
│   │   ├── MethodologyCard.tsx
│   │   ├── IndicatorView.tsx
│   │   ├── ChatInterface.tsx
│   │   └── Search.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Methodologies.tsx
│   │   ├── Indicators.tsx
│   │   └── Chat.tsx
│   ├── services/
│   │   └── api.ts
│   └── App.tsx
├── package.json
└── vite.config.ts
```

### 6.3 API Service

```typescript
// web/src/services/api.ts

const API_BASE = 'https://kb.findbc.ru/api';

export const api = {
  // Methodologies
  async getMethodologies() {
    const response = await fetch(`${API_BASE}/methodologies`);
    return response.json();
  },
  
  async getMethodology(id: string) {
    const response = await fetch(`${API_BASE}/methodologies/${id}`);
    return response.json();
  },
  
  // Indicators
  async getIndicators(methodology?: string) {
    const url = methodology 
      ? `${API_BASE}/indicators?methodology=${methodology}`
      : `${API_BASE}/indicators`;
    const response = await fetch(url);
    return response.json();
  },
  
  // Search
  async search(query: string) {
    const response = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    return response.json();
  },
  
  // Chat
  async chat(message: string, context?: any) {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context })
    });
    return response.json();
  }
};
```

## Шаг 7: Nginx Configuration

```nginx
# /etc/nginx/sites-available/kb.findbc.ru

server {
    listen 80;
    server_name kb.findbc.ru;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name kb.findbc.ru;
    
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    
    # Frontend (Web UI)
    location / {
        root /var/www/finance-knowledge/web/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support (for real-time features)
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Шаг 8: Systemd Service

```ini
# /etc/systemd/system/finance-knowledge-api.service

[Unit]
Description=Finance Knowledge API
After=network.target arangodb.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/finance-knowledge
Environment="PATH=/var/www/finance-knowledge/venv/bin"
ExecStart=/var/www/finance-knowledge/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Активировать:
```bash
sudo systemctl daemon-reload
sudo systemctl enable finance-knowledge-api
sudo systemctl start finance-knowledge-api
sudo systemctl status finance-knowledge-api
```

## Шаг 9: Проверка

### 9.1 API Health Check
```bash
curl https://kb.findbc.ru/api/health
# Expected: {"status":"ok","version":"1.0.0"}
```

### 9.2 Get Methodologies
```bash
curl https://kb.findbc.ru/api/methodologies
```

### 9.3 Web UI
Откройте в браузере: https://kb.findbc.ru

## Шаг 10: Тестирование автосинхронизации

1. Внесите изменения в GitHub репозиторий
2. Push в main branch
3. GitHub Actions запустит workflow
4. Workflow вызовет `/api/admin/sync`
5. Сервер обновится автоматически

Проверить статус:
```bash
# Логи синхронизации
journalctl -u finance-knowledge-api -f | grep sync
```

## 📋 Checklist

- [ ] Repository pushed to GitHub
- [ ] Cloned on server
- [ ] GitHub sync service added
- [ ] Admin endpoint configured
- [ ] SYNC_TOKEN set in .env and GitHub Secrets
- [ ] First sync completed
- [ ] Frontend initialized
- [ ] Nginx configured
- [ ] SSL certificate installed
- [ ] Systemd service running
- [ ] API responding
- [ ] Web UI accessible
- [ ] Auto-sync tested

## 🎉 Готово!

Ваша база знаний теперь доступна:
- **GitHub**: https://github.com/leval907/financial-methodologies-kb
- **Web UI**: https://kb.findbc.ru
- **API**: https://kb.findbc.ru/api
- **API Docs**: https://kb.findbc.ru/api/docs

## 🔄 Workflow

```
Developer → Push to GitHub → GitHub Actions → Webhook → Server Sync → Updated KB
```

## 📞 Support

При проблемах:
1. Проверить логи: `journalctl -u finance-knowledge-api`
2. Проверить GitHub Actions: https://github.com/leval907/financial-methodologies-kb/actions
3. Проверить sync status: `curl https://kb.findbc.ru/api/admin/sync/status/latest`
