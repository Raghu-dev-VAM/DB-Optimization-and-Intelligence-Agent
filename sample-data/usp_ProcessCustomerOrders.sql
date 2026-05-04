CREATE OR ALTER PROCEDURE dbo.usp_ProcessCustomerOrders
  @CustomerId INT,
  @StartDate DATE,
  @Status VARCHAR(20)
AS
BEGIN
  SET NOCOUNT ON;

  CREATE TABLE #OrderWork
  (
    OrderId INT,
    CustomerId INT,
    OrderDate DATETIME,
    Status VARCHAR(20),
    TotalAmount DECIMAL(18,2)
  );

  INSERT INTO #OrderWork
  SELECT *
  FROM dbo.Orders o WITH (NOLOCK)
  INNER JOIN dbo.Customers c ON o.CustomerId = c.CustomerId
  LEFT JOIN dbo.OrderItems oi ON o.OrderId = oi.OrderId
  WHERE YEAR(o.OrderDate) >= YEAR(@StartDate)
    AND o.Status = @Status
    AND c.CustomerId = @CustomerId
  ORDER BY o.OrderDate DESC;

  DECLARE order_cursor CURSOR FOR
    SELECT OrderId FROM #OrderWork;

  OPEN order_cursor;
  FETCH NEXT FROM order_cursor INTO @CustomerId;
  WHILE @@FETCH_STATUS = 0
  BEGIN
    EXEC dbo.usp_UpdateOrderRisk @CustomerId;
    FETCH NEXT FROM order_cursor INTO @CustomerId;
  END

  CLOSE order_cursor;
  DEALLOCATE order_cursor;
END
