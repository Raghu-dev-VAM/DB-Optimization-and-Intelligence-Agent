CREATE OR ALTER PROCEDURE dbo.usp_UpdateOrderRisk
  @CustomerId INT
AS
BEGIN
  SET NOCOUNT ON;

  UPDATE r
  SET RiskScore = CASE WHEN SUM(oi.Quantity * oi.UnitPrice) > 10000 THEN 90 ELSE 40 END,
      UpdatedAt = GETDATE()
  FROM dbo.CustomerRisk r
  INNER JOIN dbo.Orders o ON r.CustomerId = o.CustomerId
  INNER JOIN dbo.OrderItems oi ON o.OrderId = oi.OrderId
  WHERE r.CustomerId = @CustomerId
    AND DATEDIFF(day, o.OrderDate, GETDATE()) < 90;
END
