-- Manual SSMS Execution Guide
-- Replace the placeholder with your actual database name

-- Step 1: Create the database (replace 'YourActualDatabaseName' with desired name)
CREATE DATABASE [CustomerOrderDB];
GO

-- Step 2: Switch to the new database
USE [CustomerOrderDB];
GO

-- Step 3: Paste your generated DDL script here (without the USE statement)
-- The generated script will look like this:

-- CREATE TABLE [Customers] (
--   CustomerId INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
--   CustomerName NVARCHAR(100) NOT NULL,
--   Email NVARCHAR(100) NOT NULL,
--   CreatedAt DATETIME2 NOT NULL
-- );
-- GO

-- CREATE TABLE [Orders] (
--   OrderId INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
--   CustomerId INT NOT NULL,
--   OrderDate DATETIME2 NOT NULL,
--   TotalAmount DECIMAL(10,2) NOT NULL,
--   CreatedAt DATETIME2 NOT NULL
-- );
-- GO

-- ALTER TABLE [Orders] ADD CONSTRAINT FK_Orders_Customers FOREIGN KEY (CustomerId) REFERENCES [Customers](CustomerId);
-- GO

-- CREATE INDEX IX_Orders_CustomerId ON [Orders] (CustomerId);
-- GO

-- Step 4: Verify the tables were created
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length,
    c.is_nullable
FROM sys.tables t
INNER JOIN sys.columns c ON t.object_id = c.object_id
INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
ORDER BY t.name, c.column_id;

-- Step 5: Check foreign key relationships
SELECT 
    fk.name AS ForeignKeyName,
    tp.name AS ParentTable,
    cp.name AS ParentColumn,
    tr.name AS ReferencedTable,
    cr.name AS ReferencedColumn
FROM sys.foreign_keys fk
INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id;