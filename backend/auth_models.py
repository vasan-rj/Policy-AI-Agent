import sqlite3
import hashlib
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import uuid

class UserAuthManager:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.init_database()
    
    def init_database(self):
        """Initialize the users database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Create user sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == password_hash
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> Dict:
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return {"success": False, "message": "Username or email already exists"}
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_hash = self.hash_password(password)
            
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, email, password_hash, full_name))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "User created successfully",
                "user_id": user_id
            }
        
        except Exception as e:
            return {"success": False, "message": str(e)}
        
        finally:
            conn.close()
    
    def authenticate_user(self, username_or_email: str, password: str) -> Dict:
        """Authenticate user login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Find user by username or email
            cursor.execute("""
                SELECT id, username, email, password_hash, full_name, is_active
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            """, (username_or_email, username_or_email))
            
            user = cursor.fetchone()
            if not user:
                return {"success": False, "message": "Invalid credentials"}
            
            user_id, username, email, password_hash, full_name, is_active = user
            
            # Verify password
            if not self.verify_password(password, password_hash):
                return {"success": False, "message": "Invalid credentials"}
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
            conn.commit()
            
            # Generate JWT token
            token = self.generate_jwt_token(user_id, username)
            
            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name
                },
                "token": token
            }
        
        except Exception as e:
            return {"success": False, "message": str(e)}
        
        finally:
            conn.close()
    
    def generate_jwt_token(self, user_id: str, username: str) -> str:
        """Generate JWT token for user"""
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return {
                "user_id": payload["user_id"],
                "username": payload["username"]
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user information by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, username, email, full_name, created_at, last_login
                FROM users 
                WHERE id = ? AND is_active = 1
            """, (user_id,))
            
            user = cursor.fetchone()
            if user:
                return {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "full_name": user[3],
                    "created_at": user[4],
                    "last_login": user[5]
                }
            return None
        
        finally:
            conn.close()
    
    def update_user_profile(self, user_id: str, full_name: str = None, email: str = None) -> Dict:
        """Update user profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if full_name is not None:
                updates.append("full_name = ?")
                params.append(full_name)
            
            if email is not None:
                # Check if email already exists for another user
                cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
                if cursor.fetchone():
                    return {"success": False, "message": "Email already exists"}
                
                updates.append("email = ?")
                params.append(email)
            
            if not updates:
                return {"success": False, "message": "No updates provided"}
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            
            return {"success": True, "message": "Profile updated successfully"}
        
        except Exception as e:
            return {"success": False, "message": str(e)}
        
        finally:
            conn.close()
