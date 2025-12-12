"""API密钥认证模块"""

import os
import time
import threading
from typing import Dict, Optional, Set
from pathlib import Path


class APIKeyManager:
    """API密钥管理器"""

    def __init__(self, keys_file: str = None):
        self.keys_file = keys_file or str(Path(__file__).parent.parent.parent / "config" / "api_keys.txt")
        self.api_keys: Dict[str, Dict] = {}
        self.active_keys: Set[str] = set()
        self.last_reload_time = 0
        self._lock = threading.Lock()

    def load_keys(self) -> bool:
        """从配置文件加载API密钥"""
        try:
            if not os.path.exists(self.keys_file):
                print(f"⚠️ API密钥配置文件不存在: {self.keys_file}")
                return False

            with self._lock:
                self.api_keys.clear()
                self.active_keys.clear()

                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()

                        # 跳过空行和注释行
                        if not line or line.startswith('#'):
                            continue

                        # 解析格式: key_name:api_key:description
                        parts = line.split(':', 2)
                        if len(parts) < 2:
                            print(f"⚠️ API密钥配置格式错误 (第{line_num}行): {line}")
                            continue

                        key_name = parts[0].strip()
                        api_key = parts[1].strip()
                        description = parts[2].strip() if len(parts) > 2 else ""

                        # 验证密钥格式
                        if not api_key.startswith('sk-'):
                            print(f"⚠️ API密钥格式不正确 (第{line_num}行): {key_name}")
                            continue

                        self.api_keys[api_key] = {
                            'name': key_name,
                            'description': description,
                            'created_at': int(time.time()),
                            'usage_count': 0,
                            'last_used': 0,
                            'is_active': True
                        }

                        self.active_keys.add(api_key)

            self.last_reload_time = time.time()
            print(f"✅ 已加载 {len(self.api_keys)} 个API密钥")
            return True

        except Exception as e:
            print(f"❌ 加载API密钥失败: {e}")
            return False

    def validate_key(self, api_key: str) -> bool:
        """验证API密钥是否有效"""
        if not api_key:
            return False

        # 规范化密钥：去除前导/尾随空格
        api_key = api_key.strip()
        
        # 检查是否需要重新加载配置
        if self._should_reload():
            self.load_keys()

        with self._lock:
            if api_key in self.api_keys and self.api_keys[api_key]['is_active']:
                # 更新使用统计
                self.api_keys[api_key]['usage_count'] += 1
                self.api_keys[api_key]['last_used'] = int(time.time())
                return True

        return False

    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """获取密钥信息"""
        if not api_key:
            return None
        
        # 规范化密钥：去除前导/尾随空格
        api_key = api_key.strip()
        
        with self._lock:
            return self.api_keys.get(api_key)

    def deactivate_key(self, api_key: str) -> bool:
        """停用API密钥"""
        with self._lock:
            if api_key in self.api_keys:
                self.api_keys[api_key]['is_active'] = False
                self.active_keys.discard(api_key)
                return True
            return False

    def activate_key(self, api_key: str) -> bool:
        """激活API密钥"""
        with self._lock:
            if api_key in self.api_keys:
                self.api_keys[api_key]['is_active'] = True
                self.active_keys.add(api_key)
                return True
            return False

    def get_stats(self) -> Dict:
        """获取密钥使用统计"""
        with self._lock:
            total_keys = len(self.api_keys)
            active_keys = len([k for k in self.api_keys.values() if k['is_active']])
            total_usage = sum(k['usage_count'] for k in self.api_keys.values())

            recent_usage = len([
                k for k in self.api_keys.values()
                if k['last_used'] > int(time.time()) - 3600  # 最近1小时
            ])

            return {
                'total_keys': total_keys,
                'active_keys': active_keys,
                'inactive_keys': total_keys - active_keys,
                'total_usage': total_usage,
                'recent_usage': recent_usage,
                'last_reload': self.last_reload_time
            }

    def _should_reload(self) -> bool:
        """检查是否需要重新加载配置文件"""
        try:
            if not os.path.exists(self.keys_file):
                return False

            file_mtime = os.path.getmtime(self.keys_file)
            return file_mtime > self.last_reload_time
        except:
            return False

    def create_key(self, key_name: str, description: str = "") -> Optional[str]:
        """创建新的API密钥"""
        import secrets

        # 生成安全的随机密钥
        api_key = f"sk-{secrets.token_urlsafe(32)}"

        with self._lock:
            self.api_keys[api_key] = {
                'name': key_name,
                'description': description,
                'created_at': int(time.time()),
                'usage_count': 0,
                'last_used': 0,
                'is_active': True
            }
            self.active_keys.add(api_key)

        return api_key

    def save_keys(self) -> bool:
        """保存密钥到文件"""
        try:
            with self._lock:
                lines = [
                    "# API访问密钥配置文件",
                    "# 格式: key_name:api_key:description",
                    "# 每行一个密钥配置，以#开头的行为注释",
                    "# 此文件由程序自动生成，请谨慎编辑",
                    ""
                ]

                for api_key, info in self.api_keys.items():
                    status = "inactive" if not info['is_active'] else ""
                    lines.append(f"{info['name']}:{api_key}:{info['description']} {status}")

                with open(self.keys_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))

            return True
        except Exception as e:
            print(f"❌ 保存API密钥失败: {e}")
            return False


# 全局密钥管理器实例
api_key_manager = APIKeyManager()