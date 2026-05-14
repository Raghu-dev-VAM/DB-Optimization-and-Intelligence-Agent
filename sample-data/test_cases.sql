-- Test Case 1: Security Vulnerabilities
-- Expected: Security Agent should flag SQL injection, privilege escalation
CREATE PROCEDURE usp_GetUserData
  @Username NVARCHAR(50),
  @TableName NVARCHAR(50)
AS
BEGIN
  DECLARE @sql NVARCHAR(MAX)
  SET @sql = 'SELECT * FROM ' + @TableName + ' WHERE Username = ''' + @Username + ''''
  EXEC sp_executesql @sql
  
  -- Grant excessive permissions
  GRANT ALL ON SCHEMA::dbo TO [public]
END

-- Test Case 2: Performance Issues
-- Expected: Optimizer Agent should flag SELECT *, functions in WHERE, cursors
CREATE PROCEDURE usp_ProcessLargeDataset
AS
BEGIN
  SELECT *
  FROM Orders o
  WHERE YEAR(o.OrderDate) = 2024
    AND MONTH(o.OrderDate) = 12
    AND o.ProductName LIKE '%search%'
  
  DECLARE cursor_slow CURSOR FOR
    SELECT * FROM Customers WHERE UPPER(LastName) LIKE 'SMITH%'
  
  OPEN cursor_slow
  -- Cursor processing logic here
  CLOSE cursor_slow
  DEALLOCATE cursor_slow
END

-- Test Case 3: Complex Dependencies
-- Expected: Dependency Agent should map relationships
CREATE PROCEDURE usp_OrderWorkflow
  @OrderId INT
AS
BEGIN
  EXEC usp_ValidateOrder @OrderId
  EXEC usp_ProcessPayment @OrderId
  EXEC usp_UpdateInventory @OrderId
  EXEC usp_SendNotification @OrderId
END

-- Test Case 4: Mixed Issues (All Agents)
-- Expected: All agents should contribute insights
CREATE FUNCTION fn_CalculateRisk(@CustomerId INT)
RETURNS DECIMAL(5,2)
AS
BEGIN
  DECLARE @Risk DECIMAL(5,2)
  DECLARE @sql NVARCHAR(MAX)
  
  -- Security issue: Dynamic SQL
  SET @sql = 'SELECT SUM(Amount) FROM Orders WHERE CustomerId = ' + CAST(@CustomerId AS VARCHAR)
  
  -- Performance issue: Scalar function, SELECT *
  SELECT @Risk = CASE 
    WHEN EXISTS(SELECT * FROM Orders WHERE YEAR(OrderDate) = YEAR(GETDATE())) 
    THEN 0.85 
    ELSE 0.25 
  END
  
  RETURN @Risk
END

-- Test Case 5: Clean Code (Baseline)
-- Expected: Minimal issues, high confidence in analysis
CREATE PROCEDURE usp_GetCustomerOrders
  @CustomerId INT,
  @StartDate DATE = NULL
AS
BEGIN
  SET NOCOUNT ON
  
  BEGIN TRY
    SELECT 
      o.OrderId,
      o.OrderDate,
      o.TotalAmount,
      o.Status
    FROM dbo.Orders o
    WHERE o.CustomerId = @CustomerId
      AND (@StartDate IS NULL OR o.OrderDate >= @StartDate)
    ORDER BY o.OrderDate DESC
  END TRY
  BEGIN CATCH
    THROW
  END CATCH
END