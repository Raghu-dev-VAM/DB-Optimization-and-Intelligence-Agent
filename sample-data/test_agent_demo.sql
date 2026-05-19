-- ============================================================
-- DB Optimization Agent - Test Database Setup
-- Run this entire script in SSMS
-- ============================================================

USE master;
GO

-- Create test database
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'AgentTestDB')
    DROP DATABASE AgentTestDB;
GO

CREATE DATABASE AgentTestDB;
GO

USE AgentTestDB;
GO

-- ============================================================
-- Step 1 — Create Tables
-- ============================================================

CREATE TABLE dbo.Customers (
    CustomerId   INT IDENTITY(1,1) PRIMARY KEY,
    CustomerName NVARCHAR(200)     NOT NULL,
    Email        NVARCHAR(320)     NOT NULL,
    Country      NVARCHAR(100)     NOT NULL,
    Status       NVARCHAR(30)      NOT NULL DEFAULT 'Active',
    CreatedAt    DATETIME2         NOT NULL DEFAULT GETDATE()
);

CREATE TABLE dbo.Products (
    ProductId   INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(200)    NOT NULL,
    Category    NVARCHAR(100)    NOT NULL,
    Price       DECIMAL(18,2)    NOT NULL,
    IsActive    BIT              NOT NULL DEFAULT 1
);

CREATE TABLE dbo.Orders (
    OrderId     INT IDENTITY(1,1) PRIMARY KEY,
    CustomerId  INT               NOT NULL REFERENCES dbo.Customers(CustomerId),
    OrderDate   DATETIME2         NOT NULL DEFAULT GETDATE(),
    Status      NVARCHAR(30)      NOT NULL DEFAULT 'Pending',
    TotalAmount DECIMAL(18,2)     NOT NULL DEFAULT 0,
    CreatedAt   DATETIME2         NOT NULL DEFAULT GETDATE()
);

CREATE TABLE dbo.OrderItems (
    OrderItemId INT IDENTITY(1,1) PRIMARY KEY,
    OrderId     INT               NOT NULL REFERENCES dbo.Orders(OrderId),
    ProductId   INT               NOT NULL REFERENCES dbo.Products(ProductId),
    Quantity    INT               NOT NULL,
    UnitPrice   DECIMAL(18,2)     NOT NULL
);
GO

-- ============================================================
-- Step 2 — Insert Test Data (100,000 rows)
-- ============================================================

-- Insert 1,000 Customers
INSERT INTO dbo.Customers (CustomerName, Email, Country, Status)
SELECT
    'Customer ' + CAST(n AS NVARCHAR),
    'customer' + CAST(n AS NVARCHAR) + '@email.com',
    CASE n % 5
        WHEN 0 THEN 'USA'
        WHEN 1 THEN 'UK'
        WHEN 2 THEN 'Canada'
        WHEN 3 THEN 'Australia'
        ELSE 'Germany'
    END,
    CASE n % 10 WHEN 0 THEN 'Inactive' ELSE 'Active' END
FROM (
    SELECT TOP 1000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.objects a CROSS JOIN sys.objects b
) x;
GO

-- Insert 500 Products
INSERT INTO dbo.Products (ProductName, Category, Price, IsActive)
SELECT
    'Product ' + CAST(n AS NVARCHAR),
    CASE n % 4
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Food'
        ELSE 'Books'
    END,
    ROUND(RAND(CHECKSUM(NEWID())) * 500 + 10, 2),
    CASE n % 8 WHEN 0 THEN 0 ELSE 1 END
FROM (
    SELECT TOP 500 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.objects a CROSS JOIN sys.objects b
) x;
GO

-- Insert 50,000 Orders
INSERT INTO dbo.Orders (CustomerId, OrderDate, Status, TotalAmount)
SELECT
    (n % 1000) + 1,
    DATEADD(DAY, -(n % 730), GETDATE()),
    CASE n % 4
        WHEN 0 THEN 'Pending'
        WHEN 1 THEN 'Completed'
        WHEN 2 THEN 'Shipped'
        ELSE 'Cancelled'
    END,
    ROUND(RAND(CHECKSUM(NEWID())) * 1000 + 50, 2)
FROM (
    SELECT TOP 50000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.objects a CROSS JOIN sys.objects b CROSS JOIN sys.objects c
) x;
GO

-- Insert 100,000 OrderItems
INSERT INTO dbo.OrderItems (OrderId, ProductId, Quantity, UnitPrice)
SELECT
    (n % 50000) + 1,
    (n % 500) + 1,
    (n % 10) + 1,
    ROUND(RAND(CHECKSUM(NEWID())) * 200 + 5, 2)
FROM (
    SELECT TOP 100000 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.objects a CROSS JOIN sys.objects b CROSS JOIN sys.objects c
) x;
GO

-- ============================================================
-- Step 3 — Create the SLOW Stored Procedure
-- (This is what you will paste into your agent)
-- ============================================================

CREATE OR ALTER PROCEDURE dbo.usp_GetPendingOrderReport
    @Year   INT,
    @Country NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT *
    FROM dbo.Orders o WITH (NOLOCK)
    INNER JOIN dbo.Customers c ON o.CustomerId = c.CustomerId
    INNER JOIN dbo.OrderItems oi ON o.OrderId = oi.OrderId
    INNER JOIN dbo.Products p ON oi.ProductId = p.ProductId
    WHERE YEAR(o.OrderDate) = @Year
      AND o.Status = 'Pending'
      AND UPPER(c.Country) = UPPER(@Country)
      AND p.IsActive = 1
    ORDER BY o.OrderDate DESC;
END
GO

-- ============================================================
-- Step 4 — Run the SLOW procedure and measure time
-- ============================================================

SET STATISTICS TIME ON;
SET STATISTICS IO ON;

EXEC dbo.usp_GetPendingOrderReport @Year = 2024, @Country = 'USA';

SET STATISTICS TIME OFF;
SET STATISTICS IO OFF;
GO

-- ============================================================
-- You will see timing results in the Messages tab in SSMS.
-- Note down:
--   - SQL Server Execution Times (CPU time, elapsed time)
--   - Logical reads
-- Then paste the stored procedure into your agent and get
-- the optimized version. Run that and compare the numbers.
-- ============================================================
