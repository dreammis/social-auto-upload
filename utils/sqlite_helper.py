"""SQLite数据库操作帮助类

此模块提供了同步和异步两种SQLite数据库操作接口，支持：
1. 数据库连接管理（同步/异步）
2. 事务处理（同步/异步）
3. 参数化查询
4. 批量操作
5. 线程安全操作
"""

import sqlite3
import aiosqlite
from typing import Any, List, Dict, Optional, Union, Tuple
from contextlib import contextmanager, asynccontextmanager
import logging
from pathlib import Path
from threading import RLock
import asyncio

from .log import sqlite_logger as logger 

class SQLiteHelper:
    """同步SQLite数据库操作帮助类
    
    提供了一系列线程安全的同步SQLite数据库操作方法。
    适用于同步代码环境或多线程场景。
    
    典型用法:
        db = SQLiteHelper("example.db")
        with db.connection() as conn:
            db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("张三", 25))
    """
    
    def __init__(self, db_path: Union[str, Path], check_same_thread: bool = True) -> None:
        """初始化SQLite帮助类
        
        Args:
            db_path: 数据库文件路径
            check_same_thread: 是否检查同一线程
        """
        self.db_path = Path(db_path)
        self.check_same_thread = check_same_thread
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = RLock()  # 使用重入锁，避免同一线程内重复加锁引起死锁
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """初始化数据库连接"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    @contextmanager
    def connection(self):
        """获取数据库连接的上下文管理器，线程安全
        
        Returns:
            sqlite3.Connection: 数据库连接对象
            
        Example:
            with db.connection() as conn:
                conn.execute("SELECT * FROM users")
        """
        with self._lock:  # 使用线程锁保护连接操作
            if self._conn is None:
                self._conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=self.check_same_thread
                )
                self._conn.row_factory = sqlite3.Row
            
            try:
                yield self._conn
            except Exception as e:
                self._conn.rollback()
                logger.error(f"数据库操作错误: {str(e)}")
                raise
            
    def execute(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> None:
        """执行SQL语句，线程安全
        
        Args:
            sql: SQL语句
            parameters: SQL参数
            
        Example:
            db.execute("INSERT INTO users (name) VALUES (?)", ("张三",))
        """
        with self._lock:
            with self.connection() as conn:
                try:
                    if parameters:
                        conn.execute(sql, parameters)
                    else:
                        conn.execute(sql)
                    conn.commit()
                except Exception as e:
                    logger.error(f"执行SQL错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                    raise
                    
    def execute_many(self, sql: str, parameters: List[Tuple[Any, ...]]) -> None:
        """批量执行SQL语句，线程安全
        
        Args:
            sql: SQL语句
            parameters: SQL参数列表
            
        Example:
            db.execute_many(
                "INSERT INTO users (name, age) VALUES (?, ?)",
                [("张三", 25), ("李四", 30)]
            )
        """
        with self._lock:
            with self.connection() as conn:
                try:
                    conn.executemany(sql, parameters)
                    conn.commit()
                except Exception as e:
                    logger.error(f"批量执行SQL错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                    raise
                    
    def query_one(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
        """查询单条记录，线程安全
        
        Args:
            sql: SQL查询语句
            parameters: SQL参数
            
        Returns:
            Dict[str, Any]: 查询结果字典，未找到返回None
            
        Example:
            user = db.query_one("SELECT * FROM users WHERE id = ?", (1,))
        """
        with self._lock:
            with self.connection() as conn:
                try:
                    cursor = conn.execute(sql, parameters or ())
                    row = cursor.fetchone()
                    return dict(row) if row else None
                except Exception as e:
                    logger.error(f"查询单条记录错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                    raise
                    
    def query_all(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """查询多条记录，线程安全
        
        Args:
            sql: SQL查询语句
            parameters: SQL参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
            
        Example:
            users = db.query_all("SELECT * FROM users WHERE age > ?", (20,))
        """
        with self._lock:
            with self.connection() as conn:
                try:
                    cursor = conn.execute(sql, parameters or ())
                    return [dict(row) for row in cursor.fetchall()]
                except Exception as e:
                    logger.error(f"查询多条记录错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                    raise
                    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在，线程安全
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 表是否存在
        """
        sql = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        return bool(self.query_one(sql, (table_name,)))
    
    def create_table(self, sql: str) -> None:
        """创建表，线程安全
        
        Args:
            sql: 建表SQL语句
            
        Example:
            db.create_table('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER
                )
            ''')
        """
        with self._lock:
            with self.connection() as conn:
                try:
                    conn.execute(sql)
                    conn.commit()
                except Exception as e:
                    logger.error(f"创建表错误: {sql}, 错误: {str(e)}")
                    raise
                    
    def close(self) -> None:
        """关闭数据库连接，线程安全"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

class AsyncSQLiteHelper:
    """异步SQLite数据库操作帮助类
    
    提供了一系列异步的SQLite数据库操作方法，支持异步上下文管理器和事务处理。
    
    典型用法:
        db = AsyncSQLiteHelper("example.db")
        async with db.connection() as conn:
            await db.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("张三", 25))
    """
    
    def __init__(self, db_path: Union[str, Path], check_same_thread: bool = True) -> None:
        """初始化SQLite帮助类
        
        Args:
            db_path: 数据库文件路径
            check_same_thread: 是否检查同一线程
        """
        self.db_path = Path(db_path)
        self.check_same_thread = check_same_thread
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()  # 添加异步锁保护连接
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """初始化数据库连接"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    @asynccontextmanager
    async def connection(self):
        """获取数据库连接的异步上下文管理器
        
        Returns:
            aiosqlite.Connection: 数据库连接对象
            
        Example:
            async with db.connection() as conn:
                await conn.execute("SELECT * FROM users")
        """
        async with self._lock:
            if self._conn is None:
                self._conn = await aiosqlite.connect(
                    self.db_path,
                    check_same_thread=self.check_same_thread
                )
                self._conn.row_factory = aiosqlite.Row
        
        try:
            yield self._conn
        except Exception as e:
            await self._conn.rollback()
            logger.error(f"数据库操作错误: {str(e)}")
            raise
        
    async def execute(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> None:
        """异步执行SQL语句"""
        async with self._lock:  # 锁定整个操作过程
            async with self.connection() as conn:
                try:
                    if parameters:
                        await conn.execute(sql, parameters)
                    else:
                        await conn.execute(sql)
                    await conn.commit()
                except Exception as e:
                    logger.error(
                        f"执行SQL错误: {sql}, 参数: {parameters}, 错误: {str(e)}"
                    )
                    raise
                
    async def execute_many(self, sql: str, parameters: List[Tuple[Any, ...]]) -> None:
        """异步批量执行SQL语句
        
        Args:
            sql: SQL语句
            parameters: SQL参数列表
            
        Example:
            await db.execute_many(
                "INSERT INTO users (name, age) VALUES (?, ?)",
                [("张三", 25), ("李四", 30)]
            )
        """
        async with self.connection() as conn:
            try:
                await conn.executemany(sql, parameters)
                await conn.commit()
            except Exception as e:
                logger.error(f"批量执行SQL错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                raise
                
    async def query_one(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
        """异步查询单条记录
        
        Args:
            sql: SQL查询语句
            parameters: SQL参数
            
        Returns:
            Dict[str, Any]: 查询结果字典，未找到返回None
            
        Example:
            user = await db.query_one("SELECT * FROM users WHERE id = ?", (1,))
        """
        async with self.connection() as conn:
            try:
                cursor = await conn.execute(sql, parameters or ())
                row = await cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"查询单条记录错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                raise
                
    async def query_all(self, sql: str, parameters: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """异步查询多条记录
        
        Args:
            sql: SQL查询语句
            parameters: SQL参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
            
        Example:
            users = await db.query_all("SELECT * FROM users WHERE age > ?", (20,))
        """
        async with self.connection() as conn:
            try:
                cursor = await conn.execute(sql, parameters or ())
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"查询多条记录错误: {sql}, 参数: {parameters}, 错误: {str(e)}")
                raise
                
    async def table_exists(self, table_name: str) -> bool:
        """异步检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 表是否存在
        """
        sql = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = await self.query_one(sql, (table_name,))
        return bool(result)
    
    async def create_table(self, sql: str) -> None:
        """异步创建表
        
        Args:
            sql: 建表SQL语句
            
        Example:
            await db.create_table('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER
                )
            ''')
        """
        async with self.connection() as conn:
            try:
                await conn.execute(sql)
                await conn.commit()
            except Exception as e:
                logger.error(f"创建表错误: {sql}, 错误: {str(e)}")
                raise
                
    async def close(self) -> None:
        """异步关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None 