-- ========================================================
-- Sales Data Analysis System - Database Schema
-- Database: sales_db
-- ========================================================

CREATE DATABASE IF NOT EXISTS sales_db;
USE sales_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    UNIQUE KEY uq_product_category (product_name, category)
);

-- 3. Sales Table
CREATE TABLE IF NOT EXISTS sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    sale_date DATE NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    customer VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    user_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Initial standard products seed
INSERT IGNORE INTO products (product_id, product_name, category) VALUES
(1, 'Laptop', 'Electronics'),
(2, 'Car', 'Automobile'),
(3, 'Office Desk', 'Furniture'),
(4, 'Ergonomic Chair', 'Furniture'),
(5, 'Executive Pen', 'Stationery'),
(6, 'Gaming Keyboard', 'Electronics'),
(7, 'Wireless Headphones', 'Electronics'),
(8, 'Smartwatch', 'Electronics'),
(9, '4K Monitor', 'Electronics'),
(10, 'Bluetooth Earbuds', 'Electronics');
