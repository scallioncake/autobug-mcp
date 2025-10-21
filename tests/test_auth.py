"""
测试用例：模拟用户认证失败场景
用于测试 auto-bug MCP 工具的错误分析能力
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Optional


class AuthError(Exception):
    """认证相关异常"""
    pass


class UserManager:
    def __init__(self, users_file: Path):
        self.users_file = users_file
        self.users = self._load_users()
    
    def _load_users(self) -> Dict[str, Dict]:
        """加载用户数据"""
        if not self.users_file.exists():
            raise FileNotFoundError(f"用户数据文件不存在: {self.users_file}")
        
        with self.users_file.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    
    def authenticate(self, username: str, password: str) -> bool:
        """用户认证"""
        if username not in self.users:
            raise AuthError(f"用户不存在: {username}")
        
        user = self.users[username]
        if user.get("password") != password:
            raise AuthError(f"密码错误，用户: {username}")
        
        if not user.get("active", True):
            raise AuthError(f"用户账户已被禁用: {username}")
        
        return True
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """获取用户信息"""
        return self.users.get(username)


def main():
    parser = argparse.ArgumentParser(description="用户认证测试脚本")
    parser.add_argument("--users", type=Path, required=True, help="用户数据JSON文件路径")
    parser.add_argument("--username", required=True, help="要认证的用户名")
    parser.add_argument("--password", required=True, help="用户密码")
    
    args = parser.parse_args()
    
    try:
        user_manager = UserManager(args.users)
        success = user_manager.authenticate(args.username, args.password)
        
        if success:
            user_info = user_manager.get_user_info(args.username)
            print(f"认证成功！用户信息: {user_info}")
        else:
            print("认证失败")
            
    except AuthError as e:
        print(f"认证错误: {e}")
        raise
    except Exception as e:
        print(f"系统错误: {e}")
        raise


if __name__ == "__main__":
    main()
