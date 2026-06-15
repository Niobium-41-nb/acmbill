-- 设置字符集
ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 应用启动时会自动通过 db.create_all() 创建表，
-- 此文件仅用于确保数据库字符集等初始化配置
